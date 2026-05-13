# ACL Cables PLC — Procurement Intelligence Dashboard
## Project Living Document

> **Purpose of this file:** This is a continuously updated reference document for the *Predictive Forex & Climate-Aware Supply Chain Management System* proposed for ACL Cables PLC. Any new AI session should read this file in full before contributing. It captures the problem context, refined scope, design decisions, open questions, and progress to date.

---

## Document History

| Version | Date | Change Summary |
|---------|------|----------------|
| 0.1 | 2026-05-13 | Initial draft — scoped from critical analysis of ACL AR 2024/25 |
| 0.2 | 2026-05-13 | Phase 1 complete; tech stack finalised |
| 0.3 | 2026-05-13 | Phase 2 complete; delivery plan and handover notes updated |
| 0.4 | 2026-05-13 | UI refactor complete; phase checkboxes and tech stack table updated |

---

## 1. Company Context

**Company:** ACL Cables PLC — Sri Lanka's largest cable manufacturer, founded 1962.
**Website:** https://www.acl.lk/
**Source document:** Annual Report 2024/25 (`ACL_Cables_24_25_AR.pdf`)

### Key facts relevant to this project
- **Revenue:** Rs. 37,487 million (Group, FY2024/25) — up from Rs. 29,196 Mn prior year
- **Raw material sourcing:** Majority imported from UAE, China, Singapore, Vietnam
  - Primary materials: **Copper, Aluminium, XLPE**
  - Over **57% of purchases are from import/foreign vendors**
- **Backward integration:** Owns Ceylon Copper (Pvt) Ltd (copper rod manufacturing) and ACL Metals & Alloys (aluminium rods/alloys) — meaning commodity price movements hit them at multiple tiers
- **FX exposure:** USD/LKR averaged **297** in FY2024/25, down from **317** the prior year — a ~6% swing on a Rs. 37.5 Bn revenue base is material
- **Distribution:** Island-wide across Sri Lanka via **996 dealers** and **219 distributors** — making logistics vulnerable to weather events (flooding in particular)
- **Export footprint:** Exports to 10+ countries; export revenues grew 10.31% YoY

### Formally documented risks (from AR Risk Management section)
| Risk # | Risk | Current Rating | Current Mitigation (Manual) |
|--------|------|----------------|-----------------------------|
| 6 | Exchange Rate Risk | Moderate | Monitor macro trends; maintain forex reserve buffer; track global political events |
| 9 | Sustainability & Climate-Related Risk | Moderate | SLFRS S1/S2 alignment in progress; qualitative monitoring |
| 2 | Country Risk | Significant | PESTEL analysis; stakeholder relationships |
| 4 | Operational Risk | Moderate | ISO 9001/14001 compliance; BCP |

**Critical gap identified:** All current Exchange Rate and Climate Risk mitigations are entirely manual and reactive. No systematic, data-driven tooling exists for procurement decision support.

---

## 2. Problem Statement

ACL Cables' procurement team makes high-value, recurring decisions about **when and how much** to import copper, aluminium, and XLPE. These decisions are sensitive to:

1. **USD/LKR exchange rate** — directly affects LKR cost of every import order
2. **Global commodity prices** — LME copper and aluminium prices fluctuate independently of FX
3. **Geopolitical/news events** — trade disruptions in supplier countries (UAE, China, Vietnam) can affect availability and price
4. **Weather and climate events** — flooding and monsoon patterns affect Sri Lanka's logistics network and warehouse operations

Currently, the procurement team monitors these variables manually and in isolation, with no integrated tooling, alerting, or analytical layer. This creates:
- Missed windows for cost-advantageous purchasing
- Reactive (not anticipatory) responses to FX volatility
- No early warning system for supply chain disruptions driven by climate or geopolitical events

---

## 3. Refined Solution — What We Are Actually Building

### 3.1 Honest Framing (Post-Critique)

The original proposal used language like "predict short-term currency changes." This was revised after critical analysis. **The system is a Procurement Intelligence Dashboard** — it aggregates, contextualizes, and alerts. The AI/ML layer is a *signal amplifier*, not an oracle.

> **Core value proposition:** Give the procurement team a single, unified view of the forces affecting their import costs — with configurable alerts and AI-assisted pattern recognition — so they can make better-timed decisions.

