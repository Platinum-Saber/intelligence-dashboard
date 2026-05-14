from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel


# ── Backtesting ───────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    rule_ids: list[int] | None = None   # null = all enabled rules
    start_date: date
    end_date: date


class BacktestDayResult(BaseModel):
    date: date
    triggered_rules: list[str]
    alerts_fired: int
    fx_rate: float | None
    copper_price: float | None
    aluminium_price: float | None


class BacktestRuleSummary(BaseModel):
    rule_id: int
    rule_name: str
    rule_type: str
    total_fires: int
    fire_rate_pct: float
    first_fire_date: date | None
    last_fire_date: date | None


class BacktestResult(BaseModel):
    rule_summaries: list[BacktestRuleSummary]
    daily_results: list[BacktestDayResult]
    total_days: int
    total_alerts_fired: int
    start_date: date
    end_date: date


# ── UAT Scenarios ─────────────────────────────────────────────────────────────

class ScenarioSentimentTopic(BaseModel):
    positive: int
    negative: int
    neutral: int


class ScenarioConditions(BaseModel):
    usd_lkr: float
    usd_lkr_change_pct: float = 0.0
    copper_change_pct: float
    aluminium_change_pct: float
    high_risk_locations: list[str]
    drought_risk_locations: list[str] = []
    max_temp_c: float | None = None
    sentiment_by_topic: dict[str, ScenarioSentimentTopic]


class UATScenario(BaseModel):
    id: str
    name: str
    description: str
    conditions: ScenarioConditions


class ScenarioRunRequest(BaseModel):
    conditions: ScenarioConditions


class ScenarioFiredRule(BaseModel):
    rule_id: int
    rule_name: str
    rule_type: str
    message: str


class ScenarioRunResult(BaseModel):
    fired_rules: list[ScenarioFiredRule]
    total_fired: int
    conditions: ScenarioConditions
