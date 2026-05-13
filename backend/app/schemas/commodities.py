from pydantic import BaseModel
from datetime import datetime


class CommodityPriceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    timestamp: datetime
    symbol: str
    price_usd: float
    unit: str
    source: str | None


class CommoditySummary(BaseModel):
    symbol: str
    current_price_usd: float
    change_24h: float
    change_24h_pct: float
    high_30d: float
    low_30d: float
    avg_30d: float