### 3.2 System Components

#### Component 1: Real-Time Data Aggregation Layer
Collects and normalizes data from external sources on a scheduled basis (configurable — e.g., every 15 min for FX, daily for commodities, hourly for weather).

| Data Type | Specific Data | Candidate Free/Low-Cost Sources |
|-----------|--------------|--------------------------------|
| FX Rate | USD/LKR live & historical | CBSL API, exchangerate-api.com, Open Exchange Rates |
| Commodity Prices | LME Copper (spot & futures), Aluminium | Yahoo Finance API, Metals API (freemium), Quandl |
| Weather (Sri Lanka) | Rainfall, flood alerts by district | Open-Meteo (free), NOAA, DMC Sri Lanka |
| Weather (Supplier countries) | Port weather in UAE/China/Vietnam | Open-Meteo |
| News/Geopolitical | Trade, tariff, supply chain news | NewsAPI.org, GNews API, RSS feeds (Reuters, Bloomberg free tier) |

> ⚠️ **Data sourcing is a known risk.** Premium feeds (Bloomberg, Refinitiv) are enterprise-priced and not assumed. The system must be designed to work with free/freemium APIs with graceful degradation when data is unavailable. This must be addressed before development begins.

#### Component 2: Procurement Intelligence Dashboard (Web UI)
A web-based interface for the ACL procurement team. Not public-facing.

**Key views:**
- **Overview panel** — Current USD/LKR, LME copper, LME aluminium, active weather alerts, news sentiment indicator
- **FX trend panel** — 30/60/90-day historical chart, CBSL rate overlay, volatility bands
- **Commodity panel** — Copper and aluminium price trends with cost-impact calculator (e.g., "if we place an order of X tonnes today at current LME + FX, landed cost = Rs. Y")
- **Weather & logistics panel** — Sri Lanka district-level rainfall/flood risk map; supplier country port weather
- **News feed panel** — Filtered, scored news feed for supply-chain-relevant geopolitical events

#### Component 3: Alert & Notification Engine
Configurable rule-based alerting system. Procurement team sets thresholds; system notifies via email/SMS/dashboard banner.

**Example alert rules:**
- USD/LKR drops below [threshold] → "FX window: consider advancing next copper order"
- LME copper price drops >2% in 24h → "Commodity dip: review open POs"
- Flood risk alert issued for Western Province → "Logistics warning: pre-position stock before [date]"
- News sentiment score for "China trade" drops → "Geopolitical flag: monitor supplier communications"

#### Component 4: NLP Sentiment Analysis Module
Processes news headlines/articles and scores them for relevance and sentiment across defined topics:
- Topics: USD/LKR stability, copper market, Sri Lanka imports, UAE/China/Vietnam trade, global shipping/logistics
- Output: Sentiment score per topic per day (positive/negative/neutral), surfaced in dashboard

**Technology approach (honest scoping):**
- Use a pre-trained financial NLP model (e.g., **FinBERT** or similar) for baseline sentiment
- Do NOT claim this predicts FX movements — it is a contextual flag for the team to investigate
- Accuracy limitations must be documented in the UI itself (e.g., "This is an automated signal. Verify before acting.")

#### Component 5: Historical Analysis & Cost-Impact Module
Allows procurement team to run retrospective analysis:
- "What would our landed cost have been if we had purchased on date X vs. date Y?"
- Helps the team build intuition for FX-commodity correlation patterns specific to ACL's purchasing profile

---

## 4. What This System Is NOT

These items were considered and deliberately excluded or de-scoped:

| Excluded Feature | Reason |
|-----------------|--------|
| FX price prediction / forecasting model | USD/LKR is a thin, intervention-prone market. Short-term prediction is not reliably achievable. Framing as "prediction" would erode trust when wrong. |
| Automated purchasing / order placement | Procurement involves LCs, credit terms, supplier relationships — cannot and should not be automated |
| Custom-trained NLP model | Requires labelled Sri Lankan procurement corpus that doesn't exist; use pre-trained models instead |
| Real-time LME futures trading signals | Not a trading desk; scope is procurement planning, not financial speculation |
| Full ERP integration (Phase 1) | ACL's internal ERP/SAP integration is unknown and would require IT engagement. Defer to Phase 2. |

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  DATA COLLECTION LAYER                  │
│  FX APIs │ Commodity APIs │ Weather APIs │ News APIs    │
└──────────────────────┬──────────────────────────────────┘
                       │ (Scheduled jobs / cron)
