# ACL Cables Procurement Intelligence Dashboard
## Phase 4 & Phase 5 Implementation Plan

> **Purpose:** Defines the scope, sequencing, and implementation strategy for Phase 4 and Phase 5 of the dashboard. All improvements are drawn from the gap analysis in `future_improvements.md`. Phases 1–3 are complete; this document picks up from that baseline.
>
> **Read alongside:** `future_improvements.md` (full implementation strategies), `implementation_details.md` (tech stack), `project_detailes.md` (project context).

---

## Document History

| Version | Date | Change Summary |
|---------|------|----------------|
| 1.0 | 2026-05-14 | Initial plan — Phase 4 and Phase 5 scoped from `future_improvements.md` gap analysis |
| 1.1 | 2026-05-14 | Phase 4 complete — all 8 items delivered plus additional UI bug fixes and UAT overhaul; see `implementation_details.md` v1.0 for full decision log |
| 1.2 | 2026-05-14 | Phase 5 complete — all 4 sprints delivered; additional fixes: buyer-perspective sentiment, NewsAPI rate-limit optimisation, 7-day startup backfill, weather map height; see `implementation_details.md` v1.1 for full decision log |

---

## Guiding Principles

1. **Bug fixes before enhancements.** Two known bugs (Improvements 10 and 11) corrupt alert output today. Fix these first.
2. **Schema changes are batched.** `trend_window_hours` on `AlertRule` is needed by both Improvement 3 (weather) and Improvement 8 (FX). One migration covers both.
3. **Phase 4 strengthens existing signals; Phase 5 builds new layers.** Phase 4 makes the alert engine more reliable and complete. Phase 5 adds net-new capabilities (composite intelligence, compliance export, CBSL context).
4. **No new infrastructure required.** All work uses the existing stack: FastAPI, SQLAlchemy, APScheduler, React/TypeScript, Recharts, Open-Meteo, FinBERT.

---

## Phase 4 — Alert Reliability & Enhanced Intelligence

**Theme:** Close the reliability gaps in the current alert engine, complete the FX alerting surface, and add the missing climate risk signals. By the end of Phase 4, every formally documented AR risk with available data is covered, and known alert bugs are eliminated.

**Total estimated effort:** ~6 days

---

### Sprint 4.1 — Bug Fixes (Priority: Critical | Effort: ~2 hours)

These are correctness bugs in the live alerting path. They affect every alert fired today and must be resolved before any new features are added.

#### Item 10 — Sentiment Alert Minimum Article Count Guard

**File:** `backend/app/services/alert_service.py` (lines ~105–113), `backend/app/services/backtest_service.py` (line ~169)

**Problem:** On low-traffic days (weekends, holidays), a single negative article produces `1/1 = 100%` negative sentiment — indistinguishable from a genuine bulk-negative signal. Any threshold is exceeded, firing a false alert.

**Fix:**
- Add a `MIN_ARTICLES` guard (default: 5, configurable via `SENTIMENT_MIN_ARTICLES` env var) before the `neg_pct` check in `alert_service.py`.
- Apply the identical guard to the duplicated sentiment logic in `backtest_service.py`.
- Include article count in the alert message: *"COPPER: 14/20 articles negative (70%) in last 24h"*.

```
Files changed: alert_service.py, backtest_service.py
DB changes: none
```

---

#### Item 11 — Per-Rule Email Recipients (Bug Fix)

**File:** `backend/app/services/alert_service.py` (line ~140)

**Problem:** `AlertRule.email_recipients` is exposed in the CRUD UI but `_try_notify()` hardcodes `settings.alert_from_email`, making per-rule routing entirely non-functional.

**Fix:**
- In `_try_notify()`, read `rule.email_recipients`; split on comma; fall back to `settings.alert_from_email` only when the field is empty.
- Pass the `rule` object into `_try_notify()` from the `check_alerts()` call site (it already has `rule_id`; retrieve the rule once and thread it through).
- No UI change needed — the input field already exists in the alert rule creation dialog.

```
Files changed: alert_service.py
DB changes: none
```

---

### Sprint 4.2 — FX Alert Enhancements (Priority: High | Effort: ~1.5 days)

