# ACL Cables Procurement Intelligence Dashboard — User Guide

> **Audience:** ACL Cables procurement team members using the dashboard day-to-day.
> **Version:** Phase 3 | Last updated: 2026-05-13

---

## What This Dashboard Does

The Procurement Intelligence Dashboard gives you a single view of the key forces that affect your import costs:

- **USD/LKR exchange rate** — watch for windows to advance or defer orders
- **LME Copper and Aluminium prices** — track 24-hour price movements and buy-dip signals
- **Sri Lanka weather / flood risk** — early warning for logistics disruptions
- **News sentiment** — AI-scored headlines flagging geopolitical or market events

The system does **not** predict prices or make purchasing decisions. It aggregates signals so your team can make better-timed decisions.

---

## Getting Started

### Accessing the Dashboard

Open your browser and navigate to the dashboard URL provided by your IT team (default: `http://localhost:5173` for local development).

The sidebar on the left gives you access to all pages:

| Page | What you'll find |
|------|-----------------|
| **Home** | Live snapshot: FX, commodities, weather alerts, news feed |
| **Calculator** | Landed cost calculator + historical cost chart |
| **Alerts** | Log of all triggered alert events |
| **Backtesting** | Test alert rules against historical data; run UAT scenarios |
| **Configurations** | Manage alert rules, view settings, audit data sources |

---

## Home Page

### Overview Cards

The top row shows the current values of your four key metrics:

- **USD/LKR** — current exchange rate with 24-hour change
- **LME Copper** — price in USD/tonne with 24-hour % change
- **LME Aluminium** — price in USD/tonne with 24-hour % change
- **High-risk weather locations** — count of districts/ports with MEDIUM or higher flood risk

A green value means the metric moved favourably (e.g. FX rate dropped, commodity dipped). Red means adverse movement.

### FX Trend Chart

- Toggle between 30, 60, and 90-day historical views
- The dashed reference line shows the period average
- Summary stats below the chart: current, 24h change, period high/low/average

### Commodity Price Chart

- Toggle between COPPER and ALUMINIUM
- Same 30/60/90-day selector as FX
- A drop of >2% in 24 hours triggers a commodity dip alert (if configured)

### Historical Landed Cost

Shows what it would have cost to import your configured quantity of material each day over the selected period. Useful for understanding whether today's prices are high or low relative to recent history.

### Weather & Logistics Map

A map of Sri Lanka showing flood risk by district, plus key supplier ports (UAE, China, Vietnam):

| Colour | Risk level | Meaning |
|--------|-----------|---------|
| Green | LOW | Normal conditions |
| Yellow | MEDIUM | Monitor; pre-position if delivery is imminent |
| Orange | HIGH | Likely disruption; arrange alternative routing |
| Red | CRITICAL | Severe disruption; halt deliveries to affected areas |

### News Feed

AI-scored headlines relevant to your procurement. Filter by topic:

- **FX** — exchange rate news
- **COPPER** — LME copper market
- **ALUMINIUM** — LME aluminium market
- **TRADE** — trade policy, tariffs, geopolitics
- **LOGISTICS** — shipping, port disruptions, freight

Each article shows a sentiment badge (Positive / Negative / Neutral). These are signals — always read the article before acting.

---

## Landed Cost Calculator

**Purpose:** Quickly calculate what an import order would cost in LKR today, or compare costs across dates.

### How to use

1. Select **Material** (Copper or Aluminium)
2. Enter **Quantity** in tonnes
3. Optionally enter custom price overrides (to model scenarios like "what if LME copper were $9,500?")
4. Click **Calculate** — the LKR landed cost appears instantly

### Formula

```
Landed Cost (LKR) = Quantity (tonnes) × LME Price (USD/tonne) × USD/LKR Rate
```

Note: This is the raw material cost only. It does not include freight, insurance, duties, or other import costs.

### Historical Cost Chart

The area chart beneath the calculator shows what the same order would have cost on each day over the last 90 days. Use this to understand whether today is a relatively expensive or cheap time to order.

---

## Alert Event Log

All triggered alerts appear here in reverse chronological order. Each row shows:

- **Severity colour** — Red (critical/negative sentiment), Orange (high risk/price rise), Yellow (medium), Green (favourable buy signal), Blue (FX/informational)
- **Time** — when the alert fired
- **Type** — the alert category
- **Rule name** — which rule triggered
- **Message** — what condition was detected
- **Notified** — whether an email notification was sent

Use the search box to filter by rule name or message keyword. Use the row-limit dropdown to see more historical events.

---

## Backtesting & UAT

### Alert Backtesting

Test whether your alert rules would have been useful over a historical period.

1. Set a **Start Date** and **End Date** (or click 30d / 60d / 90d for a quick range)
2. Click **Run Backtest**
3. Review the results:
   - **Summary cards** — total days, total alert fires, average fires per day
   - **Frequency chart** — bar chart showing how many alerts fired on each day
   - **Per-rule table** — how often each rule triggered, first and last fire dates

