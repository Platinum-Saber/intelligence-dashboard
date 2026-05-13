"""
Phase 1 stub — collects supply-chain news from NewsAPI.org.
Requires NEWSAPI_KEY in .env (Phase 2).
"""
import logging

logger = logging.getLogger(__name__)


def fetch_supply_chain_news() -> list[dict]:
    logger.info("[news_collector] Live fetch not yet implemented")
    return []
