import random
from datetime import datetime, timedelta

from app.models.fx import FXRate


def generate_fx_rates(days: int = 90) -> list[FXRate]:
    """
    Random-walk USD/LKR rates, 4 readings per day.
    Centred around the FY2024/25 average of ~297 with realistic volatility.
    """
    records: list[FXRate] = []
    rate = 297.0
    start = datetime.utcnow() - timedelta(days=days)

    for i in range(days * 4):
        timestamp = start + timedelta(hours=i * 6)
        # Mean-reverting random walk — slight pull back toward 297
        drift = (297.0 - rate) * 0.01
        shock = random.gauss(0, 0.35)
        rate = max(280.0, min(320.0, rate + drift + shock))
        records.append(FXRate(timestamp=timestamp, usd_lkr=round(rate, 4), source="debug"))

    return records
