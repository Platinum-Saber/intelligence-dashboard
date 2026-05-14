from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

from app.models.weather import WeatherReading
from app.schemas.weather import WeatherReadingOut, WeatherLatest

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


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
            drought_risk=r.drought_risk,
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


# ── Drought risk ──────────────────────────────────────────────────────────────

def get_drought_risk(db: Session, location_name: str) -> str:
    """
    Computes rolling 14-day rainfall deficit for a location and returns a risk level.
    Baseline: 5 mm/day average (Sri Lanka outside dry season).
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
    readings = (
        db.query(WeatherReading)
        .filter(
            WeatherReading.location_name == location_name,
            WeatherReading.timestamp >= cutoff,
        )
        .all()
    )
    if not readings:
        return "LOW"

    total_mm = sum(r.rainfall_mm for r in readings if r.rainfall_mm is not None)
    expected_mm = 14 * 5
    deficit_pct = max(0, (expected_mm - total_mm) / expected_mm)

    if deficit_pct >= 0.80:
        return "CRITICAL"
    if deficit_pct >= 0.60:
        return "HIGH"
    if deficit_pct >= 0.35:
        return "MEDIUM"
    return "LOW"


def update_drought_risk_latest(db: Session, location_name: str) -> None:
    """Compute and stamp drought_risk on the most recent reading for a location."""
    risk = get_drought_risk(db, location_name)
    latest = (
        db.query(WeatherReading)
        .filter(WeatherReading.location_name == location_name)
        .order_by(WeatherReading.timestamp.desc())
        .first()
    )
    if latest:
        latest.drought_risk = risk


def get_high_drought_risk(db: Session, min_level: str = "HIGH") -> list[WeatherLatest]:
    """Returns latest SL district readings where drought_risk >= min_level."""
    min_order = _RISK_ORDER.get(min_level, 2)
    latest = get_latest_all(db)
    return [
        loc for loc in latest
        if loc.location_type == "sri_lanka_district"
        and _RISK_ORDER.get(loc.drought_risk or "LOW", 0) >= min_order
    ]


# ── Heatwave ──────────────────────────────────────────────────────────────────

def consecutive_hot_days(db: Session, location_name: str, threshold_c: float, window: int = 3) -> int:
    """
    Counts distinct calendar days in the last `window` days where temperature exceeded threshold.
    Alert fires only when this returns >= 3 to avoid false positives from single-day spikes.
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=window)
    readings = (
        db.query(WeatherReading)
        .filter(
            WeatherReading.location_name == location_name,
            WeatherReading.timestamp >= cutoff,
            WeatherReading.temperature_c >= threshold_c,
        )
        .all()
    )
    return len({r.timestamp.date() for r in readings})


# ── Multi-day trend ───────────────────────────────────────────────────────────

def location_elevated_for_hours(
    db: Session,
    location_name: str,
    min_risk: str,
    hours: int,
) -> bool:
    """
    Returns True if every flood_risk reading in the last `hours` hours is at or above `min_risk`.
    Used to detect sustained deterioration before conditions peak — enables advance warning.
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    readings = (
        db.query(WeatherReading)
        .filter(
            WeatherReading.location_name == location_name,
            WeatherReading.timestamp >= cutoff,
        )
        .order_by(WeatherReading.timestamp)
        .all()
    )
    if not readings:
        return False
    return all(
        _RISK_ORDER.get(r.flood_risk or "LOW", 0) >= _RISK_ORDER.get(min_risk, 0)
        for r in readings
    )
