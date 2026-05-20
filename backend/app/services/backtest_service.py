from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alerts import AlertRule
from app.models.commodities import CommodityPrice
from app.models.fx import FXRate
from app.models.news import NewsItem
from app.models.weather import WeatherReading
from app.schemas.backtest import (
    BacktestDayResult,
    BacktestRequest,
    BacktestResult,
    BacktestRuleSummary,
    ScenarioConditions,
    ScenarioFiredRule,
    ScenarioRunResult,
    UATScenario,
)


# ── Pre-defined UAT scenarios ─────────────────────────────────────────────────
#
# Scenarios cover all 7 live Phase-4 alert rules:
#   1. Copper Price Dip - Buy Window        (copper_price lt -2.0%)
#   2. Aluminium Price Dip - Buy Window     (aluminium_price lt -2.0%)
#   3. Sri Lanka Flood Risk                 (flood_risk eq HIGH)
#   4. FX Adverse Rate - LKR Weakening      (usd_lkr gt 330.0)
#   5. Sri Lanka Drought Risk               (drought_risk eq HIGH)
#   6. Sri Lanka Heatwave Risk              (heatwave gt 35.0 °C)
#   7. FX Daily Volatility                  (usd_lkr_change_pct gt 1.5%)
#
# For UAT scenarios FX is a point-in-time snapshot so landed-cost change % ==
# USD price change % (constant FX assumption within a single scenario).

