from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.fx import FXRateOut, FXSummary
from app.services import fx_service

router = APIRouter()


@router.get("/latest", response_model=FXRateOut)
def latest_rate(db: Session = Depends(get_db)):
    result = fx_service.get_latest(db)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(404, "No FX data available")
    return result


@router.get("/history", response_model=list[FXRateOut])
def rate_history(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return fx_service.get_history(db, days=days)


@router.get("/summary", response_model=FXSummary)
def rate_summary(db: Session = Depends(get_db)):
    return fx_service.get_summary(db)
