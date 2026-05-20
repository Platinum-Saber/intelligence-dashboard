"""
Supply-chain news collector — freenewsapi.io (free tier: 5,000 req/day, no pub delay).
Requires FREENEWSAPI_KEY in .env.

Rate-limit budget:
  Free tier: 5,000 req/day, 2 req/sec, pageSize max 100.
  5 queries per collection cycle (every 3h = 8 cycles/day = 40 req/day).
  Topic classification is done by reclassify_topic() on the fetched content.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.freenewsapi.io/v1/news"
_REQUEST_DELAY = 0.6  # seconds between requests — stays under 2 req/sec

# One keyword per query; broad terms maximise article coverage.
# reclassify_topic() assigns the final topic; _QUERY_HINTS is the fallback
# when the content classifier can't find 2 keyword hits (common for short incipit).
_QUERIES: list[str] = [
    "copper",
    "aluminium",
    "LME",
    "rupee",
    "logistics",
]

_QUERY_HINTS: dict[str, str | None] = {
    "copper":    "COPPER",
    "aluminium": "ALUMINIUM",
    "LME":       None,        # covers both metals — let content classifier decide
    "rupee":     "FX",
    "logistics": "LOGISTICS",
}

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
    if not settings.freenewsapi_key:
        logger.debug("[news_collector] FREENEWSAPI_KEY not set — skipping live fetch")
        return []

    now_utc = datetime.now(timezone.utc)
    fetched_at = now_utc.replace(tzinfo=None)
    # 24h lookback — freenewsapi has no publication delay (unlike NewsAPI free tier).
    since = (now_utc - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = {"x-api-key": settings.freenewsapi_key}
    seen_uuids: set[str] = set()
    results: list[dict] = []

    for query in _QUERIES:
        try:
            resp = httpx.get(
                _BASE,
                params={
                    "in_title": query,
                    "language": "en",
                    "limit":    100,
                    "from":     since,
                    "sortBy":   "publishedAt",
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json().get("data", [])

            for a in articles:
                uuid = a.get("uuid", "")
                if not uuid or uuid in seen_uuids:
                    continue
                seen_uuids.add(uuid)

                headline = (a.get("title") or "")[:500]
                summary  = (a.get("incipit") or "")[:1000]
                topic    = reclassify_topic(headline, summary) or _QUERY_HINTS.get(query)

                pub_str = a.get("published_at", "")
                try:
                    published_at = datetime.fromisoformat(
                        pub_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    published_at = fetched_at

                results.append({
                    "published_at":    published_at,
                    "fetched_at":      fetched_at,
                    "headline":        headline,
                    "summary":         summary,
                    "url":             a.get("original_url", ""),
                    "source":          a.get("publisher") or "freenewsapi",
                    "topic":           topic,
                    "relevance_score": 0.8,
                    "sentiment":       None,
                })

            logger.info(f"[news_collector] '{query}' → {len(articles)} articles (unique so far: {len(results)})")
            time.sleep(_REQUEST_DELAY)

        except Exception as exc:
            logger.warning(f"[news_collector] Query '{query}' failed: {exc}")

    logger.info(f"[news_collector] Total collected: {len(results)} unique articles")
    return results
