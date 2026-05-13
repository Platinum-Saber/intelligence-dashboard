from pydantic import BaseModel
from datetime import datetime


class NewsItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    published_at: datetime
    headline: str
    summary: str | None
    url: str | None
    source: str | None
    topic: str | None
    relevance_score: float | None
    sentiment: str | None
