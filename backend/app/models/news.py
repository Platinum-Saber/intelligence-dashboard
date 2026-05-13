from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from app.database import Base
from datetime import datetime


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    headline = Column(String(500), nullable=False)
    summary = Column(Text)
    url = Column(String(500))
    source = Column(String(100))
    topic = Column(String(50), index=True)  # FX | COPPER | ALUMINIUM | LOGISTICS | TRADE
    relevance_score = Column(Float, default=0.5)
    sentiment = Column(String(20))          # POSITIVE | NEGATIVE | NEUTRAL — Phase 2
