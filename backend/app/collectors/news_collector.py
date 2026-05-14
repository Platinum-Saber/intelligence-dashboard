"""
Supply-chain news collector — NewsAPI.org (free tier: 100 req/day).
Requires NEWSAPI_KEY in .env.

Rate-limit budget:
  Free tier: 100 req/day, 24-hour article delay, pageSize max 100.
  We send 2 broad queries per collection cycle (every 3h = 8 cycles/day = 16 req/day).
  Topic classification is done by reclassify_topic() on the fetched content,
  not by query-per-topic — this is why Sprint 5.1 content classification exists.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://newsapi.org/v2/everything"

# 2 broad queries cover all 5 dashboard topics within the 100 req/day budget.
# pageSize=100 (API max) maximises articles per request.
# 72h lookback accounts for the free-tier 24-hour article publication delay.
_QUERIES: list[str] = [
    # Commodity + metals signals
    "copper OR aluminium OR aluminum OR \"LME\" OR \"base metals\" OR \"metal prices\"",
    # FX + trade + Sri Lanka logistics signals
    "rupee OR \"LKR\" OR \"supply chain\" OR \"Sri Lanka\" OR shipping OR logistics OR tariff OR \"trade war\"",
]

# Sprint 5.1 — content-based topic classification.
# An article is assigned the topic with the highest keyword score (min 2 hits).
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "FX":        ["lkr", "rupee", "usd", "forex", "exchange rate", "cbsl", "dollar", "currency"],
    "COPPER":    ["copper", "lme copper", "hg=f", "copper price", "copper market", "red metal"],
    "ALUMINIUM": ["aluminium", "aluminum", "lme aluminium", "ali=f", "aluminium price"],
    "TRADE":     ["supply chain", "tariff", "trade war", "sanctions", "import", "export", "shipping", "freight", "uae", "vietnam", "china trade"],
    "LOGISTICS": ["port", "logistics", "flood", "disruption", "congestion", "colombo port", "freight delay"],
}


def reclassify_topic(headline: str, summary: str | None) -> str | None:
    """Return the best-matching topic if it scores >= 2 keyword hits, else None."""
    combined = f"{headline} {summary or ''}".lower()
    best_topic: str | None = None
    best_score = 0
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic if best_score >= 2 else None


def fetch_supply_chain_news() -> list[dict]:
    if not settings.newsapi_key:
        logger.debug("[news_collector] NEWSAPI_KEY not set — skipping live fetch")
        return []

    now_utc = datetime.now(timezone.utc)
    fetched_at = now_utc.replace(tzinfo=None)
    # 72h lookback: free tier has a 24-hour publication delay, so articles
    # from the last 24h are not yet available. Going back 72h ensures we
    # reliably catch the past 2 days of released articles.
    since = (now_utc - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")

    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in _QUERIES:
        try:
            resp = httpx.get(
                _BASE,
                params={
                    "q":        query,
                    "from":     since,
                    "sortBy":   "publishedAt",
                    "language": "en",
                    "pageSize": 100,        # API maximum — maximise articles per request
                    "apiKey":   settings.newsapi_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json().get("articles", [])

            for a in articles:
                pub = a.get("publishedAt")
                url = a.get("url")
                if not pub or not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                headline = (a.get("title") or "")[:500]
                summary  = (a.get("description") or "")[:1000]
                topic    = reclassify_topic(headline, summary)  # content-based; None if no match

                results.append({
                    "published_at":   datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None),
                    "fetched_at":     fetched_at,
                    "headline":       headline,
                    "summary":        summary,
                    "url":            url,
                    "source":         a.get("source", {}).get("name", "newsapi"),
                    "topic":          topic,   # None articles are unclassified until /reclassify-all
                    "relevance_score": 0.8,
                    "sentiment":      None,
                })

            logger.info(f"[news_collector] Query fetched {len(articles)} articles (unique so far: {len(results)})")

        except Exception as exc:
            logger.warning(f"[news_collector] Query failed: {exc}")

    logger.info(f"[news_collector] Total collected: {len(results)} unique articles")
    return results
