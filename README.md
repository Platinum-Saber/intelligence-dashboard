# ACL Cables PLC — Procurement Intelligence Dashboard

A web-based decision-support tool for ACL Cables PLC's procurement team. It aggregates real-time foreign exchange rates, commodity prices, weather risk, and geopolitical news into a single dashboard — helping the team make better-timed import decisions for copper, aluminium, and XLPE.

> **This is an intelligence and alerting system, not a price-prediction oracle.** Every data point is labelled with its source and freshness. AI sentiment scores are presented as signals to investigate, not as instructions to act.

---

## What it does

ACL Cables imports the majority of its raw materials from the UAE, China, Singapore, and Vietnam. Every purchase is exposed to:

- **USD/LKR exchange rate** — directly sets the LKR cost of every import order
- **LME commodity prices** — copper and aluminium move independently of FX
- **Geopolitical events** — trade disruptions in supplier countries affect availability and price
- **Climate and logistics risk** — flooding and monsoon patterns affect Sri Lanka's distribution network

The dashboard gives the procurement team a unified view of all four forces, with configurable alert rules and an AI-assisted news sentiment layer.

---

## Features

| Page | What it shows |
|------|--------------|
| **Home** | Live overview: USD/LKR, LME copper & aluminium, active weather alerts, today's news count. FX trend chart (30/60/90d). Commodity price chart. Historical landed-cost area chart. Weather risk map. Topic-filtered news feed with FinBERT sentiment scores. |
| **Calculator** | Landed-cost calculator: enter material, quantity (tonnes), and optional price overrides → get LKR cost at current LME and FX. Methodology reference card. |
| **Alerts** | Full event log of every triggered alert rule, colour-coded by severity (red critical → green favourable → blue FX/info). Search and row-limit controls. |
| **Configurations** | Alert rules CRUD (create, enable/disable, delete). App settings (active environment variables). FinBERT model info and manual trigger for scoring unscored news items. |

### Alert rule types