UAT_SCENARIOS: list[dict] = [
    {
        "id": "aluminium_buy_window",
        "name": "Aluminium Buy Window",
        "description": (
            "LME Aluminium landed cost drops 3.5% in 24h following an LME price correction "
            "while FX holds steady. Tests whether the Aluminium buy-window alert fires and "
            "procurement is notified to lock in a favourable rate."
        ),
        "conditions": {
            "usd_lkr": 323.5,
            "usd_lkr_change_pct": 0.1,
            "copper_change_pct": -0.5,        # < 2 % — Rule 1 should NOT fire
            "aluminium_change_pct": -3.5,     # > 2 % drop — Rule 2 SHOULD fire
            "high_risk_locations": [],
            "drought_risk_locations": [],
            "max_temp_c": 29.0,
            "sentiment_by_topic": {
                "ALUMINIUM": {"positive": 20, "negative": 55, "neutral": 25},
                "TRADE": {"positive": 30, "negative": 40, "neutral": 30},
            },
        },
    },
    {
        "id": "copper_market_dip",
        "name": "Copper & Aluminium Market Dip",
        "description": (
            "LME Copper drops 5.4% and Aluminium drops 2.8% in landed-cost terms over 24h. "
            "Tests whether both commodity buy-window alerts fire simultaneously, signalling a "
            "broad metals correction and a joint procurement opportunity."
        ),
        "conditions": {
            "usd_lkr": 319.0,
            "usd_lkr_change_pct": -0.2,
            "copper_change_pct": -5.4,        # Rule 1 SHOULD fire
            "aluminium_change_pct": -2.8,     # Rule 2 SHOULD fire
            "high_risk_locations": [],
            "drought_risk_locations": [],
            "max_temp_c": 30.0,
            "sentiment_by_topic": {
                "COPPER": {"positive": 10, "negative": 72, "neutral": 18},
                "ALUMINIUM": {"positive": 12, "negative": 65, "neutral": 23},
                "TRADE": {"positive": 20, "negative": 50, "neutral": 30},
            },
        },
    },
    {
        "id": "monsoon_disruption",
        "name": "Monsoon Supply Chain Disruption",
        "description": (
            "Multiple Western Province districts reach HIGH flood risk during peak monsoon. "
            "Tests the weather-based logistics alert and validates that procurement is warned "
            "before port and road disruptions impact inbound shipments."
        ),
        "conditions": {
            "usd_lkr": 326.5,
            "usd_lkr_change_pct": 0.2,
            "copper_change_pct": 0.5,
            "aluminium_change_pct": 0.3,
            "high_risk_locations": ["Colombo", "Gampaha", "Kalutara"],   # Rule 3 SHOULD fire
            "drought_risk_locations": [],
            "max_temp_c": 27.0,
            "sentiment_by_topic": {
                "LOGISTICS": {"positive": 5, "negative": 78, "neutral": 17},
                "FX": {"positive": 35, "negative": 35, "neutral": 30},
            },
        },
    },
    {
        "id": "drought_heatwave",
        "name": "Drought & Heatwave Advisory",
        "description": (
            "Western Province records no significant rainfall for 3+ weeks and peak temperature "
            "reaches 38.5 °C — above the heatwave threshold. Tests whether the drought water-stress "
            "alert and the heatwave alert fire together, warning procurement of agricultural "
            "supply chain disruption and elevated labour/transport risk."
        ),
        "conditions": {
            "usd_lkr": 320.5,
            "usd_lkr_change_pct": -0.1,
            "copper_change_pct": 0.2,
            "aluminium_change_pct": 0.1,
            "high_risk_locations": [],
            "drought_risk_locations": ["Colombo", "Gampaha"],            # Rule 5 SHOULD fire
            "max_temp_c": 38.5,                                          # Rule 6 SHOULD fire (> 35 °C)
            "sentiment_by_topic": {
                "TRADE": {"positive": 28, "negative": 42, "neutral": 30},
                "FX": {"positive": 32, "negative": 38, "neutral": 30},
            },
        },
    },
    {
        "id": "fx_rate_shock",
        "name": "FX Rate Shock — LKR Under Pressure",
        "description": (
            "USD/LKR surges 2.3% in a single day, reaching 336. Tests both the sustained "
            "adverse-rate alert (usd_lkr > 330) and the daily volatility alert "
            "(change > 1.5%), validating that procurement is warned to hedge or defer "
            "non-urgent imports before the rupee weakens further."
        ),
        "conditions": {
            "usd_lkr": 336.0,                  # Rule 4 SHOULD fire (> 330)
            "usd_lkr_change_pct": 2.3,         # Rule 7 SHOULD fire (> 1.5 %)
            "copper_change_pct": 1.2,
            "aluminium_change_pct": 0.8,
            "high_risk_locations": [],
            "drought_risk_locations": [],
            "max_temp_c": 31.0,
            "sentiment_by_topic": {
                "FX": {"positive": 8, "negative": 70, "neutral": 22},
                "TRADE": {"positive": 15, "negative": 58, "neutral": 27},
            },
        },
    },
    {
        "id": "combined_peak_stress",
        "name": "Combined Peak Stress Event",
        "description": (
            "All seven alert categories activate simultaneously: USD/LKR at 338 with a 2.5% "
            "daily surge (both FX rules), copper down 2.8% and aluminium down 3.2% (buy windows), "
            "HIGH flood risk at three Western Province locations, drought stress in Colombo, "
            "and a 37.5 °C heatwave. Tests full system response under worst-case procurement stress."
        ),
        "conditions": {
            "usd_lkr": 338.0,                                            # Rule 4 SHOULD fire
            "usd_lkr_change_pct": 2.5,                                   # Rule 7 SHOULD fire
            "copper_change_pct": -2.8,                                   # Rule 1 SHOULD fire
            "aluminium_change_pct": -3.2,                                # Rule 2 SHOULD fire
            "high_risk_locations": ["Colombo", "Gampaha", "Ratnapura"],  # Rule 3 SHOULD fire
            "drought_risk_locations": ["Colombo"],                       # Rule 5 SHOULD fire
            "max_temp_c": 37.5,                                          # Rule 6 SHOULD fire
            "sentiment_by_topic": {
                "COPPER": {"positive": 8, "negative": 72, "neutral": 20},
                "ALUMINIUM": {"positive": 10, "negative": 68, "neutral": 22},
                "FX": {"positive": 5, "negative": 80, "neutral": 15},
                "LOGISTICS": {"positive": 12, "negative": 65, "neutral": 23},
            },
        },
    },
]


def list_uat_scenarios() -> list[UATScenario]:
    return [UATScenario(**s) for s in UAT_SCENARIOS]


# ── Core rule evaluation (historical snapshot) ────────────────────────────────

def _compare(value: float, comparison: str, threshold: float) -> bool:
    if comparison == "lt":
        return value < threshold
    if comparison == "gt":
        return value > threshold
    if comparison == "eq":
        return value == threshold
    return False


