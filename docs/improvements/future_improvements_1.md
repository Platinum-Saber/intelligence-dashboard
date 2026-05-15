# ACL Cables Procurement Intelligence Dashboard — Future Improvements
## Climate, Exchange Rate & Intelligence Layer Enhancements

> **Purpose:** Documents post-Phase-3 improvement opportunities identified from two gap analyses: (1) the AR 2024/25 climate risk evidence (`climate_risk.md`) vs. the current weather implementation, and (2) the AR 2024/25 Exchange Rate Risk (#6) vs. the current FX/commodity/news implementation. Each item includes an implementation strategy scoped to the existing tech stack — no new infrastructure required unless stated.
>
> **Context:** Phase 4 is now complete. Items 1, 2, 3, 6, 7, 8, 10, and 11 have been implemented. Items 4, 5, 9, and 12 are planned for Phase 5.

---

## Gap Summary

### Climate / Weather Gaps

The current weather/climate layer collects `rainfall_mm`, `flood_risk`, and `temperature_c` from Open-Meteo across 13 locations every hour. Alerts fire on a point-in-time snapshot check (`flood_risk == "HIGH"`). Several climate risks formally documented in ACL's own AR are not yet covered:

| AR Risk | Currently Monitored | Gap | Phase 4 Status |
|---|---|---|---|
| Floods — Sri Lanka logistics | Yes (`flood_risk` field) | No trend/advance warning | ✅ `trend_window_hours` + `location_elevated_for_hours()` |
| Storms/cyclones — supplier ports | Partial (rainfall only) | No wind speed monitoring | Deferred (no Open-Meteo wind alert hook) |
| Heatwaves — production setbacks | No | `temperature_c` stored but no alert | ✅ `heatwave` metric + `consecutive_hot_days()` |
| Water scarcity/drought — manufacturing | No | Opposite of flood; not derived | ✅ `drought_risk` column + 14-day rolling deficit |
| SLFRS S1/S2 climate disclosures | No | No export layer | ⏳ Phase 5 (Item 4) |
| Cross-signal confluence (weather + FX + commodity) | No | Alerts are siloed | ⏳ Phase 5 (Item 5) |

### Exchange Rate Risk (#6) Gaps

Code-level analysis of `alert_service.py`, `fx_service.py`, `FXPanel.tsx`, and `calculator.py` identified the following gaps against the AR's Risk #6 requirements:

| Requirement | Implementation Status | Phase 4 Status |
|---|---|---|
| FX threshold alert | Done — `usd_lkr lt/gt threshold_value` | Unchanged |
| FX % change alert | Was missing | ✅ `usd_lkr_change_pct` metric wired into alert engine via `fx_service.get_summary()` |
| Multi-day FX trend signal | Was missing | ✅ `rate_sustained_above(db, threshold, hours)` in `fx_service.py`; shared `trend_window_hours` field on `AlertRule` |
| CBSL rate overlay on FX chart | Still not built | ⏳ Phase 5 (Item 9) |
| Per-rule email recipients | Was a bug | ✅ Fixed — `_try_notify(event, rule)` now reads `rule.email_recipients` with fallback |

### News / Sentiment Gaps

| Requirement | Implementation Status | Phase 4 Status |
|---|---|---|
| Geopolitical news monitoring | Done — FinBERT + topic filter | ✅ Min-article guard fixed (`SENTIMENT_MIN_ARTICLES`, default 5); applied in both `alert_service.py` and `backtest_service.py` |
| Topic classification accuracy | Collection-time only | ⏳ Phase 5 (Item 12) — keyword reclassification pass |
| Headline-level scoring | Done | ⏳ Phase 5 (Item 12) — summary concatenation for FinBERT |

---

## Improvement 1 — Drought & Water Stress Detection ✅ Phase 4 Complete

**AR evidence:** Risk #9 (Sustainability & Climate), C1 Chronic Physical Risks — *"Water is crucial in cable manufacturing for cooling, cleaning, and lubricating machinery. Water shortages can disrupt production efficiency, potentially leading to overheating and equipment malfunctions."*

**Problem:** The current `flood_risk` classifier is derived from excess rainfall. Drought is the opposite signal and is entirely absent from the alert engine, despite being a formally documented manufacturing continuity risk.

### Implementation Strategy

**Step 1 — Compute rolling rainfall deficit in `weather_service.py`**

Add a function that reads the last 14 days of `weather_readings` for a given district and computes the cumulative rainfall deficit against a seasonal baseline:

```python
def get_drought_risk(db: Session, location_name: str) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=14)
    readings = db.query(WeatherReading).filter(
        WeatherReading.location_name == location_name,
        WeatherReading.timestamp >= cutoff
    ).all()
    total_mm = sum(r.rainfall_mm for r in readings)
    # Sri Lanka baseline: ~5mm/day average outside dry season
    expected_mm = 14 * 5
    deficit_pct = max(0, (expected_mm - total_mm) / expected_mm)
    if deficit_pct >= 0.80: return "CRITICAL"
    if deficit_pct >= 0.60: return "HIGH"
    if deficit_pct >= 0.35: return "MEDIUM"
    return "LOW"
```

**Step 2 — Add `drought_risk` field to `WeatherReading` model**

```python
drought_risk = Column(String(20), nullable=True)  # LOW | MEDIUM | HIGH | CRITICAL
```

Populate it in the weather collector alongside the existing `flood_risk` field on each hourly write.

**Step 3 — Add `DROUGHT_RISK` alert rule type to the alert engine**

In `alert_service.py`, add a branch to the rule evaluator parallel to the existing `WEATHER_RISK` branch:

```python
elif rule.metric == "drought_risk":
    high_drought = weather_service.get_high_drought_risk(db)
    triggered = any(r["drought_risk"] == rule.threshold_text for r in high_drought)
```

**Step 4 — Surface in UI**

- Add a second map layer toggle in `WeatherMap` (Flood / Drought)
- Add `drought_risk` to the location tooltip
- Add `DROUGHT_RISK` as a selectable rule type in the alert rule creation dialog

**Effort:** ~1 day. No new APIs — Open-Meteo `precipitation_sum` is already collected.

---

## Improvement 2 — Heatwave Alert Rule ✅ Phase 4 Complete

**AR evidence:** C1 Acute Physical Risks — Heatwaves formally listed as causing *"production setbacks, decreased sales from damaged facilities."*

**Problem:** `temperature_c` is already stored in every `WeatherReading` row but is never used in the alert engine or displayed beyond the map tooltip.

### Implementation Strategy

**Step 1 — Add `HEATWAVE_RISK` rule type to `alert_service.py`**

```python
elif rule.metric == "heatwave":
    # rule.threshold_value = temperature in °C (e.g., 37.0)
    # rule.comparison = "gt"
    latest_wx = weather_service.get_all_latest(db)
    triggered = any(
        r.temperature_c is not None and r.temperature_c > rule.threshold_value
        for r in latest_wx
        if r.location_type == "sri_lanka_district"
    )
```

**Step 2 — Persist consecutive-day count for meaningful alerts**

A single hot day is not a heatwave. Add a helper that counts how many of the last N days exceeded the threshold for a given location:

```python
def consecutive_hot_days(db, location_name, threshold_c, window=3) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=window)
    readings = db.query(WeatherReading).filter(
        WeatherReading.location_name == location_name,
        WeatherReading.timestamp >= cutoff,
        WeatherReading.temperature_c >= threshold_c
    ).all()
    return len({r.timestamp.date() for r in readings})
```

Alert fires only when `consecutive_hot_days >= 3`. This avoids false positives from single-day temperature spikes.

**Step 3 — UI addition**

Add a temperature colour band to the weather map (blue-to-red scale) as an optional layer, and expose `HEATWAVE_RISK` in the alert rule type dropdown.

**Effort:** ~4 hours. All data already exists; only the evaluation logic and UI selector need adding.

---

## Improvement 3 — Multi-Day Trend Alerts ✅ Phase 4 Complete

**AR evidence:** Risk #4 (Operational Risk) — BCP requirement. Flood narrative: *"Disruptions to logistics network, delay deliveries, impact warehouse operations."* The procurement implication is that stock should be pre-positioned **before** a flood event peaks, not after.

**Problem:** The current alert engine evaluates a single snapshot every 15 minutes. It fires when a threshold is crossed — not when conditions are deteriorating toward a threshold. By the time the alert fires, the logistics window to pre-position stock may have already closed.

### Implementation Strategy

**Step 1 — Add trend evaluation to the alert rule schema**

Extend `AlertRule` with an optional `trend_window_hours` field (nullable integer). When set, the alert checks whether a condition has been `MEDIUM` or above for the entire window, rather than requiring a single `HIGH` reading:

```python
trend_window_hours = Column(Integer, nullable=True)  # e.g., 48
```

**Step 2 — Trend check function in `weather_service.py`**

```python
def location_elevated_for_hours(db, location_name, min_risk, hours) -> bool:
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    readings = db.query(WeatherReading).filter(
        WeatherReading.location_name == location_name,
        WeatherReading.timestamp >= cutoff
    ).order_by(WeatherReading.timestamp).all()
    if not readings:
        return False
    return all(risk_order.get(r.flood_risk, 0) >= risk_order[min_risk] for r in readings)
```

**Step 3 — Wire into alert evaluation**

If `rule.trend_window_hours` is set, call `location_elevated_for_hours` instead of the snapshot check. The alert message should include context: *"Western Province has been at MEDIUM flood risk for 52 consecutive hours — logistics pre-positioning advised."*

**Step 4 — UI**

Add an optional "Sustained for (hours)" input field in the alert rule creation dialog, visible only when rule type is `WEATHER_RISK`.

**Effort:** ~1 day. Schema migration + service logic + minor UI change.

---

## Improvement 4 — SLFRS S1/S2 Climate Event Log Export ⏳ Phase 5

**AR evidence:** C4 (p.32) — *"ACL Cables PLC is closely monitoring the developments [of SLFRS S1/S2]. We recognize the significant benefits of aligning our non-financial reporting with SLFRS S1 – General Requirements for Disclosure of Sustainability-related Financial Information, and SLFRS S2 – Climate-related Disclosures."*

**Problem:** The dashboard already captures the operational climate data (weather events, alert triggers, flood risk readings) that SLFRS S2 disclosures require. But there is no way to extract this data for the sustainability team — it lives only in the dashboard UI and the SQLite/PostgreSQL tables.

### Implementation Strategy

**Step 1 — New router: `app/routers/climate_report.py`**

```python
@router.get("/api/v1/climate/report")
def get_climate_report(
    start_date: date, end_date: date, db: Session = Depends(get_db)
):
    """Returns a structured climate event summary for a given period.
    Suitable for use as SLFRS S2 operational evidence."""
    return climate_report_service.generate(db, start_date, end_date)
```

**Step 2 — `climate_report_service.py` aggregations**

The report should return:
- Total weather alert events fired in period, by severity
- Days with HIGH or CRITICAL flood risk per district
- Days with drought risk above MEDIUM (once Improvement 1 is implemented)
- Temperature extremes per location
- Supplier port disruption days (any port at HIGH or above)

**Step 3 — CSV export endpoint**

```python
@router.get("/api/v1/climate/report/csv")
def download_climate_report(start_date: date, end_date: date, ...):
    data = climate_report_service.generate(db, start_date, end_date)
    # Stream as CSV using Python csv module + StreamingResponse
```

**Step 4 — UI tab in Configurations page**

Add a "Climate Report" tab to `ConfigPage` alongside the existing Data Sources tab. Provide a date range picker, a summary view, and a Download CSV button. Optionally include a note: *"This report can be submitted as operational evidence for SLFRS S2 climate disclosure."*

**Effort:** ~1.5 days. Primarily new service + router + one UI tab. No new data collection needed.

---

## Improvement 5 — Cross-Signal Composite Alerts ⏳ Phase 5

**AR evidence:** Risk #6 (Exchange Rate Risk) + Risk #9 (Climate Risk) + B5 (Supply Chain) — the AR's own evidence map shows these risks are causally linked: weather disruption at a supplier port → reduced raw material flow → commodity price pressure → LKR landed cost impact.

**Problem:** The current alert engine evaluates each rule independently. A procurement team member receives three separate alerts — one for weather, one for copper price, one for news sentiment — with no indication that they may be causally related and collectively more significant than any single signal.

### Implementation Strategy

**Step 1 — Add a `COMPOSITE` rule type**

Extend `AlertRule` with a `composite_condition` JSON field that specifies multiple sub-conditions:

```python
composite_condition = Column(Text, nullable=True)
# Stored as JSON: [{"metric": "flood_risk", "value": "HIGH"},
#                  {"metric": "copper_price_change_pct", "op": "gt", "value": 1.5}]
```

**Step 2 — Composite evaluator in `alert_service.py`**

```python
def evaluate_composite(rule, fx_data, copper_data, weather_data, sentiment_data) -> bool:
    conditions = json.loads(rule.composite_condition)
    return all(_eval_single(c, fx_data, copper_data, weather_data, sentiment_data)
               for c in conditions)
```

Each sub-condition reuses the same evaluation logic already written for individual rule types — no duplication.

**Step 3 — Richer alert message**

When a composite rule fires, the message should list which sub-conditions triggered and why they matter together:

> *"Composite alert: CRITICAL flood risk in Colombo Port District AND copper price up 2.1% in 24h AND LOGISTICS news sentiment 72% negative. Consider advancing copper order before port disruption affects availability."*

**Step 4 — UI**

Add a "Composite" rule type option in the alert rule dialog. When selected, show a dynamic list of sub-condition rows (metric + comparison + value), with an "Add condition" button. Each row mirrors the existing single-condition form fields.

**Effort:** ~2 days. Most complex of the six improvements — requires schema change, composite evaluator, and a more involved dialog UI.

---

## Improvement 6 — Seasonal / Monsoon Baseline Awareness ✅ Phase 4 Complete

**AR evidence:** The debug generators in `backend/debug/` already encode Sri Lanka's monsoon calendar (Southwest monsoon: May–September, Northeast monsoon: October–January). This domain knowledge is used for synthetic data generation but is absent from the live alert evaluation.

**Problem:** An alert firing for HIGH flood risk in October (peak Northeast monsoon in the North/East) carries different operational weight than the same reading in February. Without seasonal context, the alert engine produces the same message year-round — potentially desensitising the procurement team to genuinely anomalous events, or causing alert fatigue during expected seasonal peaks.

### Implementation Strategy

**Step 1 — `seasonal_baseline.py` utility module**

```python
MONSOON_CALENDAR = {
    "southwest": {"months": [5, 6, 7, 8, 9], "districts": ["Colombo", "Galle", "Kalutara", ...]},
    "northeast":  {"months": [10, 11, 12, 1],  "districts": ["Jaffna", "Trincomalee", "Batticaloa", ...]},
}

def is_monsoon_season(location_name: str, month: int) -> bool:
    for season in MONSOON_CALENDAR.values():
        if month in season["months"] and location_name in season["districts"]:
            return True
    return False

def seasonal_context(location_name: str, month: int) -> str:
    if is_monsoon_season(location_name, month):
        return "seasonal_expected"
    return "anomalous"
```

**Step 2 — Annotate alert event messages**

In `alert_service.py`, when writing an `AlertEvent`, append seasonal context to the message:

- If within monsoon season: *"[Seasonal context: rainfall elevated during expected Southwest Monsoon period — monitor for above-average intensity]"*
- If outside monsoon season: *"[Seasonal context: ANOMALOUS — flood risk elevated outside normal monsoon window. Investigate.]"*

**Step 3 — Severity uplift for anomalous events**

Optionally, allow anomalous-season alerts to be automatically escalated one severity level (e.g., a MEDIUM out-of-season alert is treated as HIGH for notification purposes). This is a configuration option, not a default.

**Step 4 — Alert event log UI**

Add a "Seasonal" badge to weather alert rows in the `AlertsPage` table — green for "expected seasonal" and red for "anomalous" — so the procurement team can immediately distinguish routine monsoon noise from genuine out-of-season events.

**Effort:** ~1 day. No schema changes; only message enrichment, a small utility module, and a UI badge.

---

---

## Improvement 7 — FX Percentage Change Alert ✅ Phase 4 Complete

**AR evidence:** Risk #6 — *"Volatility in USD/LKR exchange rates affecting the cost of imported raw materials."* The AR's own MDA attributes the 2.8pp gross margin improvement specifically to a 20-point FX swing (317 → 297) — a 6.3% move. A 6% move is the magnitude that matters; a fixed absolute threshold becomes stale as the rate drifts.

**Problem:** The commodity alert engine fires on `change_24h_pct` ([alert_service.py:84](../backend/app/services/alert_service.py)), but the FX alert fires on the raw `usd_lkr` value ([alert_service.py:80](../backend/app/services/alert_service.py)). `change_24h_pct` is already computed in `fx_service.get_summary()` — it is simply never wired into the alert evaluator. A procurement team that sets a threshold of `usd_lkr lt 295` will miss the signal entirely if the rate has drifted to a new range.

### Implementation Strategy

**Step 1 — Add `usd_lkr_change_pct` metric to the alert engine in `alert_service.py`**

The value is already available in the `FXSummary` object returned by `fx_service.get_summary()`:

```python
fx_summary = fx_service.get_summary(db)   # already called at check time

elif rule.metric == "usd_lkr_change_pct" and fx_summary:
    if rule.threshold_value is not None and _compare(fx_summary.change_24h_pct, rule.comparison, rule.threshold_value):
        message = (
            f"USD/LKR moved {fx_summary.change_24h_pct:+.2f}% today "
            f"(current: {fx_summary.current:.2f}) — "
            f"{rule.comparison} threshold {rule.threshold_value}%"
        )
```

Replace the current `get_latest()` call with `get_summary()` so both the absolute and the % change metrics are available from one DB query.

**Step 2 — Update `AlertRule` metric enum in frontend**

Add `usd_lkr_change_pct` to the metric selector in the alert rule creation dialog (`ConfigPage.tsx`), alongside the existing `usd_lkr` option. Label it *"USD/LKR Daily Change %"* to distinguish from the absolute level.

**Step 3 — Update `rule_type` labelling**

Keep the rule_type as `FX_THRESHOLD` — the new metric is just another FX threshold variant, not a new category. The severity colouring in `AlertsPage` will apply automatically.

**Effort:** ~2 hours. All data already exists; only the evaluator branch and the UI metric dropdown need updating.

---

## Improvement 8 — FX Multi-Day Sustained Pressure Alert ✅ Phase 4 Complete

**AR evidence:** Risk #6 mitigation actions state: *"Continuously monitor macroeconomic trends."* A single day above a threshold is noise; a week of sustained elevated rates is a structural signal that forward purchasing decisions should be made.

**Problem:** Identical to the climate multi-day trend gap (Improvement 3) but for FX. There is no way to configure a rule that fires when the rate has been above a level for N consecutive days — which is exactly the condition that would justify advancing a purchase order to lock in cost before further depreciation.

### Implementation Strategy

**Step 1 — Add `trend_window_hours` to `AlertRule` model**

This is the same field proposed in Improvement 3 for weather. Define it once on the model and both weather and FX evaluators can use it:

```python
# In models/alerts.py
trend_window_hours = Column(Integer, nullable=True)
```

**Step 2 — FX trend evaluator in `fx_service.py`**

```python
def rate_sustained_above(db: Session, threshold: float, hours: int) -> bool:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    readings = db.query(FXRate).filter(FXRate.timestamp >= cutoff).all()
    if not readings:
        return False
    return all(r.usd_lkr > threshold for r in readings)
```

**Step 3 — Wire into alert evaluator**

```python
if rule.metric == "usd_lkr" and rule.trend_window_hours:
    triggered = fx_service.rate_sustained_above(db, rule.threshold_value, rule.trend_window_hours)
    if triggered:
        message = (
            f"USD/LKR has remained above {rule.threshold_value} "
            f"for {rule.trend_window_hours}h — sustained depreciation pressure"
        )
```

When `trend_window_hours` is `None`, the existing snapshot logic runs unchanged — fully backwards compatible.

**Step 4 — UI**

Reuse the same "Sustained for (hours)" optional input added for weather trend alerts in Improvement 3. Show it when rule type is `FX_THRESHOLD`.

**Effort:** ~1 day (including Improvement 3 schema migration if done together).

---

## Improvement 9 — CBSL Rate Overlay on FX Chart ⏳ Phase 5

**AR evidence:** Risk #6 PEST analysis — *"Stability in exchange rates is essential for the industry's reliance on imported raw materials... supported by the government's commitment to the IMF-EFF program."* The CBSL (Central Bank of Sri Lanka) policy rate is a primary driver of USD/LKR movement; displaying it alongside the market rate gives the procurement team the context to distinguish market volatility from policy-driven moves.

**Problem:** `FXPanel.tsx` renders one series (the live USD/LKR rate) and one reference line (30d average). The CBSL reference rate overlay was listed as a planned chart feature in `project_detailes.md` but was never implemented. Without it, a sustained rate change is uninterpretable — the team cannot tell whether it reflects CBSL policy, market pressure, or IMF disbursement timing.

### Implementation Strategy

**Step 1 — CBSL data collection options (two approaches)**

*Option A — Manual entry (lowest effort):* Add a `cbsl_reference_rates` table with `effective_date` and `rate` columns. The CBSL announces rate changes infrequently (a few times per year). A simple form in the Configurations page lets an admin enter the new rate when the CBSL announces. No API required.

*Option B — CBSL API (if available):* The CBSL publishes exchange rate data at `www.cbsl.gov.lk`. Scraping or API access would automate this, but the endpoint reliability is unknown. Treat as a stretch goal; build Option A first.

**Step 2 — New DB model**

```python
class CBSLRate(Base):
    __tablename__ = "cbsl_rates"
    id = Column(Integer, primary_key=True)
    effective_date = Column(Date, nullable=False, index=True)
    rate = Column(Float, nullable=False)
    note = Column(String(200), nullable=True)  # e.g. "MPR cut 25bps"
```

**Step 3 — New API endpoint**

```python
GET /api/v1/fx/cbsl-history?days=90
# Returns list of {effective_date, rate, note}
```

**Step 4 — FXPanel chart overlay**

In `FXPanel.tsx`, fetch the CBSL history alongside the market rate history. Render as a second `Line` series (dashed, different colour — e.g., gold `var(--c-accent)`) on the same chart. Add a legend. Each CBSL entry spans from its `effective_date` to the next entry's date, creating a step-function appearance that clearly marks policy change boundaries.

**Effort:** ~1 day for Option A (manual entry + chart overlay). Option B adds 0.5–1 day depending on CBSL API accessibility.

---

## Improvement 10 — Sentiment Alert Minimum Article Count Guard ✅ Phase 4 Complete

**AR evidence:** Risk #2 (Country Risk) mitigation — automated news monitoring is only useful if it signals genuine events, not statistical noise from thin data days.

**Problem:** In `alert_service.py:105-113`, the sentiment rule fires when `neg_pct >= threshold_pct`. There is no minimum article count check. On low-news days (holidays, weekends), a single negative headline returns `1/1 = 100%` negative for a topic — indistinguishable from a genuine 80-article negative signal and far exceeding any threshold. This is a **bug**, not a design gap.

### Implementation Strategy

**Fix — Add a `min_articles` guard in `alert_service.py`**

The fix is two lines in the existing evaluator:

```python
# In alert_service.py, sentiment evaluation block
MIN_ARTICLES = 5   # configurable; tune based on observed daily volumes

for s in summaries:
    if s["topic"] == topic_part.upper():
        total = s["positive"] + s["negative"] + s["neutral"]
        if total < MIN_ARTICLES:          # ← add this guard
            continue
        neg_pct = s["negative"] / total
        if neg_pct >= threshold_pct:
            message = (...)
```

Make `MIN_ARTICLES` a configurable environment variable (`SENTIMENT_MIN_ARTICLES`, default `5`) so it can be tuned without a code change once real NewsAPI volumes are known.

Apply the same guard to `backtest_service.py:169` where identical sentiment logic is duplicated.

**UI addition:** Display the article count in the alert event message — e.g., *"COPPER: 14/20 articles negative (70%) in last 24h"* — so the procurement team can judge signal strength directly from the log. The message format already includes the count; it just needs the minimum check added before firing.

**Effort:** ~1 hour. Two files, two guard additions.

---

## Improvement 11 — Per-Rule Email Recipients (Bug Fix) ✅ Phase 4 Complete

**AR evidence:** Risk #6 mitigation — *"Maintain an adequate foreign currency reserve buffer."* Different alert types should reach different people: an FX threshold alert is relevant to the CFO and procurement lead; a flood risk alert is relevant to the logistics manager. Flat routing to one address undermines the alert system's operational value.

**Problem:** `AlertRule` has an `email_recipients` field (comma-separated string) in both the DB model and the Pydantic schema. However, `alert_service.py:140` ignores it entirely:

```python
# Current (broken):
msg["To"] = settings.alert_from_email   # always the same address
```

The `email_recipients` field is exposed in the alert rule CRUD UI but has no effect at runtime. This is a **bug**.

### Implementation Strategy

**Fix — Read `rule.email_recipients` in `_try_notify()`**

```python
def _try_notify(event: AlertEvent, rule: AlertRule) -> None:
    if not settings.smtp_user or not settings.alert_from_email:
        return
    recipients = [r.strip() for r in (rule.email_recipients or "").split(",") if r.strip()]
    if not recipients:
        recipients = [settings.alert_from_email]   # fallback to global default
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
        pass
```

Pass the `rule` object into `_try_notify()` from the `check_alerts()` call site. The `AlertEvent` already has `rule_id`; retrieve the rule once and pass it through.

**UI:** The `email_recipients` input already exists in the alert rule creation dialog. No UI change needed — the fix is entirely in the service layer.

**Effort:** ~30 minutes. Single function change in `alert_service.py`.

---

## Improvement 12 — Content-Based News Topic Classification ⏳ Phase 5

**AR evidence:** Risk #2 (Country Risk) — *"Negative impact arising due to adverse economic factors such as Political, Economic, Social, Technological, Environmental, and Legal."* Accurate topic tagging is the foundation of the sentiment signal: a misclassified article poisons the per-topic sentiment ratios that drive both the dashboard display and the alert rules.

**Problem:** In `news_collector.py`, topics are assigned at collection time based on which NewsAPI search query returned the article. An article about US-China tariffs that NewsAPI returns under a `COPPER` query is tagged `COPPER` regardless of content. FinBERT then scores its sentiment as a copper signal. The procurement team sees a distorted per-topic sentiment bar with no way to know whether it reflects genuine copper market sentiment or geopolitical spillover noise.

### Implementation Strategy

**Step 1 — Keyword reclassification pass after collection**

Add a lightweight post-collection step that scores each article's topic confidence using keyword matching against the headline and summary:

```python
TOPIC_KEYWORDS = {
    "FX":        ["exchange rate", "USD/LKR", "rupee", "forex", "CBSL", "currency"],
    "COPPER":    ["copper", "LME", "HG=F", "cathode", "wire rod"],
    "ALUMINIUM": ["aluminium", "aluminum", "ALI=F", "bauxite", "smelter"],
    "TRADE":     ["tariff", "trade war", "sanctions", "import ban", "WTO", "customs"],
    "LOGISTICS": ["shipping", "port", "freight", "supply chain", "container", "logistics"],
}

def reclassify_topic(headline: str, summary: str) -> str | None:
    text = (headline + " " + (summary or "")).lower()
    scores = {topic: sum(1 for kw in kws if kw.lower() in text)
              for topic, kws in TOPIC_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None   # None = keep original tag
```

Run this immediately after inserting each news item. If `reclassify_topic()` returns a non-None result with a score ≥ 2 keyword matches, overwrite the collection-time topic. If no keywords match (score < 2), retain the original collection-time tag.

**Step 2 — Score the summary, not just the headline**

Currently `sentiment_service.py:77` scores only `r.headline`. The `summary` field is collected and stored but never used for scoring. Concatenate headline and summary (truncated to 512 tokens) for a richer signal:

```python
text_to_score = f"{row.headline}. {row.summary or ''}"[:512]
```

Apply this change in `score_unscored_news()`. FinBERT's 512-token limit is unchanged; the concatenation simply gives the model more context when a summary is available.

**Step 3 — Backfill existing records**

Add a one-time migration endpoint `POST /api/v1/news/reclassify-all` that re-runs the keyword reclassifier over all stored news items. Run once after deployment; disable or remove thereafter.

**Effort:** ~1 day. Keyword dictionary + reclassifier function + one-line summary scoring change + optional backfill endpoint.

---

## Priority and Effort Summary

### Climate Improvements

| # | Improvement | AR Risk Covered | Effort | Status |
|---|---|---|---|---|
| 1 | Drought / water stress detection | Risk #9, C1 Chronic Physical | 1 day | ✅ Phase 4 |
| 2 | Heatwave alert rule | C1 Acute Physical | 4 hours | ✅ Phase 4 |
| 3 | Multi-day trend alerts (weather) | Risk #4 BCP, C1 Floods | 1 day | ✅ Phase 4 |
| 4 | SLFRS S1/S2 export | C4 Compliance | 1.5 days | ⏳ Phase 5 |
| 5 | Cross-signal composite alerts | Risk #6 + Risk #9 | 2 days | ⏳ Phase 5 |
| 6 | Seasonal monsoon baseline | Alert precision metric | 1 day | ✅ Phase 4 |

### Exchange Rate & Intelligence Layer

| # | Improvement | AR Risk Covered | Effort | Status |
|---|---|---|---|---|
| 7 | FX % change alert | Risk #6 Exchange Rate | 2 hours | ✅ Phase 4 |
| 8 | FX multi-day sustained pressure alert | Risk #6, forward purchasing | 1 day | ✅ Phase 4 |
| 9 | CBSL rate overlay on FX chart | Risk #6, PEST Economic | 1 day | ⏳ Phase 5 |
| 10 | Sentiment minimum article count guard | Risk #2, alert precision | 1 hour | ✅ Phase 4 |
| 11 | Per-rule email recipients (bug fix) | Risk #6 operational alerting | 30 min | ✅ Phase 4 |
| 12 | Content-based news topic classification | Risk #2 Country Risk | 1 day | ⏳ Phase 5 |

### Phase 4 Delivered (2026-05-14)

Items 1, 2, 3, 6, 7, 8, 10, 11 — all 8 planned Phase 4 improvements delivered. See `docs/implementation_details.md` v1.0 and `docs/phase4_phase5_plan.md` for the full decision log.

### Phase 5 Remaining (~5.5 days)

Items 4, 5, 9, 12 — see `docs/phase4_phase5_plan.md` for sprint breakdown and implementation strategies.

---

## What These Improvements Do Not Address

These items were considered and excluded from this document:

| Item | Reason |
|---|---|
| FX forecasting / prediction | USD/LKR is intervention-prone; framing as prediction erodes trust. Already documented as out-of-scope in `project_detailes.md`. |
| Commodity price ML prediction | Same rationale as FX; LME prices are driven by global macro forces outside scope. |
| Custom-trained climate NLP model | No labelled Sri Lankan procurement + climate corpus exists; FinBERT generalises adequately for signal detection. |
| Transition risk monitoring (carbon pricing, policy) | Strategic-level risk; no operational data feed exists at a granularity useful for procurement decisions. |
| Resus Energy PLC renewable output variability | Noted in `climate_risk.md` C2 as a dual-exposure point; would require separate energy-sector data feeds. |

---

*Document created: 2026-05-13 | Last updated: 2026-05-14 | Phase 4 complete — Phase 5 items (4, 5, 9, 12) remaining*
*Source analysis: `climate_risk.md`, `implementation_details.md`, `architecture.md`, `project_detailes.md`, `alert_service.py`, `fx_service.py`, `FXPanel.tsx`, `calculator.py`, `sentiment_service.py`, `news_service.py`*
*To be read alongside: `docs/implementation_details.md` for tech stack context*
