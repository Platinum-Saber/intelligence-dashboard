import random
from datetime import datetime, timedelta

from app.models.weather import WeatherReading

SL_DISTRICTS = [
    "Western", "Southern", "Northern", "Eastern",
    "North Western", "North Central", "Uva", "Sabaragamuwa", "Central",
]

SUPPLIER_PORTS = [
    "Dubai Port (UAE)",
    "Shanghai Port (China)",
    "Ho Chi Minh Port (Vietnam)",
    "Singapore Port (Singapore)",
]


def _flood_risk(rainfall_mm: float) -> str:
    if rainfall_mm < 10:
        return "LOW"
    if rainfall_mm < 30:
        return "MEDIUM"
    if rainfall_mm < 60:
        return "HIGH"
    return "CRITICAL"


def _monsoon_base(month: int) -> float:
    """Rough monsoon seasonality for Sri Lanka (mm/day expected rainfall)."""
    if month in (5, 6, 7, 8, 9):   # SW monsoon + inter-monsoon
        return 28.0
    if month in (10, 11, 12):        # NE monsoon
        return 18.0
    return 6.0                        # dry season


def generate_weather(days: int = 90) -> list[WeatherReading]:
    records: list[WeatherReading] = []
    base_ts = datetime.utcnow() - timedelta(days=days)

    for i in range(days):
        timestamp = base_ts + timedelta(days=i)
        base_rain = _monsoon_base(timestamp.month)

        for district in SL_DISTRICTS:
            rainfall = max(0.0, random.gauss(base_rain, base_rain * 0.6))
            records.append(WeatherReading(
                timestamp=timestamp,
                location_type="sri_lanka_district",
                location_name=district,
                rainfall_mm=round(rainfall, 1),
                flood_risk=_flood_risk(rainfall),
                temperature_c=round(random.gauss(29.5, 1.8), 1),
                source="debug",
            ))

        for port in SUPPLIER_PORTS:
            rainfall = max(0.0, random.gauss(7.0, 5.0))
            records.append(WeatherReading(
                timestamp=timestamp,
                location_type="supplier_port",
                location_name=port,
                rainfall_mm=round(rainfall, 1),
                flood_risk=_flood_risk(rainfall),
                temperature_c=round(random.gauss(28.0, 3.0), 1),
                source="debug",
            ))

    return records
