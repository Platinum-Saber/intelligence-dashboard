from pydantic import BaseModel
from datetime import datetime


class AlertRuleIn(BaseModel):
    name: str
    rule_type: str
    metric: str
    comparison: str
    threshold_value: float | None = None
    threshold_text: str | None = None
    enabled: bool = True
    email_recipients: str = ""
    trend_window_hours: int | None = None
    composite_condition: str | None = None  # Sprint 5.4: JSON array of sub-conditions


class AlertRuleOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    created_at: datetime
    name: str
    rule_type: str
    metric: str
    comparison: str
    threshold_value: float | None
    threshold_text: str | None
    enabled: bool
    email_recipients: str | None
    trend_window_hours: int | None
    composite_condition: str | None  # Sprint 5.4


class AlertEventOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    triggered_at: datetime
    rule_id: int
    rule_name: str
    message: str
    notified: bool


class LandedCostRequest(BaseModel):
    material: str                       # COPPER | ALUMINIUM
    quantity_tonnes: float
    custom_lme_price_usd: float | None = None
    custom_fx_rate: float | None = None


class LandedCostResponse(BaseModel):
    material: str
    quantity_tonnes: float
    lme_price_usd_per_tonne: float
    usd_lkr_rate: float
    total_usd: float
    total_lkr: float
    calculated_at: datetime