Closes the two FX alerting gaps identified against AR Risk #6.

#### Item 7 — FX Percentage Change Alert

**Files:** `backend/app/services/alert_service.py`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** `change_24h_pct` is already computed by `fx_service.get_summary()` but is never wired into the alert evaluator. Alert fires on absolute `usd_lkr` level only; a fixed threshold becomes stale as the rate drifts.

**Steps:**
1. In `alert_service.py`, add an `elif rule.metric == "usd_lkr_change_pct"` branch. Use the `FXSummary` object (already retrieved) to evaluate against `change_24h_pct`.
2. Replace the existing `get_latest()` call with `get_summary()` so both absolute and % change are available from one query.
3. In `ConfigPage.tsx`, add `usd_lkr_change_pct` to the metric selector. Label: *"USD/LKR Daily Change %"*.
4. Keep rule type as `FX_THRESHOLD` — no new category needed.

```
Files changed: alert_service.py, ConfigPage.tsx
DB changes: none
```

---

#### Item 8 — FX Multi-Day Sustained Pressure Alert

**Files:** `backend/app/models/alerts.py`, `backend/app/services/alert_service.py`, `backend/app/services/fx_service.py`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** No way to alert when USD/LKR has been above a level for N consecutive days — the condition that would justify advancing a purchase order to lock in cost.

**Steps:**
1. Add `trend_window_hours = Column(Integer, nullable=True)` to `AlertRule` in `models/alerts.py`. **(Shared with Item 3 — do this migration once.)**
2. Add `rate_sustained_above(db, threshold, hours) -> bool` to `fx_service.py`. Queries `FXRate` rows in the window; returns `True` only if all readings exceed the threshold.
3. In `alert_service.py`, when `rule.metric == "usd_lkr"` and `rule.trend_window_hours` is set, call `rate_sustained_above` instead of the snapshot check. Backwards-compatible: existing rules with `trend_window_hours = NULL` run unchanged.
4. In `ConfigPage.tsx`, add an optional *"Sustained for (hours)"* number input to the alert rule dialog. Show it when rule type is `FX_THRESHOLD`. (Reused verbatim for weather in Item 3.)

```
Files changed: models/alerts.py, fx_service.py, alert_service.py, ConfigPage.tsx
DB changes: ALTER TABLE alert_rules ADD COLUMN trend_window_hours INTEGER (nullable)
```

---

### Sprint 4.3 — Climate Alert Enhancements (Priority: High | Effort: ~3 days)

Addresses the four climate signal gaps against AR Risk #9 (C1 Acute/Chronic Physical Risks). All changes touch `weather_service.py` and `alert_service.py` — batch them to minimise integration surface.

#### Item 1 — Drought & Water Stress Detection

**Files:** `backend/app/models/weather.py`, `backend/app/services/weather_service.py`, `backend/app/services/alert_service.py`, weather map component

**Problem:** Drought is a formally documented manufacturing continuity risk (water used in cooling, cleaning, lubricating). Only flood risk is currently monitored; drought is the opposite signal and is entirely absent.

**Steps:**
1. Add `drought_risk = Column(String(20), nullable=True)` to `WeatherReading`.
2. Add `get_drought_risk(db, location_name) -> str` to `weather_service.py`. Reads last 14 days of `rainfall_mm`; computes deficit against 5 mm/day baseline (Sri Lanka outside dry season); returns `LOW / MEDIUM / HIGH / CRITICAL`.
3. Populate `drought_risk` in the hourly weather collector alongside the existing `flood_risk`.
4. Add `elif rule.metric == "drought_risk"` branch to `alert_service.py`.
5. Add a Drought layer toggle to the weather map component and `drought_risk` to location tooltips.
6. Add `DROUGHT_RISK` to the alert rule type dropdown in `ConfigPage.tsx`.

```
Files changed: weather.py (model), weather_service.py, alert_service.py, WeatherMap component, ConfigPage.tsx
DB changes: ALTER TABLE weather_readings ADD COLUMN drought_risk VARCHAR(20)
```

---

#### Item 2 — Heatwave Alert Rule

**Files:** `backend/app/services/alert_service.py`, `backend/app/services/weather_service.py`, weather map component, `frontend/src/pages/ConfigPage.tsx`

