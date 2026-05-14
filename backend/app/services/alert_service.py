import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models.alerts import AlertRule, AlertEvent
from app.schemas.alerts import AlertRuleIn, AlertRuleOut, AlertEventOut


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_rules(db: Session) -> list[AlertRuleOut]:
    rows = db.query(AlertRule).order_by(AlertRule.created_at).all()
    return [AlertRuleOut.model_validate(r) for r in rows]


def create_rule(db: Session, rule_in: AlertRuleIn) -> AlertRuleOut:
    rule = AlertRule(**rule_in.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return AlertRuleOut.model_validate(rule)


def update_rule(db: Session, rule_id: int, rule_in: AlertRuleIn) -> AlertRuleOut | None:
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        return None
    for field, value in rule_in.model_dump().items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return AlertRuleOut.model_validate(rule)


def delete_rule(db: Session, rule_id: int) -> bool:
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True


def list_events(db: Session, limit: int = 50) -> list[AlertEventOut]:
    rows = db.query(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(limit).all()
    return [AlertEventOut.model_validate(r) for r in rows]


# ── Rule evaluation ───────────────────────────────────────────────────────────

def _compare(value: float, comparison: str, threshold: float) -> bool:
    if comparison == "lt":
        return value < threshold
    if comparison == "gt":
        return value > threshold
    if comparison == "eq":
        return value == threshold
    return False


def _landed_cost_change_pct(
    price_now: float,
    fx_now: float,
    price_ref: float,
    fx_ref: float,
) -> tuple[float, float, float] | None:
    """
    Returns (change_pct, landed_cost_now_lkr, landed_cost_ref_lkr) or None.
    Landed cost = LME price (USD/t) × USD/LKR rate.
    """
    landed_now = price_now * fx_now
    landed_ref = price_ref * fx_ref
    if landed_ref == 0:
        return None
    change_pct = (landed_now - landed_ref) / landed_ref * 100
    return round(change_pct, 2), round(landed_now, 0), round(landed_ref, 0)


def _price_before(db: Session, model, cutoff: datetime, extra_filter=None) -> object | None:
    """Most recent row with timestamp <= cutoff."""
    q = db.query(model).filter(model.timestamp <= cutoff)
    if extra_filter is not None:
        q = q.filter(extra_filter)
    return q.order_by(model.timestamp.desc()).first()


def check_alerts(db: Session) -> list[AlertEvent]:
    """Evaluate all enabled rules against current data; persist triggered events."""
    from datetime import timedelta
    from app.services import fx_service, commodity_service, weather_service
    from app.models.fx import FXRate
    from app.models.commodities import CommodityPrice

    rules = db.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()
    triggered: list[AlertEvent] = []

    fx_latest = fx_service.get_latest(db)
    copper_summary = commodity_service.get_summary(db, "COPPER")
    aluminium_summary = commodity_service.get_summary(db, "ALUMINIUM")
    high_risk_weather = weather_service.get_high_risk(db)

    # Reference readings from 24h ago (most recent reading at or before that point)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    fx_ref_row     = _price_before(db, FXRate, cutoff)
    cu_ref_row     = _price_before(db, CommodityPrice, cutoff, CommodityPrice.symbol == "COPPER")
    al_ref_row     = _price_before(db, CommodityPrice, cutoff, CommodityPrice.symbol == "ALUMINIUM")

    fx_ref = fx_ref_row.usd_lkr    if fx_ref_row else None
    cu_ref = cu_ref_row.price_usd  if cu_ref_row else None
    al_ref = al_ref_row.price_usd  if al_ref_row else None

    for rule in rules:
        message: str | None = None

        if rule.metric == "usd_lkr" and fx_latest:
            if rule.threshold_value is not None and _compare(fx_latest.usd_lkr, rule.comparison, rule.threshold_value):
                message = f"USD/LKR is {fx_latest.usd_lkr} — {rule.comparison} threshold {rule.threshold_value}"

        elif rule.metric == "copper_price" and copper_summary and fx_latest and cu_ref is not None and fx_ref is not None:
            result = _landed_cost_change_pct(copper_summary.current_price_usd, fx_latest.usd_lkr, cu_ref, fx_ref)
            if result and rule.threshold_value is not None and _compare(result[0], rule.comparison, rule.threshold_value):
                change_pct, landed_now, landed_ref = result
                message = (
                    f"Copper landed cost 24h change: {change_pct:+.2f}% "
                    f"(LKR {landed_ref:,.0f}/t → LKR {landed_now:,.0f}/t) — "
                    f"{rule.comparison} threshold {rule.threshold_value}%"
                )

        elif rule.metric == "aluminium_price" and aluminium_summary and fx_latest and al_ref is not None and fx_ref is not None:
            result = _landed_cost_change_pct(aluminium_summary.current_price_usd, fx_latest.usd_lkr, al_ref, fx_ref)
            if result and rule.threshold_value is not None and _compare(result[0], rule.comparison, rule.threshold_value):
                change_pct, landed_now, landed_ref = result
                message = (
                    f"Aluminium landed cost 24h change: {change_pct:+.2f}% "
                    f"(LKR {landed_ref:,.0f}/t → LKR {landed_now:,.0f}/t) — "
                    f"{rule.comparison} threshold {rule.threshold_value}%"
                )

        elif rule.metric == "flood_risk" and rule.threshold_text:
            flagged = [loc.location_name for loc in high_risk_weather if loc.flood_risk == rule.threshold_text]
            if flagged:
                message = f"Flood risk {rule.threshold_text} in: {', '.join(flagged)}"

        elif rule.metric == "news_sentiment" and rule.threshold_text:
            # Trigger when a topic's negative score fraction exceeds a threshold
            # threshold_text = "COPPER:0.6" → 60% negative articles in last 24h
            topic_part, *pct_part = rule.threshold_text.split(":")
            if pct_part:
                threshold_pct = float(pct_part[0])
                from app.services.sentiment_service import get_sentiment_summary
                summaries = get_sentiment_summary(db, days=1)
                for s in summaries:
                    if s["topic"] == topic_part.upper():
                        total = s["positive"] + s["negative"] + s["neutral"]
                        if total > 0:
                            neg_pct = s["negative"] / total
                            if neg_pct >= threshold_pct:
                                message = (
                                    f"News sentiment warning: {topic_part} — "
                                    f"{s['negative']}/{total} articles negative "
                                    f"({neg_pct:.0%}) in last 24h"
                                )

        if message:
            event = AlertEvent(
                triggered_at=datetime.utcnow(),
                rule_id=rule.id,
                rule_name=rule.name,
                message=message,
                notified=False,
            )
            db.add(event)
            triggered.append(event)

    if triggered:
        db.commit()
        for event in triggered:
            _try_notify(event)

    return triggered


def _try_notify(event: AlertEvent) -> None:
    if not settings.smtp_user or not settings.alert_from_email:
        return
    try:
        msg = MIMEText(event.message)
        msg["Subject"] = f"[ACL Dashboard] Alert: {event.rule_name}"
        msg["From"] = settings.alert_from_email
        msg["To"] = settings.alert_from_email   # default; per-rule recipients in future
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    except Exception:
        pass  # notification failure must never crash the check
