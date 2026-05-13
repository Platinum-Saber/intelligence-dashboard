from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text
from app.database import Base
from datetime import datetime


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), index=True)   # FX_THRESHOLD | COMMODITY_DIP | WEATHER_RISK
    metric = Column(String(50))                  # usd_lkr | copper_price | aluminium_price | flood_risk
    comparison = Column(String(10))              # lt | gt | eq
    threshold_value = Column(Float)
    threshold_text = Column(String(50))          # for text comparisons e.g. flood_risk = "HIGH"
    enabled = Column(Boolean, default=True)
    email_recipients = Column(Text)              # comma-separated


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    rule_id = Column(Integer, index=True)
    rule_name = Column(String(100))
    message = Column(Text)
    notified = Column(Boolean, default=False)
