from pydantic import BaseModel
from datetime import datetime


class FXRateOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    timestamp: datetime
    usd_lkr: float
    source: str | None


class FXSummary(BaseModel):
    current: float
    change_24h: float
    change_24h_pct: float
    high_30d: float
    low_30d: float
    avg_30d: float
