"""
Live USD/LKR collector — exchangerate-api.com (free tier: 1500 req/month).
Requires FX_API_KEY in .env.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://v6.exchangerate-api.com/v6"


def fetch_usd_lkr() -> float | None:
    if not settings.fx_api_key:
        logger.debug("[fx_collector] FX_API_KEY not set — skipping live fetch")
        return None
    try:
        resp = httpx.get(
            f"{_BASE}/{settings.fx_api_key}/pair/USD/LKR",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") == "success":
            return float(data["conversion_rate"])
        logger.warning(f"[fx_collector] Unexpected response: {data.get('error-type')}")
    except Exception as exc:
        logger.warning(f"[fx_collector] Fetch failed: {exc}")
    return None
