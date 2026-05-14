"""
Sprint 5.3 — SLFRS S2 climate event log aggregation.

Reads existing weather_readings and alert_events tables for a given date range
and returns structured summaries suitable for SLFRS S2 climate disclosure evidence.
"""
import csv
import io
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session


_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _risk_ge(risk: str | None, min_level: str) -> bool:
    if risk is None:
        return False
    return _RISK_ORDER.get(risk, 0) >= _RISK_ORDER.get(min_level, 0)


def generate_report(db: Session, start_date: date, end_date: date) -> dict:
    from app.models.weather import WeatherReading
    from app.models.alerts import AlertEvent

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    days_total = (end_date - start_date).days + 1

    # ── Flood risk days per Sri Lanka district (HIGH or CRITICAL) ─────────────
    flood_rows = (
        db.query(
            WeatherReading.location_name,
            func.date(WeatherReading.timestamp).label("day"),
        )
        .filter(
            WeatherReading.location_type == "sri_lanka_district",
            WeatherReading.timestamp >= start_dt,
            WeatherReading.timestamp <= end_dt,
            WeatherReading.flood_risk.in_(["HIGH", "CRITICAL"]),
        )
        .distinct()
        .all()
    )
    flood_days: dict[str, int] = {}
    for loc, _ in flood_rows:
        flood_days[loc] = flood_days.get(loc, 0) + 1

    # ── Drought risk days per Sri Lanka district (MEDIUM or above) ────────────
    drought_rows = (
        db.query(
            WeatherReading.location_name,
            func.date(WeatherReading.timestamp).label("day"),
        )
        .filter(
            WeatherReading.location_type == "sri_lanka_district",
            WeatherReading.timestamp >= start_dt,
            WeatherReading.timestamp <= end_dt,
            WeatherReading.drought_risk.in_(["MEDIUM", "HIGH", "CRITICAL"]),
        )
        .distinct()
        .all()
    )
    drought_days: dict[str, int] = {}
    for loc, _ in drought_rows:
        drought_days[loc] = drought_days.get(loc, 0) + 1

    # ── Temperature extremes per location ─────────────────────────────────────
    temp_rows = (
        db.query(
            WeatherReading.location_name,
            func.max(WeatherReading.temperature_c).label("max_t"),
            func.min(WeatherReading.temperature_c).label("min_t"),
        )
        .filter(
            WeatherReading.location_type == "sri_lanka_district",
            WeatherReading.timestamp >= start_dt,
            WeatherReading.timestamp <= end_dt,
            WeatherReading.temperature_c.isnot(None),
        )
        .group_by(WeatherReading.location_name)
        .all()
    )
    temp_extremes = [
        {"location": loc, "max_temp_c": round(max_t, 1), "min_temp_c": round(min_t, 1)}
        for loc, max_t, min_t in temp_rows
        if max_t is not None and min_t is not None
    ]

    # ── Supplier port disruption days (flood HIGH+) ───────────────────────────
    port_rows = (
        db.query(
            WeatherReading.location_name,
            func.date(WeatherReading.timestamp).label("day"),
        )
        .filter(
            WeatherReading.location_type == "supplier_port",
            WeatherReading.timestamp >= start_dt,
            WeatherReading.timestamp <= end_dt,
            WeatherReading.flood_risk.in_(["HIGH", "CRITICAL"]),
        )
        .distinct()
        .all()
    )
    port_days: dict[str, int] = {}
    for loc, _ in port_rows:
        port_days[loc] = port_days.get(loc, 0) + 1

    # ── Alert events by severity keyword ─────────────────────────────────────
    alert_rows = (
        db.query(AlertEvent)
        .filter(
            AlertEvent.triggered_at >= start_dt,
            AlertEvent.triggered_at <= end_dt,
        )
        .all()
    )
    severity_counts: dict[str, int] = {}
    for ev in alert_rows:
        sev = _classify_severity(ev.message)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days_total,
        },
        "alert_events_by_severity": severity_counts,
        "flood_risk_days_by_district": flood_days,
        "drought_risk_days_by_district": drought_days,
        "temperature_extremes": temp_extremes,
        "supplier_port_disruption_days": port_days,
    }


def _classify_severity(message: str) -> str:
    msg_lower = message.lower()
    if any(k in msg_lower for k in ["critical", "heatwave", "drought risk critical"]):
        return "Critical"
    if any(k in msg_lower for k in ["high", "flood risk high", "heatwave"]):
        return "High"
    if any(k in msg_lower for k in ["medium", "drought", "sustained"]):
        return "Medium"
    if any(k in msg_lower for k in ["buy window", "favourable", "dip"]):
        return "Favourable"
    return "Info"


def generate_csv(db: Session, start_date: date, end_date: date) -> str:
    """Return climate report as CSV string."""
    report = generate_report(db, start_date, end_date)
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["ACL Cables PLC — SLFRS S2 Climate Operational Evidence"])
    writer.writerow([f"Period: {report['period']['start_date']} to {report['period']['end_date']} ({report['period']['days']} days)"])
    writer.writerow([])

    writer.writerow(["== Alert Events by Severity =="])
    writer.writerow(["Severity", "Count"])
    for sev, count in report["alert_events_by_severity"].items():
        writer.writerow([sev, count])
    writer.writerow([])

    writer.writerow(["== Flood Risk Days (HIGH or CRITICAL) by District =="])
    writer.writerow(["District", "Days"])
    for loc, days in report["flood_risk_days_by_district"].items():
        writer.writerow([loc, days])
    writer.writerow([])

    writer.writerow(["== Drought Risk Days (MEDIUM or above) by District =="])
    writer.writerow(["District", "Days"])
    for loc, days in report["drought_risk_days_by_district"].items():
        writer.writerow([loc, days])
    writer.writerow([])

    writer.writerow(["== Temperature Extremes by Location =="])
    writer.writerow(["Location", "Max Temp (°C)", "Min Temp (°C)"])
    for t in report["temperature_extremes"]:
        writer.writerow([t["location"], t["max_temp_c"], t["min_temp_c"]])
    writer.writerow([])

    writer.writerow(["== Supplier Port Disruption Days (HIGH+ flood risk) =="])
    writer.writerow(["Port", "Days"])
    for port, days in report["supplier_port_disruption_days"].items():
        writer.writerow([port, days])

    return buf.getvalue()
