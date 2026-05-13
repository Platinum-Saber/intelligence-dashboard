"""
Supply-chain news collector — NewsAPI.org (free tier: 100 req/day).
Requires NEWSAPI_KEY in .env.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://newsapi.org/v2/everything"

# Queries mapped to dashboard topics
_QUERIES: list[tuple[str, str]] = [
    ("USD LKR OR rupee dollar Sri Lanka", "FX"),
    ("LME copper price", "COPPER"),
    ("LME aluminium price", "ALUMINIUM"),
    ("UAE Vietnam China supply chain shipping", "TRADE"),
    ("Sri Lanka port logistics flood", "LOGISTICS"),
]


def fetch_supply_chain_news() -> list[dict]:
    if not settings.newsapi_key:
        logger.debug("[news_collector] NEWSAPI_KEY not set — skipping live fetch")
        return []

    since = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []

    for query, topic in _QUERIES:
        try:
            resp = httpx.get(
                _BASE,
                params={
                    "q": query,
                    "from": since,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 10,
                    "apiKey": settings.newsapi_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            for a in articles:
                pub = a.get("publishedAt")
                if not pub:
                    continue
                results.append({
                    "published_at": datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None),
                    "headline": (a.get("title") or "")[:500],
                    "summary": (a.get("description") or "")[:1000],
                    "url": a.get("url"),
                    "source": a.get("source", {}).get("name", "newsapi"),
                    "topic": topic,
                    "relevance_score": 0.8,
                    "sentiment": None,
                })
        except Exception as exc:
            logger.warning(f"[news_collector] Query '{topic}' failed: {exc}")

    logger.info(f"[news_collector] Fetched {len(results)} articles")
    return results
