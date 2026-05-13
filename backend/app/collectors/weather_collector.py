"""
Open-Meteo weather collector — free, no API key required.
Fetches daily precipitation and temperature for Sri Lanka districts
and supplier ports.
"""
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Static coordinates for Sri Lanka districts (capital city of each province)
SL_DISTRICTS: dict[str, tuple[float, float]] = {
    "Western":       (6.9271, 79.8612),
    "Southern":      (6.0535, 80.2210),
    "Northern":      (9.6615, 80.0255),
    "Eastern":       (8.5874, 81.2152),
    "North Western": (7.9403, 80.3500),
    "North Central": (8.3347, 80.4000),
    "Uva":           (6.9934, 81.0550),
    "Sabaragamuwa":  (6.6828, 80.3992),
    "Central":       (7.2906, 80.6337),
}

SUPPLIER_PORTS: dict[str, tuple[float, float]] = {
    "Dubai Port (UAE)":               (25.0657, 55.1713),
    "Shanghai Port (China)":          (31.3725, 121.5168),
    "Ho Chi Minh Port (Vietnam)":     (10.7769, 106.7009),
    "Singapore Port (Singapore)":     (1.2868,  103.8545),
}

_BASE = "https://api.open-meteo.com/v1/forecast"


def _fetch_location(name: str, lat: float, lon: float, location_type: str) -> dict | None:
    try:
        resp = httpx.get(
            _BASE,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "precipitation_sum,temperature_2m_max",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        rainfall = (daily.get("precipitation_sum") or [None])[0]
        temp = (daily.get("temperature_2m_max") or [None])[0]

        def _risk(mm: float | None) -> str:
            if mm is None:
                return "LOW"
            if mm < 10:
                return "LOW"
            if mm < 30:
                return "MEDIUM"
            if mm < 60:
                return "HIGH"
            return "CRITICAL"

        return {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
            "location_type": location_type,
            "location_name": name,
            "rainfall_mm": rainfall,
            "flood_risk": _risk(rainfall),
            "temperature_c": temp,
            "source": "open-meteo",
        }
    except Exception as exc:
        logger.warning(f"[weather_collector] {name} fetch failed: {exc}")
        return None


def fetch_sri_lanka_weather() -> list[dict]:
    results = []
    for name, (lat, lon) in SL_DISTRICTS.items():
        rec = _fetch_location(name, lat, lon, "sri_lanka_district")
        if rec:
            results.append(rec)
    return results


def fetch_supplier_port_weather() -> list[dict]:
    results = []
    for name, (lat, lon) in SUPPLIER_PORTS.items():
        rec = _fetch_location(name, lat, lon, "supplier_port")
        if rec:
            results.append(rec)
    return results