def _evaluate_rule_against_snapshot(
    rule: AlertRule,
    usd_lkr: float | None,
    usd_lkr_change_pct: float | None,
    # For UAT scenarios: copper/aluminium landed-cost change % (FX assumed constant,
    # so this equals the USD price change %).
    # For historical backtest: pre-computed (price_today*fx_today - price_prev*fx_prev)
    # / (price_prev*fx_prev) * 100.
    copper_landed_change_pct: float | None,
    aluminium_landed_change_pct: float | None,
    high_risk_locations: list[str],
    drought_risk_locations: list[str],
    max_temp_c: float | None,
    sentiment_by_topic: dict[str, dict[str, int]],
) -> str | None:
    """Return a trigger message if the rule fires, else None."""
    if rule.metric == "usd_lkr" and usd_lkr is not None:
        if rule.threshold_value is not None and _compare(usd_lkr, rule.comparison, rule.threshold_value):
            return f"USD/LKR is {usd_lkr:.2f} — {rule.comparison} threshold {rule.threshold_value}"

    elif rule.metric == "usd_lkr_change_pct" and usd_lkr_change_pct is not None:
        if rule.threshold_value is not None and _compare(usd_lkr_change_pct, rule.comparison, rule.threshold_value):
            return f"USD/LKR daily change: {usd_lkr_change_pct:+.2f}% — {rule.comparison} threshold {rule.threshold_value}%"

    elif rule.metric == "copper_price" and copper_landed_change_pct is not None:
        if rule.threshold_value is not None and _compare(copper_landed_change_pct, rule.comparison, rule.threshold_value):
            return f"Copper landed cost 24h change: {copper_landed_change_pct:+.2f}% — {rule.comparison} threshold {rule.threshold_value}%"

    elif rule.metric == "aluminium_price" and aluminium_landed_change_pct is not None:
        if rule.threshold_value is not None and _compare(aluminium_landed_change_pct, rule.comparison, rule.threshold_value):
            return f"Aluminium landed cost 24h change: {aluminium_landed_change_pct:+.2f}% — {rule.comparison} threshold {rule.threshold_value}%"

    elif rule.metric == "flood_risk" and rule.threshold_text and high_risk_locations:
        return f"Flood risk {rule.threshold_text} in: {', '.join(high_risk_locations)}"

    elif rule.metric == "drought_risk" and rule.threshold_text and drought_risk_locations:
        return f"Drought risk {rule.threshold_text} in: {', '.join(drought_risk_locations)}"

    elif rule.metric == "heatwave" and max_temp_c is not None:
        if rule.threshold_value is not None and _compare(max_temp_c, rule.comparison, rule.threshold_value):
            return f"Heatwave alert: temperature {max_temp_c:.1f} °C — {rule.comparison} threshold {rule.threshold_value} °C"

    elif rule.metric == "news_sentiment" and rule.threshold_text:
        topic_part, *pct_part = rule.threshold_text.split(":")
        if pct_part and topic_part in sentiment_by_topic:
            threshold_pct = float(pct_part[0])
            counts = sentiment_by_topic[topic_part]
            total = counts.get("positive", 0) + counts.get("negative", 0) + counts.get("neutral", 0)
            # Minimum article count guard — mirrors alert_service.py; avoids 1/1=100% false signals
            from app.config import settings
            if total < settings.sentiment_min_articles:
                return None
            if total > 0:
                neg_pct = counts.get("negative", 0) / total
                if neg_pct >= threshold_pct:
                    return (
                        f"News sentiment warning: {topic_part} — "
                        f"{counts.get('negative', 0)}/{total} articles negative "
                        f"({neg_pct:.0%}) in period"
                    )
    return None


# ── Backtesting ───────────────────────────────────────────────────────────────

