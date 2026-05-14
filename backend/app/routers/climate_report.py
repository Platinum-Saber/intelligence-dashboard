"""Sprint 5.3 — SLFRS S2 climate event log export endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import climate_report_service

router = APIRouter()


@router.get("/report")
def climate_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    return climate_report_service.generate_report(db, start_date, end_date)


@router.get("/report/csv")
def climate_report_csv(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    csv_content = climate_report_service.generate_csv(db, start_date, end_date)
    filename = f"acl_climate_report_{start_date}_{end_date}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
