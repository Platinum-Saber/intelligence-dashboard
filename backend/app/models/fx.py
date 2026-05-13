from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base
from datetime import datetime


class FXRate(Base):
    __tablename__ = "fx_rates"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    usd_lkr = Column(Float, nullable=False)
    source = Column(String(50))