def run_backtest(db: Session, request: BacktestRequest) -> BacktestResult:
    start_dt = datetime(request.start_date.year, request.start_date.month, request.start_date.day)
    end_dt = datetime(request.end_date.year, request.end_date.month, request.end_date.day, 23, 59, 59)
    lookback_dt = start_dt - timedelta(days=7)

    # Fetch all relevant data in one pass (avoid N+1 queries)
    all_fx = (
        db.query(FXRate)
        .filter(FXRate.timestamp >= lookback_dt, FXRate.timestamp <= end_dt)
        .order_by(FXRate.timestamp.asc())
        .all()
    )
    all_copper = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == "COPPER", CommodityPrice.timestamp >= lookback_dt, CommodityPrice.timestamp <= end_dt)
        .order_by(CommodityPrice.timestamp.asc())
        .all()
    )
    all_aluminium = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == "ALUMINIUM", CommodityPrice.timestamp >= lookback_dt, CommodityPrice.timestamp <= end_dt)
        .order_by(CommodityPrice.timestamp.asc())
        .all()
    )
    all_weather = (
        db.query(WeatherReading)
        .filter(WeatherReading.timestamp >= lookback_dt, WeatherReading.timestamp <= end_dt)
        .order_by(WeatherReading.timestamp.asc())
        .all()
    )
    all_news = (
        db.query(NewsItem)
        .filter(NewsItem.published_at >= lookback_dt, NewsItem.published_at <= end_dt)
        .order_by(NewsItem.published_at.asc())
        .all()
    )

    # Get rules
    rules_query = db.query(AlertRule)
    if request.rule_ids:
        rules_query = rules_query.filter(AlertRule.id.in_(request.rule_ids))
    rules = rules_query.all()

    rule_fire_counts: dict[int, int] = {r.id: 0 for r in rules}
    rule_fire_dates: dict[int, list[date]] = {r.id: [] for r in rules}
    daily_results: list[BacktestDayResult] = []

    current = request.start_date
    while current <= request.end_date:
        day_start = datetime(current.year, current.month, current.day, 0, 0, 0)
        day_end = datetime(current.year, current.month, current.day, 23, 59, 59)
        prev_day_end = day_start - timedelta(seconds=1)

        # Latest FX on or before day_end (with 7-day lookback)
        fx_for_day = None
        for rate in reversed(all_fx):
            if rate.timestamp <= day_end:
                fx_for_day = rate
                break

        # Commodity prices: today and previous day
        copper_today = copper_prev = None
        aluminium_today = aluminium_prev = None
        for price in reversed(all_copper):
            if price.timestamp <= day_end and copper_today is None:
                copper_today = price
            if price.timestamp <= prev_day_end and copper_prev is None:
                copper_prev = price
            if copper_today and copper_prev:
                break
        for price in reversed(all_aluminium):
            if price.timestamp <= day_end and aluminium_today is None:
                aluminium_today = price
            if price.timestamp <= prev_day_end and aluminium_prev is None:
                aluminium_prev = price
            if aluminium_today and aluminium_prev:
                break

        # FX for the previous day (most recent rate before day_start)
        fx_prev_day = None
        for rate in reversed(all_fx):
            if rate.timestamp <= prev_day_end:
                fx_prev_day = rate
                break
        fx_today_rate = fx_for_day.usd_lkr if fx_for_day else None
        fx_prev_rate = fx_prev_day.usd_lkr if fx_prev_day else fx_today_rate

        # Landed cost change % = (price_today * fx_today - price_prev * fx_prev)
        #                        / (price_prev * fx_prev) * 100
        copper_landed_change_pct = None
        if copper_today and copper_prev and fx_today_rate and fx_prev_rate:
            landed_now = copper_today.price_usd * fx_today_rate
            landed_ref = copper_prev.price_usd * fx_prev_rate
            if landed_ref > 0:
                copper_landed_change_pct = (landed_now - landed_ref) / landed_ref * 100

        aluminium_landed_change_pct = None
        if aluminium_today and aluminium_prev and fx_today_rate and fx_prev_rate:
            landed_now = aluminium_today.price_usd * fx_today_rate
            landed_ref = aluminium_prev.price_usd * fx_prev_rate
            if landed_ref > 0:
                aluminium_landed_change_pct = (landed_now - landed_ref) / landed_ref * 100

        # FX daily change %
        usd_lkr_change_pct = None
        if fx_today_rate and fx_prev_rate and fx_prev_rate > 0:
            usd_lkr_change_pct = (fx_today_rate - fx_prev_rate) / fx_prev_rate * 100

        # Latest weather per location on or before day_end
        weather_by_location: dict[str, WeatherReading] = {}
        for reading in all_weather:
            if reading.timestamp <= day_end:
                weather_by_location[reading.location_name] = reading

        high_risk_locations = [
            r.location_name for r in weather_by_location.values()
            if r.flood_risk in ("HIGH", "CRITICAL")
        ]
        drought_risk_locations = [
            r.location_name for r in weather_by_location.values()
            if r.drought_risk in ("HIGH", "CRITICAL")
        ]
        temps = [r.temperature_c for r in weather_by_location.values() if r.temperature_c is not None]
        max_temp_c = max(temps) if temps else None

        # Sentiment: news items within this day's window
        day_news = [n for n in all_news if day_start <= n.published_at <= day_end]
        sentiment_by_topic: dict[str, dict[str, int]] = {}
        for item in day_news:
            topic = item.topic or "UNKNOWN"
            if topic not in sentiment_by_topic:
                sentiment_by_topic[topic] = {"positive": 0, "negative": 0, "neutral": 0}
            label = (item.sentiment or "NEUTRAL").lower()
            sentiment_by_topic[topic][label] = sentiment_by_topic[topic].get(label, 0) + 1

        # Evaluate each rule
        triggered_names: list[str] = []
        for rule in rules:
            msg = _evaluate_rule_against_snapshot(
                rule,
                usd_lkr=fx_for_day.usd_lkr if fx_for_day else None,
                usd_lkr_change_pct=usd_lkr_change_pct,
                copper_landed_change_pct=copper_landed_change_pct,
                aluminium_landed_change_pct=aluminium_landed_change_pct,
                high_risk_locations=high_risk_locations,
                drought_risk_locations=drought_risk_locations,
                max_temp_c=max_temp_c,
                sentiment_by_topic=sentiment_by_topic,
            )
            if msg:
                triggered_names.append(rule.name)
                rule_fire_counts[rule.id] += 1
                rule_fire_dates[rule.id].append(current)

        daily_results.append(
            BacktestDayResult(
                date=current,
                triggered_rules=triggered_names,
                alerts_fired=len(triggered_names),
                fx_rate=round(fx_for_day.usd_lkr, 2) if fx_for_day else None,
                copper_price=round(copper_today.price_usd, 2) if copper_today else None,
                aluminium_price=round(aluminium_today.price_usd, 2) if aluminium_today else None,
            )
        )
        current += timedelta(days=1)

    total_days = (request.end_date - request.start_date).days + 1
    rule_summaries = [
        BacktestRuleSummary(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type or "",
            total_fires=rule_fire_counts[rule.id],
            fire_rate_pct=round(rule_fire_counts[rule.id] / total_days * 100, 1),
            first_fire_date=min(rule_fire_dates[rule.id]) if rule_fire_dates[rule.id] else None,
            last_fire_date=max(rule_fire_dates[rule.id]) if rule_fire_dates[rule.id] else None,
        )
        for rule in rules
    ]
    rule_summaries.sort(key=lambda x: x.total_fires, reverse=True)

    return BacktestResult(
        rule_summaries=rule_summaries,
        daily_results=daily_results,
        total_days=total_days,
        total_alerts_fired=sum(rule_fire_counts.values()),
        start_date=request.start_date,
        end_date=request.end_date,
    )


