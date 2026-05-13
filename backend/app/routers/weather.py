from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.weather import WeatherReadingOut, WeatherLatest
from app.services import weather_service

router = APIRouter()


@router.get("/latest", response_model=list[WeatherLatest])
def latest_all(db: Session = Depends(get_db)):
    return weather_service.get_latest_all(db)


@router.get("/high-risk", response_model=list[WeatherLatest])
def high_risk(db: Session = Depends(get_db)):
    return weather_service.get_high_risk(db)


@router.get("/history", response_model=list[WeatherReadingOut])
def location_history(
    location: str = Query(..., description="Exact location_name value"),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return weather_service.get_history(db, location, days=days)
