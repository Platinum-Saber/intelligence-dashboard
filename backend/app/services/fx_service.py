from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.fx import FXRate
from app.schemas.fx import FXRateOut, FXSummary


def get_latest(db: Session) -> FXRateOut | None:
    row = db.query(FXRate).order_by(FXRate.timestamp.desc()).first()
    return FXRateOut.model_validate(row) if row else None


def get_history(db: Session, days: int = 30) -> list[FXRateOut]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(FXRate)
        .filter(FXRate.timestamp >= since)
        .order_by(FXRate.timestamp.asc())
        .all()
    )
    # Keep only the latest reading per calendar date so intraday scheduler
    # runs don't create duplicate x-axis points on charts.
    by_date: dict = {}
    for r in rows:
        by_date[r.timestamp.date()] = r
    deduped = sorted(by_date.values(), key=lambda r: r.timestamp)
    return [FXRateOut.model_validate(r) for r in deduped]


def rate_sustained_above(db: Session, threshold: float, hours: int) -> bool:
    """Returns True if every FX reading in the last `hours` hours exceeds `threshold`."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(FXRate).filter(FXRate.timestamp >= cutoff).all()
    if not readings:
        return False
    return all(r.usd_lkr > threshold for r in readings)


def get_summary(db: Session) -> FXSummary:
    rates_30d = get_history(db, days=30)
    rates_24h = get_history(db, days=1)

    if not rates_30d:
        return FXSummary(current=0, change_24h=0, change_24h_pct=0, high_30d=0, low_30d=0, avg_30d=0)

    prices = [r.usd_lkr for r in rates_30d]
    current = prices[-1]
    day_ago = rates_24h[0].usd_lkr if rates_24h else current
    change = current - day_ago

    return FXSummary(
        current=current,
        change_24h=round(change, 4),
        change_24h_pct=round(change / day_ago * 100, 2) if day_ago else 0,
        high_30d=max(prices),
        low_30d=min(prices),
        avg_30d=round(sum(prices) / len(prices), 4),
    )
