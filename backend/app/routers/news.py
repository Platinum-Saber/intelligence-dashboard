from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.news import NewsItemOut
from app.schemas.calculator import SentimentSummary
from app.services import news_service, sentiment_service

router = APIRouter()


@router.get("/", response_model=list[NewsItemOut])
def recent_news(
    days: int = Query(default=7, ge=1, le=90),
    topic: str | None = Query(default=None, description="FX | COPPER | ALUMINIUM | TRADE | LOGISTICS"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return news_service.get_recent(db, days=days, topic=topic, limit=limit)


@router.get("/sentiment-summary", response_model=list[SentimentSummary])
def sentiment_summary(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return sentiment_service.get_sentiment_summary(db, days=days)


@router.post("/score-now", status_code=202)
def score_now(db: Session = Depends(get_db)):
    """Manually trigger FinBERT scoring of unscored news items."""
    scored = sentiment_service.score_unscored_news(db)
    return {"scored": scored}


@router.post("/reclassify-all", status_code=202)
def reclassify_all(db: Session = Depends(get_db)):
    """Sprint 5.1: backfill content-based topic reclassification for all existing articles."""
    updated = sentiment_service.reclassify_all_topics(db)
    return {"updated": updated}
