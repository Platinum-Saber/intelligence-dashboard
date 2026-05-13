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

UAT_SCENARIOS: list[dict] = [
    {
        "id": "fx_buying_window",
        "name": "FX Buying Window",
        "description": (
            "USD/LKR drops to 283 — a favourable import window. "
            "Tests whether FX threshold alerts fire correctly for proactive procurement."
        ),
        "conditions": {
            "usd_lkr": 283.0,
            "copper_change_pct": -0.3,
            "aluminium_change_pct": 0.1,
            "high_risk_locations": [],
            "sentiment_by_topic": {
                "FX": {"positive": 60, "negative": 15, "neutral": 25},
                "COPPER": {"positive": 45, "negative": 30, "neutral": 25},
            },
        },
    },
    {
        "id": "copper_market_dip",
        "name": "Copper Market Dip",
        "description": (
            "LME Copper drops 5.4% in 24h with negative market sentiment. "
            "Tests commodity dip alerts and whether the system flags a bulk buying opportunity."
        ),
        "conditions": {
            "usd_lkr": 308.5,
            "copper_change_pct": -5.4,
            "aluminium_change_pct": -1.2,
            "high_risk_locations": [],
            "sentiment_by_topic": {
                "COPPER": {"positive": 10, "negative": 72, "neutral": 18},
                "TRADE": {"positive": 20, "negative": 50, "neutral": 30},
            },
        },
    },
    {
        "id": "monsoon_disruption",
        "name": "Monsoon Supply Chain Disruption",
        "description": (
            "Multiple Western Province districts at HIGH flood risk during monsoon. "
            "Tests weather alerts and whether the logistics warning system activates."
        ),
        "conditions": {
            "usd_lkr": 304.0,
            "copper_change_pct": 0.5,
            "aluminium_change_pct": 0.3,
            "high_risk_locations": ["Colombo", "Gampaha", "Kalutara"],
            "sentiment_by_topic": {
                "LOGISTICS": {"positive": 5, "negative": 78, "neutral": 17},
                "FX": {"positive": 35, "negative": 35, "neutral": 30},
            },
        },
    },
    {
        "id": "geopolitical_alert",
        "name": "Geopolitical Supply Risk",
        "description": (
            "68% negative copper market news — simulates trade disruption in supplier countries. "
            "Tests sentiment-based alerts for early geopolitical warning."
        ),
        "conditions": {
            "usd_lkr": 313.0,
            "copper_change_pct": 2.2,
            "aluminium_change_pct": 1.7,
            "high_risk_locations": [],
            "sentiment_by_topic": {
                "COPPER": {"positive": 12, "negative": 68, "neutral": 20},
                "TRADE": {"positive": 8, "negative": 65, "neutral": 27},
                "LOGISTICS": {"positive": 15, "negative": 55, "neutral": 30},
            },
        },
    },
    {
        "id": "combined_risk_event",
        "name": "Combined Risk Event",
        "description": (
            "FX pressure (USD/LKR at 326), active flood risk, and strongly negative copper sentiment — "
            "all simultaneously. Tests whether all alert categories activate under peak stress."
        ),
        "conditions": {
            "usd_lkr": 326.0,
            "copper_change_pct": 3.8,
            "aluminium_change_pct": 2.9,
            "high_risk_locations": ["Colombo", "Gampaha", "Ratnapura"],
            "sentiment_by_topic": {
                "COPPER": {"positive": 8, "negative": 75, "neutral": 17},
                "FX": {"positive": 5, "negative": 80, "neutral": 15},
                "TRADE": {"positive": 10, "negative": 70, "neutral": 20},
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
    copper_change_pct: float | None,
    aluminium_change_pct: float | None,
    high_risk_locations: list[str],
    sentiment_by_topic: dict[str, dict[str, int]],
) -> str | None:
    """Return a trigger message if the rule fires, else None."""
    if rule.metric == "usd_lkr" and usd_lkr is not None:
        if rule.threshold_value is not None and _compare(usd_lkr, rule.comparison, rule.threshold_value):
            return f"USD/LKR is {usd_lkr:.2f} — {rule.comparison} threshold {rule.threshold_value}"

    elif rule.metric == "copper_price" and copper_change_pct is not None:
        if rule.threshold_value is not None and _compare(copper_change_pct, rule.comparison, rule.threshold_value):
            return f"Copper 24h change: {copper_change_pct:.2f}% — {rule.comparison} threshold {rule.threshold_value}%"

    elif rule.metric == "aluminium_price" and aluminium_change_pct is not None:
        if rule.threshold_value is not None and _compare(aluminium_change_pct, rule.comparison, rule.threshold_value):
            return f"Aluminium 24h change: {aluminium_change_pct:.2f}% — {rule.comparison} threshold {rule.threshold_value}%"

    elif rule.metric == "flood_risk" and rule.threshold_text and high_risk_locations:
        matching = [loc for loc in high_risk_locations]
        if matching:
            return f"Flood risk {rule.threshold_text} in: {', '.join(matching)}"

    elif rule.metric == "news_sentiment" and rule.threshold_text:
        topic_part, *pct_part = rule.threshold_text.split(":")
        if pct_part and topic_part in sentiment_by_topic:
            threshold_pct = float(pct_part[0])
            counts = sentiment_by_topic[topic_part]
            total = counts.get("positive", 0) + counts.get("negative", 0) + counts.get("neutral", 0)
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

        copper_change_pct = None
        if copper_today and copper_prev and copper_prev.price_usd > 0:
            copper_change_pct = (copper_today.price_usd - copper_prev.price_usd) / copper_prev.price_usd * 100

        aluminium_change_pct = None
        if aluminium_today and aluminium_prev and aluminium_prev.price_usd > 0:
            aluminium_change_pct = (aluminium_today.price_usd - aluminium_prev.price_usd) / aluminium_prev.price_usd * 100

        # Latest weather per location on or before day_end
        weather_by_location: dict[str, WeatherReading] = {}
        for reading in all_weather:
            if reading.timestamp <= day_end:
                weather_by_location[reading.location_name] = reading

        high_risk_locations = [
            r.location_name for r in weather_by_location.values()
            if r.flood_risk in ("HIGH", "CRITICAL")
        ]

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
                copper_change_pct=copper_change_pct,
                aluminium_change_pct=aluminium_change_pct,
                high_risk_locations=high_risk_locations,
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
            copper_change_pct=conditions.copper_change_pct,
            aluminium_change_pct=conditions.aluminium_change_pct,
            high_risk_locations=conditions.high_risk_locations,
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
