from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base
from datetime import datetime


class CommodityPrice(Base):
    __tablename__ = "commodity_prices"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # COPPER | ALUMINIUM
    price_usd = Column(Float, nullable=False)
    unit = Column(String(20), default="per_tonne")
    source = Column(String(50))
