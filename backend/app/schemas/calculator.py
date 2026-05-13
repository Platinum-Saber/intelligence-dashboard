from pydantic import BaseModel


class CostHistoryPoint(BaseModel):
    date: str
    lme_price_usd: float
    usd_lkr: float
    landed_cost_lkr: float


class SentimentSummary(BaseModel):
    topic: str
    positive: int
    negative: int
    neutral: int
    unscored: int
    period_days: int
