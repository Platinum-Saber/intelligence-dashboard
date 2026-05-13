"""
LME copper and aluminium price collector via Yahoo Finance (free, no key required).
Uses ticker symbols: HG=F (copper), ALI=F (aluminium).
"""
import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

# Yahoo Finance v8 chart endpoint (unofficial but stable)
_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_HEADERS = {"User-Agent": "Mozilla/5.0"}

_TICKERS = {
    "COPPER": "HG=F",       # LME copper futures (USD/lb — converted to USD/tonne)
    "ALUMINIUM": "ALI=F",   # LME aluminium futures
}

_LB_TO_TONNE = 2204.62


def _fetch_ticker(ticker: str, symbol: str) -> float | None:
    try:
        resp = httpx.get(
            f"{_BASE}/{ticker}",
            params={"interval": "1d", "range": "1d"},
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        # Copper (HG=F) is quoted in USD/lb; convert to USD/tonne
        if symbol == "COPPER":
            price = round(price * _LB_TO_TONNE, 2)
        return float(price)
    except Exception as exc:
        logger.warning(f"[commodity_collector] {ticker} fetch failed: {exc}")
        return None


def fetch_copper_price() -> float | None:
    return _fetch_ticker(_TICKERS["COPPER"], "COPPER")


def fetch_aluminium_price() -> float | None:
    return _fetch_ticker(_TICKERS["ALUMINIUM"], "ALUMINIUM")