**Problem:** `temperature_c` is stored in every `WeatherReading` row but is never evaluated. Heatwaves are formally listed as causing production setbacks.

**Steps:**
1. Add `consecutive_hot_days(db, location_name, threshold_c, window=3) -> int` to `weather_service.py`. Counts distinct calendar days in the last N days where temperature exceeded the threshold.
2. Add `elif rule.metric == "heatwave"` to `alert_service.py`. Alert fires only when `consecutive_hot_days >= 3` for any Sri Lanka district.
3. Add a temperature colour band (blue→red) as an optional layer on the weather map.
4. Add `HEATWAVE_RISK` to the rule type dropdown.

```
Files changed: weather_service.py, alert_service.py, WeatherMap component, ConfigPage.tsx
DB changes: none (temperature_c already stored)
```

---

#### Item 3 — Multi-Day Trend Alerts (Weather)

**Files:** `backend/app/services/weather_service.py`, `backend/app/services/alert_service.py`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** Alerts fire on a single-snapshot `flood_risk == HIGH` check. By the time this fires, the logistics window to pre-position stock may already be closed. A trend alert fires earlier, when conditions have been elevated for hours — giving the team time to act.

**Steps:**
1. `trend_window_hours` schema change is already done in Item 8 — no additional migration.
2. Add `location_elevated_for_hours(db, location_name, min_risk, hours) -> bool` to `weather_service.py`. Reads all readings in the window; returns `True` only if every reading is at or above `min_risk`.
3. In the `WEATHER_RISK` evaluator block in `alert_service.py`, check `rule.trend_window_hours`: if set, call `location_elevated_for_hours` instead of the snapshot check.
4. Alert message context: *"Western Province has been at MEDIUM flood risk for 52 consecutive hours — logistics pre-positioning advised."*
5. The *"Sustained for (hours)"* input added in Item 8 is already visible for `WEATHER_RISK` rule type — no additional UI work needed.

```
Files changed: weather_service.py, alert_service.py
DB changes: none (uses trend_window_hours added in Item 8)
```

---

#### Item 6 — Seasonal / Monsoon Baseline Awareness

**Files:** new `backend/app/utils/seasonal_baseline.py`, `backend/app/services/alert_service.py`, alerts table component

**Problem:** The same `flood_risk == HIGH` message fires year-round. An October HIGH in Jaffna (peak Northeast Monsoon) is expected; a February HIGH is genuinely anomalous. Without seasonal context, the procurement team cannot distinguish routine seasonal peaks from real outliers — leading to alert fatigue.

**Steps:**
1. Create `seasonal_baseline.py` with `MONSOON_CALENDAR` dict (Southwest: May–Sep, Northwest/East districts; Northeast: Oct–Jan, North/East districts) and `seasonal_context(location_name, month) -> "seasonal_expected" | "anomalous"`.
2. In `alert_service.py`, when writing a weather `AlertEvent`, append the seasonal context string to the message.
3. Add a "Seasonal" badge column to the alert event log in `AlertsPage` — green chip for `seasonal_expected`, red chip for `anomalous`.

```
Files changed: new seasonal_baseline.py, alert_service.py, AlertsPage component
DB changes: none
```

---

### Phase 4 — Delivery Checklist ✅ Complete