┌──────────────────────▼──────────────────────────────────┐
│                  BACKEND SERVICES                        │
│  Data Normalizer │ Alert Engine │ NLP Sentiment Service  │
│  Historical Store (PostgreSQL / TimescaleDB)             │
└──────────────────────┬──────────────────────────────────┘
                       │ (REST API / WebSocket)
┌──────────────────────▼──────────────────────────────────┐
│                  WEB DASHBOARD (Frontend)                │
│  Overview │ FX Panel │ Commodity Panel │ Weather Panel   │
│  News Feed │ Alert Config │ Cost-Impact Calculator       │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  Email / SMS Alerts → Procurement Team
```

### Finalised Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.12 + FastAPI 0.136 | REST endpoints; OpenAPI docs at `/docs`; `uv` for package management |
| Scheduler | APScheduler 3.11 (`BackgroundScheduler`) | In-process; no Redis needed |
| Database | SQLAlchemy 2 + SQLite (dev) / PostgreSQL + TimescaleDB (prod) | Swap via `DATABASE_URL` env var |
| NLP | FinBERT (`ProsusAI/finbert`) via HuggingFace | CPU-only inference; lazy-loaded; ~400 MB download on first use |
| Frontend | React 19 + TypeScript + Vite 8 + Tailwind CSS v3 | shadcn/ui components; React Router v7 |
| Charts | Recharts 3 | Line, area charts with CSS variable theming |
| Data fetching | @tanstack/react-query v5 | Query caching; configurable refetch intervals |
| Weather | Open-Meteo API | Free, keyless; runs in all modes |
| FX | exchangerate-api.com | Requires `FX_API_KEY` |
| News | NewsAPI.org | Requires `NEWSAPI_KEY` |
| Commodities | Yahoo Finance (`HG=F`, `ALI=F`) | Free but unofficial endpoint — fragile |
| Alerts | Rule-based engine + SMTP email (optional) | Twilio SMS deprioritised |
| Deployment | Docker Compose (dev), VPS or AWS EC2 (prod) | Containerized for portability |

---

## 6. Phased Delivery Plan

### Phase 1 — Foundation ✅ Complete

- [x] Set up data collection for USD/LKR (CBSL + free API)
- [x] Set up data collection for LME copper and aluminium prices
- [x] Set up Sri Lanka weather data collection (Open-Meteo)
- [x] Set up news feed collection (NewsAPI.org)
- [x] PostgreSQL schema design (FX, commodities, weather, news tables)
- [x] Basic FastAPI backend with REST endpoints
- [x] React dashboard: Overview, FX panel, Commodity panel
- [x] Rule-based alert engine (threshold-based, email notifications)
- [x] Cost-impact calculator (simple: quantity × LME price × FX rate → LKR)

### Phase 2 — Intelligence Layer ✅ Complete

- [x] Integrate FinBERT for news sentiment scoring
- [x] Build topic-filtered news feed with sentiment scores
- [x] Historical cost-impact analysis view ("what-if" calculator)
- [x] Weather panel: district-level flood risk map for Sri Lanka
- [x] Supplier country weather (UAE, China, Vietnam ports)
- [x] Alert engine expansion: sentiment-based and weather-based alerts
- [x] User-configurable alert thresholds

### UI Refactor ✅ Complete

- [x] Tailwind CSS v3 + shadcn/ui component library
- [x] Sidebar navigation with 4 pages (Home, Calculator, Alerts, Configurations)
- [x] ACL brand colour scheme (blue + gold) with light and dark modes
- [x] Centralised CSS token system (`globals.css`) — `--c-*` semantic vars, Tailwind HSL tokens, legacy aliases
- [x] Alert event log with severity-based row coloring (red/orange/yellow/green/blue)
- [x] Configurations page: alert rules CRUD, app settings, FinBERT model tuning

### Phase 3 — Validation & Handover (Not started)
**Goal:** Test with real data, document for handover to ACL team.

- [ ] Backtest alert rules against historical FX/commodity data (2022–2025)
- [ ] User acceptance testing with simulated procurement scenarios
- [ ] System documentation and user guide
- [ ] Data source reliability audit (which APIs are fragile? which need paid fallbacks?)
- [ ] (Optional) ERP integration scoping meeting with ACL IT team

---

## 7. Key Risks & Mitigations (Project-Level)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Free API rate limits or ToS violations | High | High | Identify paid fallbacks early; respect ToS; cache aggressively |
| NLP sentiment scores are noisy / unreliable | High | Medium | Show confidence scores; frame as "signal, not signal" in UI; don't auto-alert on sentiment alone |
| FX prediction framing creep | Medium | High | Enforce language discipline in UI copy: "indicator" not "forecast" |
| Procurement team doesn't adopt dashboard | Medium | High | Involve at least one procurement team member in Phase 1 UAT |
| ACL IT firewall blocks external API calls | Medium | Medium | Clarify deployment environment early; consider cloud-hosted backend |
| Commodity API data quality / delays | Medium | Medium | Show data freshness timestamps prominently in UI |

---

## 8. Open Questions (To Be Resolved)

1. **Data access:** Has ACL Cables agreed to share their procurement volume data (tonnes per order, order frequency)? This would significantly improve the cost-impact calculator.
2. **Deployment environment:** Will this be hosted externally (cloud) or on ACL's internal network? This affects API access and security design.
3. **Stakeholder:** Who is the primary user in the procurement team? What is their technical comfort level?
4. **Alert channels:** Does ACL use Microsoft Teams or Slack internally? Webhook integration would be more useful than email for some teams.
5. **Regulatory:** Are there any data residency requirements for a Sri Lankan company receiving external financial data feeds?
6. **ERP:** What ERP/planning system does ACL use? (SAP? Sage? Custom?) Phase 3 integration depends on this.
7. **Commodity granularity:** Does ACL purchase copper/aluminium on spot or on forward contracts? This affects which price data is most relevant.

---

## 9. Success Metrics

The project should define measurable outcomes to evaluate whether it delivered value:

| Metric | Target | How Measured |
|--------|--------|-------------|
| Dashboard daily active usage | ≥ 3 procurement team members | Session logs |
| Alert precision (true useful alerts / total alerts) | > 60% | User feedback log |
| Time to surface relevant news signal | < 2 hours from publication | Timestamp comparison |
| Cost-impact calculator adoption | Used in ≥ 50% of import decisions | Usage tracking |
| Reduction in time spent manually aggregating data | > 30% | Team self-report (before/after survey) |

---

## 10. Session Handover Notes

> **Instructions for the next AI session:**
> Read this document and `docs/implementation_details.md` in full before contributing. All design decisions are finalised unless explicitly reopened. When a decision is reopened, add a note to Section 8 (Open Questions) and update the Document History table.
>
> **Current status as of 2026-05-13:**
> - Phase 1 (backend + debug data layer + basic dashboard) ✅ Complete
> - Phase 2 (FinBERT sentiment, live collectors, weather map, enhanced alerts) ✅ Complete
> - UI refactor (Tailwind/shadcn, sidebar, brand colours, light/dark mode, alert severity) ✅ Complete
> - **Next step:** Phase 3 — validation, backtesting, user acceptance testing, data source audit, user guide
>
> **Running the project:**
> ```bash
> # Backend (debug mode)
> cd backend && uv run uvicorn app.main:app --reload
> # http://localhost:8000 | Docs: http://localhost:8000/docs
>
> # Frontend
> cd frontend && npm run dev
> # http://localhost:5173
> ```
>
> **Key environment variables** (`backend/.env`):
> - `DEBUG=true` — uses generated data, skips live API calls
> - `FX_API_KEY` — exchangerate-api.com (optional; required for live FX)
> - `NEWSAPI_KEY` — newsapi.org (optional; required for live news)
> - `SENTIMENT_ENABLED=true` — enables FinBERT scoring (downloads ~400 MB model on first use)
>
> **Files referenced:**
> - `docs/implementation_details.md` — tech stack decisions and progress log (read alongside this file)
> - `ACL_Cables_24_25_AR.pdf` — ACL Annual Report 2024/25 (source of company context)

---

*Last updated: 2026-05-13 | Current phase: UI refactor complete — Phase 3 (validation & handover) next*
