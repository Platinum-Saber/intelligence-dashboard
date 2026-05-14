from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base
from datetime import datetime


class WeatherReading(Base):
    __tablename__ = "weather_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    location_type = Column(String(30))   # sri_lanka_district | supplier_port
    location_name = Column(String(100), index=True)
    rainfall_mm = Column(Float)
    flood_risk = Column(String(20))       # LOW | MEDIUM | HIGH | CRITICAL
    drought_risk = Column(String(20), nullable=True)  # LOW | MEDIUM | HIGH | CRITICAL
    temperature_c = Column(Float)
    source = Column(String(50))
