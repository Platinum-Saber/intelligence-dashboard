"""
One-shot historical backfill script.
Fetches 7 days of FX, commodity, and news data and inserts into the DB.

Run from inside the container or from local with a valid DATABASE_URL:
    python backfill_history.py

Uses:
  - Yahoo Finance chart API  (FX + commodities, no key)
  - NewsAPI.org              (news, NEWSAPI_KEY from env)
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backfill")

BACKFILL_DAYS = 7
YF_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
YF_HEADERS = {"User-Agent": "Mozilla/5.0"}
LB_TO_TONNE = 2204.62

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWS_QUERIES = [
    ("USD LKR OR rupee dollar Sri Lanka", "FX"),
    ("LME copper price", "COPPER"),
    ("LME aluminium price", "ALUMINIUM"),
    ("UAE Vietnam China supply chain shipping", "TRADE"),
    ("Sri Lanka port logistics flood", "LOGISTICS"),
]


# ── Yahoo Finance helpers ─────────────────────────────────────────────────────

def _yf_history(ticker: str, days: int) -> list[tuple[datetime, float]]:
    """Return list of (naive utc datetime, close price) for the last N days."""
    try:
        resp = httpx.get(
            f"{YF_BASE}/{ticker}",
            params={"interval": "1d", "range": f"{days}d"},
            headers=YF_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        pairs = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
            pairs.append((dt, float(close)))
        return pairs
    except Exception as exc:
        log.warning(f"Yahoo Finance {ticker} failed: {exc}")
        return []


def backfill_fx(db) -> int:
    from app.models.fx import FXRate

    existing_ts = {r.timestamp.date() for r in db.query(FXRate.timestamp).all()}
    pairs = _yf_history("USDLKR=X", BACKFILL_DAYS + 2)
    inserted = 0
    for dt, rate in pairs:
        if dt.date() in existing_ts:
            continue
        db.add(FXRate(timestamp=dt, usd_lkr=rate, source="yahoo-finance-history"))
        existing_ts.add(dt.date())
        inserted += 1
    db.commit()
    log.info(f"FX: inserted {inserted} rows")
    return inserted


def backfill_commodities(db) -> int:
    from app.models.commodities import CommodityPrice

    existing_ts = {
        (r.symbol, r.timestamp.date())
        for r in db.query(CommodityPrice.symbol, CommodityPrice.timestamp).all()
    }

    specs = [
        ("COPPER",    "HG=F",  True),   # True = convert lb→tonne
        ("ALUMINIUM", "ALI=F", False),
    ]
    inserted = 0
    for symbol, ticker, convert in specs:
        pairs = _yf_history(ticker, BACKFILL_DAYS + 2)
        for dt, price in pairs:
            key = (symbol, dt.date())
            if key in existing_ts:
                continue
            if convert:
                price = round(price * LB_TO_TONNE, 2)
            db.add(CommodityPrice(
                symbol=symbol,
                timestamp=dt,
                price_usd=price,
                unit="per_tonne",
                source="yahoo-finance-history",
            ))
            existing_ts.add(key)
            inserted += 1
    db.commit()
    log.info(f"Commodities: inserted {inserted} rows")
    return inserted


def backfill_news(db) -> int:
    from app.models.news import NewsItem

    if not NEWSAPI_KEY:
        log.warning("NEWSAPI_KEY not set — skipping news backfill")
        return 0

    from_ = (datetime.now(timezone.utc) - timedelta(days=BACKFILL_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    existing_urls = {r.url for r in db.query(NewsItem.url).all()}

    inserted = 0
    for query, topic in NEWS_QUERIES:
        page = 1
        while page <= 3:
            try:
                resp = httpx.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "from": from_,
                        "to": to_,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": 100,
                        "page": page,
                        "apiKey": NEWSAPI_KEY,
                    },
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                if not articles:
                    break
                for a in articles:
                    url = a.get("url") or ""
                    if url in existing_urls:
                        continue
                    pub = a.get("publishedAt")
                    if not pub:
                        continue
                    published_at = datetime.fromisoformat(
                        pub.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    db.add(NewsItem(
                        published_at=published_at,
                        headline=(a.get("title") or "")[:500],
                        summary=(a.get("description") or "")[:1000],
                        url=url[:500],
                        source=a.get("source", {}).get("name", "newsapi"),
                        topic=topic,
                        relevance_score=0.8,
                        sentiment=None,
                    ))
                    existing_urls.add(url)
                    inserted += 1
                total_results = data.get("totalResults", 0)
                if page * 100 >= min(total_results, 300):
                    break
                page += 1
            except Exception as exc:
                log.warning(f"NewsAPI [{topic}] page {page} failed: {exc}")
                break
    db.commit()
    log.info(f"News: inserted {inserted} articles")
    return inserted


def main():
    # Bootstrap SQLAlchemy models so tables exist
    from app.database import Base, engine, SessionLocal
    from app.models import FXRate  # ensures all models registered

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        total_fx   = backfill_fx(db)
        total_comm = backfill_commodities(db)
        total_news = backfill_news(db)
        log.info(f"Backfill complete: FX={total_fx}, Commodities={total_comm}, News={total_news}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
