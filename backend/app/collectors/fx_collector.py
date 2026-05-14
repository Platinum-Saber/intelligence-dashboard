"""
Live USD/LKR collector — exchangerate-api.com (free tier: 1500 req/month).
Requires FX_API_KEY in .env.
Historical backfill uses Yahoo Finance USDLKR=X (free, no key required).
"""
import logging
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://v6.exchangerate-api.com/v6"
_YF_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_YF_HEADERS = {"User-Agent": "Mozilla/5.0"}


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


def fetch_usd_lkr_history(days: int = 7) -> list[dict]:
    """Fetch up to `days` of daily USD/LKR rates via Yahoo Finance USDLKR=X.
    Returns [{date, rate}] sorted oldest-first."""
    try:
        resp = httpx.get(
            f"{_YF_BASE}/USDLKR=X",
            params={"interval": "1d", "range": f"{days}d"},
            headers=_YF_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        closes = result["indicators"]["quote"][0].get("close", [])
        out = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            out.append({"date": datetime.utcfromtimestamp(ts).date(), "rate": round(float(close), 4)})
        return out
    except Exception as exc:
        logger.warning(f"[fx_collector] history fetch failed: {exc}")
        return []