| Type | Trigger example |
|------|----------------|
| `FX_THRESHOLD` | USD/LKR drops below a configured level — favourable import window |
| `COMMODITY_DIP` | LME copper or aluminium drops >X% in 24 h |
| `WEATHER_RISK` | Flood risk rises above threshold in a Sri Lanka district |
| `SENTIMENT_NEGATIVE` | FinBERT negative sentiment exceeds threshold for a topic (e.g., `COPPER:0.60`) |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | Backend runtime |
| [uv](https://github.com/astral-sh/uv) | latest | Python package/venv manager |
| Node.js | 18+ | Frontend build tooling |
| npm | 9+ | Bundled with Node |

No database setup is required for development — SQLite is used automatically.

---

## Quick start

### 1. Clone / open the project

```
d:\Projects\Intelligence Dashboard\
├── backend\     ← Python FastAPI service
└── frontend\    ← React + Vite dashboard
```

### 2. Start the backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive API docs (Swagger): http://localhost:8000/docs

On first startup the database is auto-seeded with 90 days of generated data. No manual step needed.

### 3. Start the frontend

```bash
cd frontend
npm install          # first time only
npm run dev
```

- Dashboard: http://localhost:5173

---

## Configuration

All settings live in `backend/.env`. Create the file if it does not exist.

```env
# --- Core ---
DEBUG=true                  # true = generated data, no live API calls
DATABASE_URL=sqlite:///./procurement_intel.db   # swap to PostgreSQL for production

# --- Live data feeds (only needed when DEBUG=false) ---
FX_API_KEY=your_key         # exchangerate-api.com — required for live USD/LKR
NEWSAPI_KEY=your_key        # newsapi.org — required for live news feed

# --- NLP ---
SENTIMENT_ENABLED=false     # true = download ~400 MB FinBERT model and score news

# --- Email alerts (optional) ---
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your_password
ALERT_EMAIL_TO=procurement@acl.lk
```

### Debug mode vs live mode

| Setting | `DEBUG=true` | `DEBUG=false` |
|---------|-------------|--------------|
| Data source | Generated realistic data | Live external APIs |
| FX feed | Simulated random-walk | exchangerate-api.com (`FX_API_KEY` required) |
| Commodity feed | Simulated | Yahoo Finance (`HG=F`, `ALI=F`) — unofficial endpoint |
| Weather feed | Open-Meteo always runs | Open-Meteo always runs (free, no key) |
| News feed | Templated headlines | NewsAPI.org (`NEWSAPI_KEY` required) |
| Scheduler | Runs but collectors return early | Full 15-min/1-h/2-h schedule |

Start with `DEBUG=true` to verify the system runs correctly before adding API keys.

---

## Pages walkthrough

### Home

The home page is divided into six panels:

1. **Overview cards** — Snapshot of USD/LKR, copper price, aluminium price, high-risk weather locations, and today's news count.
2. **FX Trend** — 30/60/90-day USD/LKR line chart with average reference line and summary statistics.
3. **Commodity Prices** — Toggle between copper and aluminium; same period controls.
4. **Historical Landed Cost** — Area chart showing what it would have cost to import X tonnes of a material on each day over the selected period.
5. **Weather & Logistics** — Interactive Leaflet map of Sri Lanka districts colour-coded by flood risk (green → red). Supplier country port weather shown separately.
6. **News Feed** — Filter by topic (FX, COPPER, ALUMINIUM, TRADE, LOGISTICS). Each item shows headline, summary, topic tag, and FinBERT sentiment indicator (↑ positive / ↓ negative / – neutral).

### Calculator

Enter material type, order quantity in tonnes, and optional price overrides. The calculator multiplies `quantity × LME price (USD/t) × USD/LKR` to give landed cost in LKR. The methodology card explains every variable. The historical cost chart below gives context for whether today is a good time to buy.

### Alerts

A searchable, paginated table of all triggered alert events. Each row is colour-coded:

| Colour | Meaning |
|--------|---------|
| Red | Critical weather risk or strongly negative sentiment |
| Orange | High weather risk or commodity price spike |
| Yellow | Medium/low weather risk |
| Green | Favourable outcome (e.g. commodity price dip — good buying opportunity) |
| Blue | FX threshold crossed or informational |

Click the row limit selector (25 / 50 / 100 / 200) to control how many events load.

### Configurations

Three tabs:

- **Alert Rules** — View all rules; toggle enabled/disabled; create new rules with the dialog; delete rules. Fields: name, type, threshold, notification email.
- **App Settings** — Read-only display of active environment variables. Useful for verifying which API keys are loaded.
- **Model Tuning** — Shows FinBERT model status and configuration. The "Score now" button triggers immediate sentiment scoring of any unscored news items (useful after adding new API key and disabling `SENTIMENT_ENABLED=false`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  DATA COLLECTION LAYER                  │
│  FX APIs │ Commodity APIs │ Weather APIs │ News APIs    │
└──────────────────────┬──────────────────────────────────┘
                       │  APScheduler (15 min / 1 h / 2 h)
┌──────────────────────▼──────────────────────────────────┐
│                  BACKEND — FastAPI                       │
│  Collectors │ Alert Engine │ FinBERT Sentiment Service  │
│  SQLAlchemy ORM │ SQLite (dev) / PostgreSQL+TimescaleDB │
│  REST API at /api/v1/*                                  │
└──────────────────────┬──────────────────────────────────┘
                       │  React Query (polling + cache)
┌──────────────────────▼──────────────────────────────────┐
│                  FRONTEND — React 19 + Vite             │
│  Home │ Calculator │ Alerts │ Configurations            │
│  Recharts charts │ Leaflet map │ shadcn/ui components   │
│  Tailwind CSS v3 │ Light + dark mode                    │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  SMTP email alerts → Procurement team
```

### Tech stack summary

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI 0.136, SQLAlchemy 2, APScheduler 3.11 |
| NLP | FinBERT (`ProsusAI/finbert`) via HuggingFace Transformers, PyTorch CPU |
| Database | SQLite (development), PostgreSQL + TimescaleDB (production) |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v3, shadcn/ui |
| Charts | Recharts 3 |
| Maps | react-leaflet + Leaflet.js |
| Data fetching | @tanstack/react-query v5 |
| Weather API | Open-Meteo (free, no key required) |
| FX API | exchangerate-api.com (requires `FX_API_KEY`) |
| News API | NewsAPI.org (requires `NEWSAPI_KEY`) |
| Commodity data | Yahoo Finance futures (`HG=F`, `ALI=F`) |

---

## Production deployment

For production, switch SQLite to PostgreSQL by setting `DATABASE_URL`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/procurement_intel
```

A `docker-compose.yml` is included at the project root. Run both services with:

```bash
docker compose up --build
```

The PostgreSQL section in `docker-compose.yml` is commented out — uncomment it for a fully containerised stack including the database.

---

## Resetting the database

```bash
cd backend
# Delete the SQLite file, then restart the server (auto-reseeds on startup)
del procurement_intel.db
uv run uvicorn app.main:app --reload

# Or reseed manually without deleting:
uv run python -m debug.seed
```

---

## Triggering FinBERT scoring manually

```bash
# Via the API:
curl -X POST http://localhost:8000/api/v1/news/score-now

# Or directly in Python:
cd backend
uv run python -c "
from app.database import SessionLocal
from app.services.sentiment_service import score_unscored_news
db = SessionLocal()
print(score_unscored_news(db, 200))
db.close()
"
```

Note: `SENTIMENT_ENABLED=true` must be set in `.env` and the ~400 MB FinBERT model will download on first use.

---

## Known limitations

- **Yahoo Finance commodity endpoint** is an unofficial API — it may break without warning. A paid fallback (e.g., Metals API) should be evaluated before production use.
- **FinBERT sentiment scores** are noisy on short headlines. They are presented as signals, not instructions. The UI labels them accordingly.
- **USD/LKR** is a thin, intervention-prone market. The dashboard does not attempt to forecast exchange rates — it surfaces current data and alerts on thresholds.
- **Free API rate limits** apply to exchangerate-api.com and NewsAPI.org on free tiers. Cache aggressively and consider paid tiers for production.

---

## Project status

| Phase | Status |
|-------|--------|
| Phase 1 — Foundation (backend, debug data, basic dashboard) | Complete |
| Phase 2 — Intelligence layer (FinBERT, live collectors, weather map, enhanced alerts) | Complete |
| UI Refactor (Tailwind/shadcn, sidebar, brand colours, light/dark mode) | Complete |
| Phase 3 — Validation & handover (backtesting, UAT, data source audit, user guide) | Not started |

---

*Built for ACL Cables PLC · Sri Lanka's largest cable manufacturer*
