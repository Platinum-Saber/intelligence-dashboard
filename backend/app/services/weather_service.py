from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

from app.models.weather import WeatherReading
from app.schemas.weather import WeatherReadingOut, WeatherLatest


def get_latest_all(db: Session) -> list[WeatherLatest]:
    """Most recent reading per location."""
    from sqlalchemy import func

    subq = (
        db.query(
            WeatherReading.location_name,
            func.max(WeatherReading.timestamp).label("max_ts"),
        )
        .group_by(WeatherReading.location_name)
        .subquery()
    )

    rows = (
        db.query(WeatherReading)
        .join(
            subq,
            (WeatherReading.location_name == subq.c.location_name)
            & (WeatherReading.timestamp == subq.c.max_ts),
        )
        .order_by(WeatherReading.location_type, WeatherReading.location_name)
        .all()
    )

    return [
        WeatherLatest(
            location_name=r.location_name,
            location_type=r.location_type,
            timestamp=r.timestamp,
            rainfall_mm=r.rainfall_mm,
            flood_risk=r.flood_risk or "LOW",
            temperature_c=r.temperature_c,
        )
        for r in rows
    ]


def get_history(db: Session, location_name: str, days: int = 30) -> list[WeatherReadingOut]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        db.query(WeatherReading)
        .filter(WeatherReading.location_name == location_name, WeatherReading.timestamp >= since)
        .order_by(WeatherReading.timestamp.asc())
        .all()
    )
    return [WeatherReadingOut.model_validate(r) for r in rows]


def get_high_risk(db: Session, risk_levels: list[str] | None = None) -> list[WeatherLatest]:
    """Returns latest readings where flood_risk is in the specified levels."""
    if risk_levels is None:
        risk_levels = ["HIGH", "CRITICAL"]
    latest = get_latest_all(db)
    return [loc for loc in latest if loc.flood_risk in risk_levels]
