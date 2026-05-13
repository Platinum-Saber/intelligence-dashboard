from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alerts import LandedCostRequest, LandedCostResponse
from app.services import fx_service, commodity_service

router = APIRouter()

_SYMBOL_MAP = {"COPPER": "COPPER", "ALUMINIUM": "ALUMINIUM"}


@router.post("/landed-cost", response_model=LandedCostResponse)
def landed_cost(req: LandedCostRequest, db: Session = Depends(get_db)):
    symbol = req.material.upper()
    if symbol not in _SYMBOL_MAP:
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
    total_lkr = round(total_usd * fx_rate, 2)

    return LandedCostResponse(
        material=symbol,
        quantity_tonnes=req.quantity_tonnes,
        lme_price_usd_per_tonne=lme_price,
        usd_lkr_rate=fx_rate,
        total_usd=total_usd,
        total_lkr=total_lkr,
        calculated_at=datetime.utcnow(),
    )
