from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alerts import LandedCostRequest, LandedCostResponse
from app.schemas.calculator import CostHistoryPoint
from app.services import fx_service, commodity_service

router = APIRouter()

_SYMBOLS = {"COPPER", "ALUMINIUM"}


@router.post("/landed-cost", response_model=LandedCostResponse)
def landed_cost(req: LandedCostRequest, db: Session = Depends(get_db)):
    symbol = req.material.upper()
    if symbol not in _SYMBOLS:
        raise HTTPException(400, "material must be COPPER or ALUMINIUM")

    lme_price = req.custom_lme_price_usd
    if lme_price is None:
        latest_commodity = commodity_service.get_latest(db, symbol)
        if not latest_commodity:
            raise HTTPException(404, f"No commodity data for {symbol}")
        lme_price = latest_commodity.price_usd

    fx_rate = req.custom_fx_rate
    if fx_rate is None:
        latest_fx = fx_service.get_latest(db)
        if not latest_fx:
            raise HTTPException(404, "No FX data available")
        fx_rate = latest_fx.usd_lkr

    total_usd = round(req.quantity_tonnes * lme_price, 2)
    return LandedCostResponse(
        material=symbol,
        quantity_tonnes=req.quantity_tonnes,
        lme_price_usd_per_tonne=lme_price,
        usd_lkr_rate=fx_rate,
        total_usd=total_usd,
        total_lkr=round(total_usd * fx_rate, 2),
        calculated_at=datetime.utcnow(),
    )


@router.get("/history", response_model=list[CostHistoryPoint])
def cost_history(
    material: str = Query(..., description="COPPER or ALUMINIUM"),
    quantity_tonnes: float = Query(default=50.0, gt=0, description="Order size in tonnes"),
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    symbol = material.upper()
    if symbol not in _SYMBOLS:
        raise HTTPException(400, "material must be COPPER or ALUMINIUM")

    since = datetime.utcnow() - timedelta(days=days)

    from app.models.commodities import CommodityPrice
    from app.models.fx import FXRate
    from datetime import date

    commodities = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == symbol, CommodityPrice.timestamp >= since)
        .order_by(CommodityPrice.timestamp.asc())
        .all()
    )
    fx_rows = (
        db.query(FXRate)
        .filter(FXRate.timestamp >= since)
        .order_by(FXRate.timestamp.asc())
        .all()
    )

    # Last FX reading per calendar day (ascending → last one wins)
    fx_by_date: dict[date, float] = {}
    for r in fx_rows:
        fx_by_date[r.timestamp.date()] = r.usd_lkr

    result: list[CostHistoryPoint] = []
    for c in commodities:
        day = c.timestamp.date()
        rate = fx_by_date.get(day)
        if rate is None:
            for offset in range(1, 8):
                rate = fx_by_date.get(day - timedelta(days=offset))
                if rate:
                    break
        if rate is None:
            continue
        result.append(CostHistoryPoint(
            date=str(day),
            lme_price_usd=c.price_usd,
            usd_lkr=rate,
            landed_cost_lkr=round(quantity_tonnes * c.price_usd * rate, 0),
        ))

    return result
