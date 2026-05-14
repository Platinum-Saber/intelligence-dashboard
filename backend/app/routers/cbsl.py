"""
CBSL reference rate endpoints.
Manual-entry only — CBSL announces rate changes a few times per year.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cbsl import CBSLRate

router = APIRouter()


class CBSLRateIn(BaseModel):
    effective_date: date
    rate: float
    note: str | None = None


class CBSLRateOut(BaseModel):
    id: int
    effective_date: date
    rate: float
    note: str | None

    model_config = {"from_attributes": True}


@router.get("/history", response_model=list[CBSLRateOut])
def cbsl_history(
    days: int = 90,
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(CBSLRate)
        .filter(CBSLRate.effective_date >= since)
        .order_by(CBSLRate.effective_date.asc())
        .all()
    )
    return rows


@router.get("/", response_model=list[CBSLRateOut])
def list_cbsl_rates(db: Session = Depends(get_db)):
    return db.query(CBSLRate).order_by(CBSLRate.effective_date.desc()).all()


@router.post("/", response_model=CBSLRateOut, status_code=201)
def create_cbsl_rate(body: CBSLRateIn, db: Session = Depends(get_db)):
    row = CBSLRate(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{rate_id}", response_model=CBSLRateOut)
def update_cbsl_rate(rate_id: int, body: CBSLRateIn, db: Session = Depends(get_db)):
    row = db.query(CBSLRate).filter(CBSLRate.id == rate_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="CBSL rate not found")
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{rate_id}", status_code=204)
def delete_cbsl_rate(rate_id: int, db: Session = Depends(get_db)):
    row = db.query(CBSLRate).filter(CBSLRate.id == rate_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="CBSL rate not found")
    db.delete(row)
    db.commit()
