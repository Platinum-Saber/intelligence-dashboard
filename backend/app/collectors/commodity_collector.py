"""
LME copper and aluminium price collector via Yahoo Finance (free, no key required).
Uses ticker symbols: HG=F (copper), ALI=F (aluminium).
"""
import logging
from datetime import datetime, date

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


def fetch_commodity_history(symbol: str, days: int = 7) -> list[dict]:
    """Fetch up to `days` of daily closing prices. Returns [{date, price_usd}]."""
    ticker = _TICKERS.get(symbol.upper())
    if not ticker:
        return []
    try:
        resp = httpx.get(
            f"{_BASE}/{ticker}",
            params={"interval": "1d", "range": f"{days}d"},
            headers=_HEADERS,
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
            price = round(close * _LB_TO_TONNE, 2) if symbol.upper() == "COPPER" else round(float(close), 2)
            out.append({"date": datetime.utcfromtimestamp(ts).date(), "price_usd": price})
        return out
    except Exception as exc:
        logger.warning(f"[commodity_collector] history fetch failed for {symbol}: {exc}")
        return []