| Item | Area | Status | Notes |
|------|------|--------|-------|
| 10 — Sentiment min article guard | Bug fix | ✅ Done | `SENTIMENT_MIN_ARTICLES` env var (default 5); applied in `alert_service.py` and `backtest_service.py` |
| 11 — Per-rule email recipients | Bug fix | ✅ Done | `_try_notify(event, rule)` reads `rule.email_recipients`; comma-split; falls back to global `alert_from_email` |
| 7 — FX % change alert | FX | ✅ Done | `usd_lkr_change_pct` metric; switches to `get_summary()` for combined FX data; `ConfigPage` shows `(%)` unit label |
| 8 — FX multi-day trend alert | FX + Schema | ✅ Done | `trend_window_hours` on `AlertRule`; `rate_sustained_above()` in `fx_service.py`; `migrations.py` handles `ALTER TABLE IF NOT EXISTS` |
| 1 — Drought detection | Climate | ✅ Done | `drought_risk` column on `WeatherReading`; 14-day rolling deficit computation; scheduler stamps on each collection cycle |
| 2 — Heatwave alert | Climate | ✅ Done | `consecutive_hot_days()` in `weather_service.py`; fires when ≥3 consecutive days above threshold |
| 3 — Multi-day weather trend | Climate | ✅ Done | `location_elevated_for_hours()` in `weather_service.py`; uses shared `trend_window_hours` column |
| 6 — Seasonal baseline | Climate | ✅ Done | `utils/seasonal_baseline.py`; `[Seasonal context: …]` suffix appended to weather alerts; `SeasonalBadge` in `AlertsPage` |
| — UI bug fixes (additional) | Frontend | ✅ Done | Delete/Check Now buttons fixed (absolute URL); query key mismatch fixed; drought badge misclassification fixed |
| — UAT scenarios overhaul | Testing | ✅ Done | Expanded from 5 to 6 scenarios; all 7 Phase 4 rules covered; backtest engine evaluates drought/heatwave/FX-change historically |

**Phase 4 total: delivered 2026-05-14**

---

---

## Phase 5 — Advanced Intelligence & Compliance Layer

**Theme:** Build the net-new capabilities that require the Phase 4 alert foundation to be solid: cross-signal composite alerts (require reliable individual signals), CBSL chart context, improved news intelligence, and the SLFRS S2 compliance export. Phase 5 transforms the dashboard from a monitoring tool into an analytical one.

**Total estimated effort: ~5.5 days**

---

### Sprint 5.1 — News Intelligence Upgrade (Priority: Medium | Effort: ~1 day)

#### Item 12 — Content-Based News Topic Classification

**Files:** `backend/app/collectors/news_collector.py`, `backend/app/services/sentiment_service.py`

**Problem:** Topics are assigned at collection time based on which NewsAPI search query returned the article — not by article content. An article about US–China tariffs retrieved under a `COPPER` query is tagged `COPPER` regardless of whether copper is mentioned. This distorts per-topic sentiment ratios across the entire dashboard.

**Steps:**
1. Add `TOPIC_KEYWORDS` dict to `news_collector.py` (FX, COPPER, ALUMINIUM, TRADE, LOGISTICS keyword lists — ~5–6 keywords each).
2. Add `reclassify_topic(headline, summary) -> str | None`. Scores keyword hits across both fields; returns the best-matching topic if it scores ≥ 2 hits, otherwise `None` (keep original tag).
3. Call `reclassify_topic()` immediately after inserting each article; overwrite topic only on a confident match.
4. In `sentiment_service.py`, replace `text_to_score = r.headline` with `text_to_score = f"{r.headline}. {r.summary or ''}"[:512]`. FinBERT's 512-token limit is unchanged; this gives the model more signal when a summary is available.
5. Add a one-time migration endpoint `POST /api/v1/news/reclassify-all` to backfill existing records. Remove or disable after first run.

```
Files changed: news_collector.py, sentiment_service.py
New endpoint: POST /api/v1/news/reclassify-all (temporary)
DB changes: none
```

---

### Sprint 5.2 — CBSL Rate Overlay (Priority: Medium | Effort: ~1 day)

#### Item 9 — CBSL Reference Rate on FX Chart

**Files:** new `backend/app/models/cbsl.py`, new `backend/app/routers/cbsl.py`, `frontend/src/components/FXPanel.tsx`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** `FXPanel.tsx` renders the live USD/LKR rate and a 30-day average. Without the CBSL policy rate reference line, a sustained rate change is uninterpretable — the team cannot tell whether it reflects CBSL policy, market pressure, or IMF disbursement timing.

