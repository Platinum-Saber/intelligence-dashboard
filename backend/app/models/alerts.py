from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text
from app.database import Base
from datetime import datetime


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), index=True)   # FX_THRESHOLD | COMMODITY_DIP | WEATHER_RISK | SENTIMENT_NEGATIVE
    metric = Column(String(50))                  # usd_lkr | usd_lkr_change_pct | copper_price | aluminium_price | flood_risk | drought_risk | heatwave | news_sentiment
    comparison = Column(String(10))              # lt | gt | eq
    threshold_value = Column(Float)
    threshold_text = Column(String(50))          # for text comparisons e.g. flood_risk = "HIGH"
    enabled = Column(Boolean, default=True)
    email_recipients = Column(Text)              # comma-separated
    trend_window_hours = Column(Integer, nullable=True)  # sustained-condition window for FX and weather alerts


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    rule_id = Column(Integer, index=True)
    rule_name = Column(String(100))
    message = Column(Text)
    notified = Column(Boolean, default=False)
