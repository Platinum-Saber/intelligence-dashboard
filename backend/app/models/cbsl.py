from sqlalchemy import Column, Integer, Float, String, Date
from app.database import Base


class CBSLRate(Base):
    __tablename__ = "cbsl_rates"

    id = Column(Integer, primary_key=True, index=True)
    effective_date = Column(Date, nullable=False, index=True)
    rate = Column(Float, nullable=False)
    note = Column(String(200), nullable=True)
