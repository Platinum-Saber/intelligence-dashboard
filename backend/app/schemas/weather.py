from pydantic import BaseModel
from datetime import datetime


class WeatherReadingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    timestamp: datetime
    location_type: str
    location_name: str
    rainfall_mm: float | None
    flood_risk: str | None
    temperature_c: float | None
    source: str | None


class WeatherLatest(BaseModel):
    location_name: str
    location_type: str
    timestamp: datetime
    rainfall_mm: float | None
    flood_risk: str
    temperature_c: float | None
