"""
FinBERT-based sentiment scoring for news headlines.
Lazy-loaded on first use; gracefully no-ops if SENTIMENT_ENABLED=false
or if torch/transformers aren't available.
"""
import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import settings

if TYPE_CHECKING:
    from transformers import Pipeline

logger = logging.getLogger(__name__)

_pipeline: "Pipeline | None" = None
_load_attempted = False


def _get_pipeline() -> "Pipeline | None":
    global _pipeline, _load_attempted
    if not settings.sentiment_enabled:
        return None
    if _load_attempted:
        return _pipeline
    _load_attempted = True
    try:
        from transformers import pipeline as hf_pipeline
        logger.info("[sentiment] Loading FinBERT model (first run: downloads ~400 MB)…")
        _pipeline = hf_pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=-1,          # CPU
            truncation=True,
            max_length=512,
        )
        logger.info("[sentiment] FinBERT ready.")
    except Exception as exc:
        logger.error(f"[sentiment] FinBERT load failed — sentiment scoring disabled: {exc}")
        _pipeline = None
    return _pipeline


def score_text(text: str) -> tuple[str, float] | tuple[None, None]:
    """Return (label, confidence) or (None, None) if unavailable."""
    pipe = _get_pipeline()
    if pipe is None:
        return None, None
    try:
        result = pipe(text[:512])[0]
        # FinBERT labels: positive / negative / neutral
        return result["label"].upper(), round(result["score"], 3)
    except Exception as exc:
        logger.debug(f"[sentiment] Scoring failed: {exc}")
        return None, None


def score_unscored_news(db: Session, batch_size: int = 50) -> int:
    """Score news items that have no sentiment yet. Returns count processed."""
    from app.models.news import NewsItem

    pipe = _get_pipeline()
    if pipe is None:
        return 0

    rows = (
        db.query(NewsItem)
        .filter(NewsItem.sentiment.is_(None))
        .order_by(NewsItem.published_at.desc())
        .limit(batch_size)
        .all()
    )

    if not rows:
        return 0

    texts = [r.headline for r in rows]
    try:
        results = pipe(texts, truncation=True, max_length=512)
    except Exception as exc:
        logger.error(f"[sentiment] Batch scoring failed: {exc}")
        return 0

    for row, result in zip(rows, results):
        row.sentiment = result["label"].upper()

    db.commit()
    logger.info(f"[sentiment] Scored {len(rows)} news items.")
    return len(rows)


def get_sentiment_summary(db: Session, days: int = 7) -> list[dict]:
    """Aggregated sentiment counts per topic for the past N days."""
    from datetime import datetime, timedelta
    from app.models.news import NewsItem
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            NewsItem.topic,
            NewsItem.sentiment,
            func.count(NewsItem.id).label("cnt"),
        )
        .filter(NewsItem.published_at >= since, NewsItem.topic.isnot(None))
        .group_by(NewsItem.topic, NewsItem.sentiment)
        .all()
    )

    # Aggregate into {topic: {positive, negative, neutral, unscored}}
    by_topic: dict[str, dict] = {}
    for topic, sentiment, cnt in rows:
        if topic not in by_topic:
            by_topic[topic] = {"topic": topic, "positive": 0, "negative": 0, "neutral": 0, "unscored": 0, "period_days": days}
        key = sentiment.lower() if sentiment else "unscored"
        if key not in ("positive", "negative", "neutral"):
            key = "unscored"
        by_topic[topic][key] += cnt

    return list(by_topic.values())
