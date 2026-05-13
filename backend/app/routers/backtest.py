from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.backtest import BacktestRequest, BacktestResult, ScenarioRunRequest, ScenarioRunResult, UATScenario
from app.services import backtest_service

router = APIRouter()


@router.post("/run", response_model=BacktestResult)
def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    days = (request.end_date - request.start_date).days
    if days > 730:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 2 years")
    return backtest_service.run_backtest(db, request)


@router.get("/scenarios", response_model=list[UATScenario])
def list_scenarios():
    return backtest_service.list_uat_scenarios()


@router.post("/scenario/run", response_model=ScenarioRunResult)
def run_scenario(request: ScenarioRunRequest, db: Session = Depends(get_db)):
    return backtest_service.run_scenario(db, request.conditions)
