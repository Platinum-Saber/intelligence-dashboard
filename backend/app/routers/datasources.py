from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import datasource_service

router = APIRouter()


class DataSourceStatus(BaseModel):
    source_name: str
    status: str
    data_points_24h: int
    last_data_timestamp: datetime | None
    fragility_rating: str
    fragility_reason: str
    paid_fallback: str | None
    notes: str


class DataSourceAuditResult(BaseModel):
    sources: list[DataSourceStatus]
    audit_timestamp: datetime
    overall_health: str


@router.get("/audit", response_model=DataSourceAuditResult)
def get_audit(db: Session = Depends(get_db)):
    return datasource_service.get_datasource_audit(db)