**Steps:**
1. New DB model `CBSLRate`: `id`, `effective_date (Date, indexed)`, `rate (Float)`, `note (String 200)` — e.g., *"MPR cut 25bps"*.
2. New router at `GET /api/v1/fx/cbsl-history?days=90`. Returns `[{effective_date, rate, note}]`.
3. New admin form in the Configurations page (new "CBSL Rates" section) — date picker + rate input + note field. CBSL announces rate changes only a few times per year, so manual entry is appropriate (Option A from the improvement doc).
4. In `FXPanel.tsx`, fetch CBSL history alongside market rate. Add a second `Line` series (dashed, gold `var(--c-accent)`) rendered as a step function (each entry spans to the next entry's `effective_date`). Add a legend. Each rate change boundary is visually marked.

```
Files changed: new cbsl.py (model), new cbsl.py (router), FXPanel.tsx, ConfigPage.tsx
DB changes: CREATE TABLE cbsl_rates
```

---

### Sprint 5.3 — SLFRS S2 Climate Export (Priority: Medium | Effort: ~1.5 days)

#### Item 4 — SLFRS S1/S2 Climate Event Log Export

**Files:** new `backend/app/services/climate_report_service.py`, new `backend/app/routers/climate_report.py`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** The dashboard already captures the climate operational data that SLFRS S2 disclosures require (weather events, alert triggers, flood risk readings). However, this data is locked inside the UI — there is no way for the sustainability team to extract it.

**Steps:**
1. New service `climate_report_service.py`. Aggregations for a given date range:
   - Total weather alert events by severity
   - Days per district with HIGH or CRITICAL flood risk
   - Days per district with MEDIUM or above drought risk (requires Phase 4 Item 1)
   - Temperature extremes per location
   - Supplier port disruption days (any port at HIGH or above)
2. New router `climate_report.py`:
   - `GET /api/v1/climate/report?start_date=&end_date=` — JSON summary
   - `GET /api/v1/climate/report/csv?start_date=&end_date=` — CSV download via `StreamingResponse`
3. New "Climate Report" tab in `ConfigPage`. Date range picker, summary table, and a *"Download CSV"* button. Disclaimer copy: *"This report can be submitted as operational evidence for SLFRS S2 climate disclosure."*

```
Files changed: new climate_report_service.py, new climate_report.py (router), ConfigPage.tsx
DB changes: none (reads existing weather_readings and alert_events tables)
Note: Drought risk aggregation requires Phase 4 Item 1 to be complete first.
```

---

### Sprint 5.4 — Cross-Signal Composite Alerts (Priority: Medium | Effort: ~2 days)

#### Item 5 — Cross-Signal Composite Alert Rules

**Files:** `backend/app/models/alerts.py`, `backend/app/services/alert_service.py`, `frontend/src/pages/ConfigPage.tsx`

**Problem:** The alert engine evaluates each rule independently. A procurement team member receives three separate alerts — flood risk, copper price spike, logistics sentiment negative — with no indication that they may be causally linked and together more operationally significant than any individual signal.

**Prerequisite:** Requires Phase 4 Sprints 4.2 and 4.3 to be complete. Composite alerts reuse the individual signal evaluators; those must be reliable first.

**Steps:**
1. Add `composite_condition = Column(Text, nullable=True)` to `AlertRule`. Stored as JSON array of sub-conditions: `[{"metric": "flood_risk", "value": "HIGH"}, {"metric": "copper_price_change_pct", "op": "gt", "value": 1.5}]`.
2. Add `evaluate_composite(rule, fx_data, commodity_data, weather_data, sentiment_data) -> bool` to `alert_service.py`. Deserialises `composite_condition`; calls `_eval_single()` for each sub-condition (reuses existing per-metric evaluation logic); returns `True` only when **all** sub-conditions pass.
3. Composite alert message lists each triggered sub-condition and the procurement implication:
   > *"Composite alert: CRITICAL flood risk in Colombo Port District AND copper price up 2.1% in 24h AND LOGISTICS news sentiment 72% negative. Consider advancing copper order before port disruption affects availability."*
4. In `ConfigPage.tsx`, add `"Composite"` to the rule type dropdown. When selected, replace the single condition row with a dynamic list of sub-condition rows (metric + comparison + value), each identical in structure to the single-condition form. An *"Add condition"* button appends a new row. Minimum two sub-conditions required.

```
Files changed: models/alerts.py, alert_service.py, ConfigPage.tsx
DB changes: ALTER TABLE alert_rules ADD COLUMN composite_condition TEXT (nullable)
```

---

### Phase 5 — Delivery Checklist ✅ Complete

| Item | Area | Status | Notes |
|------|------|--------|-------|
| 12 — Content-based topic classification | News / NLP | ✅ Done | `TOPIC_KEYWORDS` + `reclassify_topic()` in `news_collector.py`; 2 broad queries replace 5 per-topic queries; 72h lookback; `pageSize=100`; URL dedup; `POST /reclassify-all` backfill endpoint |
| 9 — CBSL rate overlay | FX chart | ✅ Done | `CBSLRate` model + full CRUD router at `/api/v1/fx/cbsl`; step-function gold line on FX chart; CBSL Rates Config tab with add/edit/delete dialog |
| 4 — SLFRS S2 climate export | Compliance | ✅ Done | `climate_report_service.py` aggregates flood/drought/temp/port/alert data by date range; JSON + CSV download endpoints; Climate Report tab in Config with date picker and Download CSV |
| 5 — Cross-signal composite alerts | Alert engine | ✅ Done | `composite_condition` TEXT column on `AlertRule`; `_eval_single_metric()` + `evaluate_composite()` with AND semantics; COMPOSITE rule type in alert engine; dynamic condition builder UI in ConfigPage |
| — Buyer-perspective sentiment fix | NLP / Data | ✅ Done | `_buyer_key()` inverts COPPER/ALUMINIUM sentiment at scoring time; DB stores procurement-correct labels; no read-time inversion |
| — NewsAPI rate-limit optimisation | Collector | ✅ Done | Reduced from ~40 req/day to ~16 req/day; free tier quota no longer exhausted |
| — Startup 7-day history backfill | Scheduler | ✅ Done | `_backfill_history()` in `jobs.py`; uses Yahoo Finance historical chart API for both FX and commodities; idempotent on every restart |
| — Weather map portrait layout | Frontend | ✅ Done | `.mapWrap` height increased to `700px` |

**Phase 5 total: delivered 2026-05-14**

---

## Combined Roadmap

```
Phase 4 (~6 days)
├── Sprint 4.1 — Bug Fixes          (Items 10, 11)   ~2 hours
├── Sprint 4.2 — FX Enhancements    (Items 7, 8)     ~1.5 days
└── Sprint 4.3 — Climate Alerts     (Items 1, 2, 3, 6) ~3 days

Phase 5 (~5.5 days)
├── Sprint 5.1 — News Intelligence  (Item 12)        ~1 day
├── Sprint 5.2 — CBSL Overlay       (Item 9)         ~1 day
├── Sprint 5.3 — SLFRS S2 Export    (Item 4)         ~1.5 days
└── Sprint 5.4 — Composite Alerts   (Item 5)         ~2 days
```

## Database Migrations Summary

All required schema changes, in dependency order:

| Migration | Phase | Change | Notes |
|-----------|-------|--------|-------|
| M1 | 4.2 | `ALTER TABLE alert_rules ADD COLUMN trend_window_hours INTEGER` | Shared by Items 8 and 3; do once |
| M2 | 4.3 | `ALTER TABLE weather_readings ADD COLUMN drought_risk VARCHAR(20)` | Required for Item 1 |
| M3 | 5.2 | `CREATE TABLE cbsl_rates (id, effective_date, rate, note)` | Required for Item 9 |
| M4 | 5.4 | `ALTER TABLE alert_rules ADD COLUMN composite_condition TEXT` | Required for Item 5 |

---

## AR Risk Coverage After Both Phases

| AR Risk | Phase 4 Addition | Phase 5 Addition | Full Coverage |
|---------|-----------------|-----------------|---------------|
| Risk #6 — Exchange Rate | FX % change + multi-day trend alerts | CBSL rate context on chart | ✅ |
| Risk #9 — Climate | Drought + heatwave + trend + seasonal | SLFRS S2 export | ✅ |
| Risk #2 — Country Risk | Article count guard fixes false alerts | Content-based topic accuracy | ✅ |
| Risk #4 — Operational BCP | Multi-day trend weather alert (advance warning) | Composite flood+FX+sentiment | ✅ |

---

*Plan created: 2026-05-14*
*Source: `future_improvements.md`, `implementation_details.md`, `project_detailes.md`*
*Phases 1–3 baseline: see `project_detailes.md` Section 6*
