from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.news import NewsItemOut
from app.services import news_service

router = APIRouter()


@router.get("/", response_model=list[NewsItemOut])
def recent_news(
    days: int = Query(default=7, ge=1, le=90),
    topic: str | None = Query(default=None, description="FX | COPPER | ALUMINIUM | TRADE | LOGISTICS"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return news_service.get_recent(db, days=days, topic=topic, limit=limit)
