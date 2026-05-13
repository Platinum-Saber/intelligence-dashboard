from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.commodities import CommodityPriceOut, CommoditySummary
from app.services import commodity_service

router = APIRouter()

SYMBOLS = {"COPPER", "ALUMINIUM"}


def _validate_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s not in SYMBOLS:
        raise HTTPException(400, f"symbol must be one of {SYMBOLS}")
    return s


@router.get("/{symbol}/latest", response_model=CommodityPriceOut)
def latest_price(symbol: str, db: Session = Depends(get_db)):
    s = _validate_symbol(symbol)
    result = commodity_service.get_latest(db, s)
    if not result:
        raise HTTPException(404, f"No data for {s}")
    return result


@router.get("/{symbol}/history", response_model=list[CommodityPriceOut])
def price_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return commodity_service.get_history(db, _validate_symbol(symbol), days=days)


@router.get("/{symbol}/summary", response_model=CommoditySummary)
def price_summary(symbol: str, db: Session = Depends(get_db)):
    result = commodity_service.get_summary(db, _validate_symbol(symbol))
    if not result:
        raise HTTPException(404, f"No data for {symbol.upper()}")
    return result
