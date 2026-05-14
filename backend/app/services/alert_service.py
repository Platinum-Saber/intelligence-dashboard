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
    from app.utils.seasonal_baseline import seasonal_context

    rules = db.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()
    triggered: list[tuple[AlertEvent, AlertRule]] = []

    # Fetch latest data once — get_summary covers both current rate and 24h change
    fx_summary = fx_service.get_summary(db)
    copper_summary = commodity_service.get_summary(db, "COPPER")
    aluminium_summary = commodity_service.get_summary(db, "ALUMINIUM")
    high_risk_weather = weather_service.get_high_risk(db)
    all_latest_weather = weather_service.get_latest_all(db)

    # Reference readings from 24h ago for landed cost calculation
    cutoff = datetime.utcnow() - timedelta(hours=24)
    fx_ref_row     = _price_before(db, FXRate, cutoff)
    cu_ref_row     = _price_before(db, CommodityPrice, cutoff, CommodityPrice.symbol == "COPPER")
    al_ref_row     = _price_before(db, CommodityPrice, cutoff, CommodityPrice.symbol == "ALUMINIUM")

    fx_ref = fx_ref_row.usd_lkr    if fx_ref_row else None
    cu_ref = cu_ref_row.price_usd  if cu_ref_row else None
    al_ref = al_ref_row.price_usd  if al_ref_row else None

    sl_districts = [loc for loc in all_latest_weather if loc.location_type == "sri_lanka_district"]

    for rule in rules:
        message: str | None = None

        # ── FX: absolute level (snapshot or sustained-window) ──────────────
        if rule.metric == "usd_lkr" and fx_summary and fx_summary.current:
            if rule.trend_window_hours:
                if rule.threshold_value is not None and fx_service.rate_sustained_above(
                    db, rule.threshold_value, rule.trend_window_hours
                ):
                    message = (
                        f"USD/LKR has remained above {rule.threshold_value} "
                        f"for {rule.trend_window_hours}h — sustained depreciation pressure "
                        f"(current: {fx_summary.current:.2f})"
                    )
            elif rule.threshold_value is not None and _compare(fx_summary.current, rule.comparison, rule.threshold_value):
                message = f"USD/LKR is {fx_summary.current} — {rule.comparison} threshold {rule.threshold_value}"

        # ── FX: 24h percentage change ──────────────────────────────────────
        elif rule.metric == "usd_lkr_change_pct" and fx_summary:
            if rule.threshold_value is not None and _compare(
                fx_summary.change_24h_pct, rule.comparison, rule.threshold_value
            ):
                message = (
                    f"USD/LKR moved {fx_summary.change_24h_pct:+.2f}% today "
                    f"(current: {fx_summary.current:.2f}) — "
                    f"{rule.comparison} threshold {rule.threshold_value}%"
                )

        # ── Commodity: landed cost 24h change ─────────────────────────────
        elif rule.metric == "copper_price" and copper_summary and fx_summary and cu_ref is not None and fx_ref is not None:
            result = _landed_cost_change_pct(copper_summary.current_price_usd, fx_summary.current, cu_ref, fx_ref)
            if result and rule.threshold_value is not None and _compare(result[0], rule.comparison, rule.threshold_value):
                change_pct, landed_now, landed_ref = result
                message = (
                    f"Copper landed cost 24h change: {change_pct:+.2f}% "
                    f"(LKR {landed_ref:,.0f}/t → LKR {landed_now:,.0f}/t) — "
                    f"{rule.comparison} threshold {rule.threshold_value}%"
                )

        elif rule.metric == "aluminium_price" and aluminium_summary and fx_summary and al_ref is not None and fx_ref is not None:
            result = _landed_cost_change_pct(aluminium_summary.current_price_usd, fx_summary.current, al_ref, fx_ref)
            if result and rule.threshold_value is not None and _compare(result[0], rule.comparison, rule.threshold_value):
                change_pct, landed_now, landed_ref = result
                message = (
                    f"Aluminium landed cost 24h change: {change_pct:+.2f}% "
                    f"(LKR {landed_ref:,.0f}/t → LKR {landed_now:,.0f}/t) — "
                    f"{rule.comparison} threshold {rule.threshold_value}%"
                )

        # ── Weather: flood risk (snapshot or sustained-window) ────────────
        elif rule.metric == "flood_risk" and rule.threshold_text:
            if rule.trend_window_hours:
                elevated = [
                    loc.location_name for loc in sl_districts
                    if weather_service.location_elevated_for_hours(
                        db, loc.location_name, rule.threshold_text, rule.trend_window_hours
                    )
                ]
                if elevated:
                    ctx = seasonal_context(elevated[0], datetime.utcnow().month)
                    message = (
                        f"Flood risk {rule.threshold_text} sustained for {rule.trend_window_hours}h in: "
                        f"{', '.join(elevated)} — logistics pre-positioning advised. {ctx}"
                    )
            else:
                flagged = [loc.location_name for loc in high_risk_weather if loc.flood_risk == rule.threshold_text]
                if flagged:
                    ctx = seasonal_context(flagged[0], datetime.utcnow().month)
                    message = f"Flood risk {rule.threshold_text} in: {', '.join(flagged)}. {ctx}"

        # ── Weather: drought risk ─────────────────────────────────────────
        elif rule.metric == "drought_risk" and rule.threshold_text:
            high_drought = weather_service.get_high_drought_risk(db, rule.threshold_text)
            if high_drought:
                locations = [loc.location_name for loc in high_drought]
                message = (
                    f"Drought risk {rule.threshold_text} in: {', '.join(locations)} — "
                    f"water stress may affect manufacturing operations"
                )

        # ── Weather: heatwave ─────────────────────────────────────────────
        elif rule.metric == "heatwave" and rule.threshold_value is not None:
            hot_locations = [
                loc.location_name for loc in sl_districts
                if weather_service.consecutive_hot_days(db, loc.location_name, rule.threshold_value) >= 3
            ]
            if hot_locations:
                message = (
                    f"Heatwave alert: ≥3 consecutive days above {rule.threshold_value}°C in: "
                    f"{', '.join(hot_locations)} — production setback risk"
                )

        # ── Sentiment ─────────────────────────────────────────────────────
        elif rule.metric == "news_sentiment" and rule.threshold_text:
            topic_part, *pct_part = rule.threshold_text.split(":")
            if pct_part:
                threshold_pct = float(pct_part[0])
                from app.services.sentiment_service import get_sentiment_summary
                summaries = get_sentiment_summary(db, days=1)
                for s in summaries:
                    if s["topic"] == topic_part.upper():
                        total = s["positive"] + s["negative"] + s["neutral"]
                        # Sprint 4.1: minimum article count guard — avoids 1/1=100% false alerts
                        if total < settings.sentiment_min_articles:
                            break
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
            triggered.append((event, rule))

    if triggered:
        db.commit()
        for event, rule in triggered:
            _try_notify(event, rule)

    return [event for event, _ in triggered]


def _try_notify(event: AlertEvent, rule: AlertRule) -> None:
    if not settings.smtp_user or not settings.alert_from_email:
        return
    # Sprint 4.1: read per-rule recipients; fall back to global sender address
    recipients = [r.strip() for r in (rule.email_recipients or "").split(",") if r.strip()]
    if not recipients:
        recipients = [settings.alert_from_email]
    try:
        msg = MIMEText(event.message)
        msg["Subject"] = f"[ACL Dashboard] Alert: {event.rule_name}"
        msg["From"] = settings.alert_from_email
        msg["To"] = ", ".join(recipients)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    except Exception:
        pass  # notification failure must never crash the check
