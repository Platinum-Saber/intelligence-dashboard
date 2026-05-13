from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alerts import AlertRuleIn, AlertRuleOut, AlertEventOut
from app.services import alert_service

router = APIRouter()


@router.get("/rules", response_model=list[AlertRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return alert_service.list_rules(db)


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(rule_in: AlertRuleIn, db: Session = Depends(get_db)):
    return alert_service.create_rule(db, rule_in)


@router.put("/rules/{rule_id}", response_model=AlertRuleOut)
def update_rule(rule_id: int, rule_in: AlertRuleIn, db: Session = Depends(get_db)):
    result = alert_service.update_rule(db, rule_id, rule_in)
    if not result:
        raise HTTPException(404, "Rule not found")
    return result


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    if not alert_service.delete_rule(db, rule_id):
        raise HTTPException(404, "Rule not found")


@router.get("/events", response_model=list[AlertEventOut])
def list_events(limit: int = 50, db: Session = Depends(get_db)):
    return alert_service.list_events(db, limit=limit)


@router.post("/check", response_model=list[AlertEventOut])
def manual_check(db: Session = Depends(get_db)):
    return [AlertEventOut.model_validate(e) for e in alert_service.check_alerts(db)]
