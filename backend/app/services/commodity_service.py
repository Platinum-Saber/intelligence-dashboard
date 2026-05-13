from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.commodities import CommodityPrice
from app.schemas.commodities import CommodityPriceOut, CommoditySummary


def get_latest(db: Session, symbol: str) -> CommodityPriceOut | None:
    row = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == symbol.upper())
        .order_by(CommodityPrice.timestamp.desc())
        .first()
    )
    return CommodityPriceOut.model_validate(row) if row else None


def get_history(db: Session, symbol: str, days: int = 30) -> list[CommodityPriceOut]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == symbol.upper(), CommodityPrice.timestamp >= since)
        .order_by(CommodityPrice.timestamp.asc())
        .all()
    )
    return [CommodityPriceOut.model_validate(r) for r in rows]


def get_summary(db: Session, symbol: str) -> CommoditySummary | None:
    rows_30d = get_history(db, symbol, days=30)
    rows_24h = get_history(db, symbol, days=1)

    if not rows_30d:
        return None

    prices = [r.price_usd for r in rows_30d]
    current = prices[-1]
    day_ago = rows_24h[0].price_usd if rows_24h else current
    change = current - day_ago

    return CommoditySummary(
        symbol=symbol.upper(),
        current_price_usd=current,
        change_24h=round(change, 2),
        change_24h_pct=round(change / day_ago * 100, 2) if day_ago else 0,
        high_30d=max(prices),
        low_30d=min(prices),
        avg_30d=round(sum(prices) / len(prices), 2),
    )
