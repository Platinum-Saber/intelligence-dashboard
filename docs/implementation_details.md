# ACL Cables PLC — Procurement Intelligence Dashboard
## Implementation Details

> **Purpose of this file:** Tracks tech stack decisions and implementation progress per phase. Updated as each phase is completed. Read alongside `project_detailes.md` for full context.

---

## Document History

| Version | Date | Change Summary |
|---------|------|----------------|
| 0.1 | 2026-05-13 | Initial draft — tech stack documented per phase, pre-implementation |
| 0.2 | 2026-05-13 | Phase 1 fully implemented — backend, debug layer, and frontend complete |

---

## Tech Stack by Phase

### Phase 1 — Foundation ✅

**Goal:** Working dashboard backed by generated debug data, with real architecture ready to swap in live feeds.

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.12 + FastAPI 0.136 | REST endpoints for all data domains; auto OpenAPI docs at `/docs` |
| Package manager | uv | Dependency and virtualenv management |
| Database | SQLAlchemy + SQLite (dev) / PostgreSQL + TimescaleDB (prod) | SQLite requires no setup; swap `DATABASE_URL` to move to Postgres |
| Scheduler | APScheduler 3.11 (`BackgroundScheduler`) | In-process cron jobs; collector stubs run every 15 min–1 h |
| Frontend | React 19 + TypeScript + Vite | Component-based dashboard |
| Charts | Recharts | FX and commodity line charts with tooltips and reference lines |
| Data fetching | @tanstack/react-query | Query caching, refetch intervals, loading/error states |
| Debug data | Custom generators (`backend/debug/`) | Realistic random-walk FX/commodity data, monsoon-aware weather, templated news |
| Alerting | Rule-based engine + SMTP (optional) | Threshold rules stored in DB; scheduler evaluates every 15 min |
| Containerisation | Docker Compose | `docker-compose up` starts both services |

**Decisions made during implementation:**
- Used SQLite (not PostgreSQL) for development. `DATABASE_URL` in `.env` switches to Postgres with zero code changes.
- APScheduler chosen over Celery — no Redis dependency needed for Phase 1 job volume.
- Used `BackgroundScheduler` (sync threads) rather than `AsyncIOScheduler` to keep SQLAlchemy sessions simple.
- In DEBUG mode the scheduler still starts but all collector jobs return early — preserves the real code path for testing.
- Debug DB is auto-seeded on first startup if the `fx_rates` table is empty — no manual step needed.
- Frontend uses CSS Modules + CSS variables (dark theme) rather than Tailwind — avoids build-time dependency complexity.

---

### Phase 2 — Intelligence Layer

**Goal:** NLP sentiment scoring, weather maps, smarter alerting. Builds on Phase 1 infra.

| Layer | Technology | Purpose |
|---|---|---|
| NLP / Sentiment | FinBERT (HuggingFace `transformers`) | Pre-trained financial sentiment model; scores news per topic |
| ML Runtime | PyTorch | Inference only — no model training required |
| Weather Mapping | Open-Meteo API + Leaflet.js / react-leaflet | District-level flood risk map; supplier port weather |
| Alert expansion | Extend Phase 1 engine | Sentiment-triggered and weather-triggered rules; user-configurable thresholds |
| SMS Alerts | Twilio (optional) | Escalation channel for high-priority alerts |

**Notes:**
- FinBERT runs inference on CPU — no GPU needed.
- Leaflet.js integrates cleanly into React via `react-leaflet`.

---

### Phase 3 — Validation & Handover

**Goal:** Backtesting, UAT, documentation, data source reliability audit.

| Activity | Tool / Approach |
|---|---|
| Backtesting alert rules | Python scripts against historical PostgreSQL data (2022–2025) |
| User acceptance testing | Simulated procurement scenarios against live dashboard |
| Documentation | Markdown user guide + FastAPI auto-generated OpenAPI/Swagger docs |
| Data source audit | Manual review of free API fragility; identify paid fallbacks |
| Production deployment | VPS or AWS EC2 with Docker Compose |
| ERP scoping (optional) | Discovery meeting with ACL IT — no code; informs future Phase 4 |

---

## Implementation Log

### Phase 1 Progress

| Task | Status | Notes |
|------|--------|-------|
| Project structure + uv setup | ✅ Done | `backend/` with `app/`, `debug/` subdirs; `uv` manages venv |
| ORM models (fx, commodities, weather, news, alerts) | ✅ Done | SQLAlchemy declarative; all tables created on startup |
| Debug generators | ✅ Done | `debug/generators/` — random-walk FX, commodity prices, monsoon weather, templated news |
| Seed script | ✅ Done | `debug/seed.py` — run standalone or auto-called on startup if DB is empty |
| Services layer | ✅ Done | `app/services/` — all business logic; routers only do HTTP concerns |
| FastAPI routers | ✅ Done | `/api/v1/fx`, `/commodities`, `/weather`, `/news`, `/alerts`, `/calculator` |
| Rule-based alert engine | ✅ Done | CRUD for rules + 15-min scheduler check; optional SMTP email |
| Landed cost calculator | ✅ Done | `POST /api/v1/calculator/landed-cost`; uses live DB prices or custom overrides |
| Collector stubs | ✅ Done | All four collectors stubbed with TODO comments; ready to implement in Phase 2 |
| Scheduler | ✅ Done | APScheduler with 15-min FX + alert jobs, 1-h commodity/weather/news jobs |
| Vite + React + TypeScript frontend | ✅ Done | Recharts + React Query; dark dashboard theme |
| Overview panel | ✅ Done | 5 stat cards: USD/LKR, copper, aluminium, high-risk locations, today's news count |
| FX panel | ✅ Done | 30/60/90d toggle, line chart with avg reference line, 5 summary stats |
| Commodity panel | ✅ Done | COPPER/ALUMINIUM toggle, 30/60/90d chart, colour-coded change |
| Weather panel | ✅ Done | All Sri Lanka districts + supplier ports, flood risk colour-coded |
| News feed | ✅ Done | Topic filter chips, recency, truncated summaries |
| Cost calculator UI | ✅ Done | Material + quantity inputs, optional price overrides, LKR output |
| Docker Compose | ✅ Done | Compose file with backend + frontend; PostgreSQL section commented for prod |

### Phase 2 Progress

| Task | Status | Notes |
|------|--------|-------|
| FinBERT news sentiment integration | Not started | |
| Topic-filtered news feed with sentiment scores | Not started | |
| Historical cost-impact analysis (what-if calculator) | Not started | |
| Weather panel: district-level flood risk map | Not started | |
| Supplier country weather (UAE, China, Vietnam ports) | Not started | Phase 1 already seeds port data; Phase 2 adds live fetch |
| Alert engine expansion (sentiment + weather rules) | Not started | |
| User-configurable alert thresholds | Not started | Backend CRUD already built; Phase 2 adds frontend UI |

### Phase 3 Progress

| Task | Status | Notes |
|------|--------|-------|
| Backtest alert rules (2022–2025 historical data) | Not started | |
| User acceptance testing | Not started | |
| System documentation and user guide | Not started | |
| Data source reliability audit | Not started | |
| ERP integration scoping (optional) | Not started | |

---

## Running the Project

### Backend (debug mode)
```bash
cd backend
uv run uvicorn app.main:app --reload
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm run dev
# http://localhost:5173
```

### Reseed the database
```bash
cd backend
# delete procurement_intel.db first, then restart the server
# or run manually:
uv run python -m debug.seed
```

---

*Last updated: 2026-05-13 | Current phase: Phase 1 complete — Phase 2 next*
