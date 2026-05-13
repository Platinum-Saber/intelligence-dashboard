from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.news import NewsItem
from app.schemas.news import NewsItemOut

VALID_TOPICS = {"FX", "COPPER", "ALUMINIUM", "TRADE", "LOGISTICS"}


def get_recent(
    db: Session,
    days: int = 7,
    topic: str | None = None,
    limit: int = 50,
) -> list[NewsItemOut]:
    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(NewsItem).filter(NewsItem.published_at >= since)

    if topic and topic.upper() in VALID_TOPICS:
        q = q.filter(NewsItem.topic == topic.upper())

    rows = q.order_by(NewsItem.published_at.desc()).limit(limit).all()
    return [NewsItemOut.model_validate(r) for r in rows]
