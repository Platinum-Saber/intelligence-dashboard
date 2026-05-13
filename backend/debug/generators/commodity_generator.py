import random
from datetime import datetime, timedelta

from app.models.commodities import CommodityPrice

# LME benchmarks (USD/tonne) for FY2024/25 context
_COPPER_MID = 9200.0
_ALUMINIUM_MID = 2400.0


def _walk(start: float, days: int, std: float, lo: float, hi: float, symbol: str, unit: str) -> list[CommodityPrice]:
    records: list[CommodityPrice] = []
    price = start
    base_ts = datetime.utcnow() - timedelta(days=days)

    for i in range(days):
        timestamp = base_ts + timedelta(days=i)
        drift = (start - price) * 0.008   # weak mean reversion
        shock = random.gauss(0, std)
        price = max(lo, min(hi, price + drift + shock))
        records.append(CommodityPrice(
            timestamp=timestamp,
            symbol=symbol,
            price_usd=round(price, 2),
            unit=unit,
            source="debug",
        ))

    return records


def generate_copper_prices(days: int = 90) -> list[CommodityPrice]:
    return _walk(_COPPER_MID, days, std=55.0, lo=7800.0, hi=10800.0, symbol="COPPER", unit="per_tonne")


def generate_aluminium_prices(days: int = 90) -> list[CommodityPrice]:
    return _walk(_ALUMINIUM_MID, days, std=22.0, lo=1900.0, hi=3100.0, symbol="ALUMINIUM", unit="per_tonne")