**How to interpret:** A rule that fires on 5% of days or fewer is well-calibrated. A rule that fires every day may have a threshold that is too loose and will generate noise. A rule that never fires may have a threshold that is unreachable.

### UAT Scenarios

Five pre-built procurement scenarios let you verify that your alert rules are correctly configured:

| Scenario | What it simulates |
|----------|------------------|
| **FX Buying Window** | USD/LKR drops to 283 — tests FX threshold alerts |
| **Copper Market Dip** | LME copper falls 5.4% in 24h — tests commodity dip alerts |
| **Monsoon Disruption** | Colombo, Gampaha, Kalutara at HIGH flood risk — tests weather alerts |
| **Geopolitical Supply Risk** | 68% negative copper news — tests sentiment alerts |
| **Combined Risk Event** | FX spike + flood + negative sentiment simultaneously |

Click **Run** on any scenario to see which rules would fire and why. If a scenario does not trigger the rules you expect, review your thresholds in **Configurations → Alert Rules**.

---

## Configurations

### Alert Rules

Create, enable/disable, or delete alert rules.

**Rule types:**

| Type | Metric | Example threshold |
|------|--------|------------------|
| FX_THRESHOLD | usd_lkr | Less than 290 → buying opportunity |
| COMMODITY_DIP | copper_price / aluminium_price | Less than –2% → 24h price drop |
| WEATHER_RISK | flood_risk | Equals HIGH → logistics warning |
| SENTIMENT_NEGATIVE | news_sentiment | COPPER:0.60 → 60% negative articles |

**Manual check:** Click **Check Now** to immediately evaluate all rules against current data, rather than waiting for the next 15-minute scheduler run.

**Email notifications:** Enter comma-separated email addresses in the "Email recipients" field of a rule to receive an email whenever that rule fires. Requires SMTP configuration on the server.

### App Settings

Read-only view of the current environment configuration. To change a setting, edit `backend/.env` and restart the backend.

### Model Tuning

Controls for the FinBERT sentiment model. Click **Score unscored news** to manually trigger sentiment scoring on articles that have not yet been processed.

### Data Sources

A reliability audit of all external APIs the system depends on. Check this tab when:
- Data appears stale or missing
- You notice a gap in the news feed or commodity prices
- You are preparing for production deployment

Each source shows its current status, data points in the last 24 hours, fragility rating (LOW/MEDIUM/HIGH), and recommended paid fallbacks.

---

## Understanding Sentiment Scores

The FinBERT model reads each news headline and assigns it one of three labels:

- **Positive** — the article describes a favourable development (e.g. "Copper demand surges")
- **Negative** — an adverse development (e.g. "Trade restrictions tighten on copper exports")
- **Neutral** — factual or ambiguous (e.g. "LME opens trading session")

**Important limitations:**
- FinBERT is a general financial model, not trained specifically on procurement news
- Short headlines may be classified incorrectly
- Sentiment is a signal to investigate, not a direct instruction to act
- The UI shows confidence labels; low-confidence scores should be weighted less

---

## Alert Thresholds — Recommended Starting Points

| Metric | Conservative | Moderate | Aggressive |
|--------|-------------|---------|------------|
| USD/LKR buy signal | < 285 | < 290 | < 295 |
| USD/LKR pressure alert | > 320 | > 310 | > 305 |
| Copper dip signal | < –5% 24h | < –3% 24h | < –2% 24h |
| Aluminium dip signal | < –4% 24h | < –3% 24h | < –2% 24h |
| Flood risk alert | CRITICAL | HIGH | MEDIUM |
| Sentiment alert | > 70% negative | > 60% negative | > 50% negative |

Use the **Backtesting** tool to validate your thresholds before relying on them in production.

---

## Frequently Asked Questions

**Q: The FX rate hasn't updated — is something wrong?**
Data is collected every 15 minutes. If the last reading is more than 1 hour old, check **Configurations → Data Sources** for an API error. In debug mode, data is generated automatically and should always be current.

**Q: The news feed shows articles from yesterday — is this normal?**
The free tier of NewsAPI.org delays articles by up to 24 hours. For real-time procurement signals, the paid tier (or an alternative source) is required. See **Configurations → Data Sources** for details.

**Q: A rule fired but the alert seems wrong — what happened?**
Review the message in the Alert Log. The most common causes are:
- A threshold set too loosely (fires too often) — use Backtesting to recalibrate
- A sentiment alert firing on a single low-volume news day — consider requiring a minimum article count

**Q: Can I export the data?**
The backend exposes a full REST API at `http://localhost:8000/docs`. All data can be queried programmatically. Export to CSV is not built into the UI but can be done via the API.

**Q: Who do I contact if the dashboard goes down?**
Contact your IT team or the system administrator. See the Deployment Runbook (`docs/deployment_runbook.md`) for troubleshooting steps.

---

*This guide covers the Phase 3 release. For technical documentation, see `docs/deployment_runbook.md` and the API documentation at `/docs`.*