# ── Scenario runner ───────────────────────────────────────────────────────────

def run_scenario(db: Session, conditions: ScenarioConditions) -> ScenarioRunResult:
    rules = db.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()

    # Convert ScenarioSentimentTopic models to plain dicts
    sentiment_raw: dict[str, dict[str, int]] = {
        topic: {"positive": s.positive, "negative": s.negative, "neutral": s.neutral}
        for topic, s in conditions.sentiment_by_topic.items()
    }

    fired_rules: list[ScenarioFiredRule] = []
    for rule in rules:
        msg = _evaluate_rule_against_snapshot(
            rule,
            usd_lkr=conditions.usd_lkr,
            usd_lkr_change_pct=conditions.usd_lkr_change_pct,
            copper_landed_change_pct=conditions.copper_change_pct,
            aluminium_landed_change_pct=conditions.aluminium_change_pct,
            high_risk_locations=conditions.high_risk_locations,
            drought_risk_locations=conditions.drought_risk_locations,
            max_temp_c=conditions.max_temp_c,
            sentiment_by_topic=sentiment_raw,
        )
        if msg:
            fired_rules.append(
                ScenarioFiredRule(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type or "",
                    message=msg,
                )
            )

    return ScenarioRunResult(
        fired_rules=fired_rules,
        total_fired=len(fired_rules),
        conditions=conditions,
    )
