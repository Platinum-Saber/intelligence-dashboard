# ACL Cables PLC — Procurement Intelligence Dashboard
## Implementation Details

> **Purpose of this file:** Tracks tech stack decisions and implementation progress per phase. Updated as each phase is completed. Read alongside `project_detailes.md` for full context.

---

## Document History

| Version | Date | Change Summary |
|---------|------|----------------|
| 0.1 | 2026-05-13 | Initial draft — tech stack documented per phase, pre-implementation |
| 0.2 | 2026-05-13 | Phase 1 fully implemented — backend, debug layer, and frontend complete |
| 0.3 | 2026-05-13 | Phase 2 fully implemented — FinBERT sentiment, live collectors, weather map, alerts UI, cost history |
| 0.4 | 2026-05-13 | UI refactor — shadcn/ui components, sidebar navigation, ACL brand colours, light/dark mode |
| 0.5 | 2026-05-13 | CSS variable conflict fix, light/dark mode verified, alert severity coloring added |

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
- Frontend uses CSS Modules + CSS variables (dark theme) rather than Tailwind — avoids build-time dependency complexity. *(Tailwind added later in the UI refactor; CSS modules remain alongside Tailwind for existing components.)*

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
| FinBERT news sentiment integration | ✅ Done | `app/services/sentiment_service.py` — lazy-loaded, CPU inference, graceful fallback if disabled |
| Topic-filtered news feed with sentiment scores | ✅ Done | `sentiment` badge on each news item; `SENTIMENT_ENABLED=false` in .env skips FinBERT |
| Historical cost-impact analysis | ✅ Done | `GET /api/v1/calculator/history` + `CostHistory` area chart; shows landed cost over time |
| Weather panel: district-level flood risk map | ✅ Done | Leaflet `CircleMarker` map centred on Sri Lanka; colour-coded by flood risk |
| Supplier country weather (live) | ✅ Done | `weather_collector.py` using Open-Meteo (free, no key); scheduler runs hourly |
| FX live collector | ✅ Done | `fx_collector.py` using exchangerate-api.com; requires `FX_API_KEY` in .env |
| News live collector | ✅ Done | `news_collector.py` using NewsAPI.org; requires `NEWSAPI_KEY` in .env |
| Commodity live collector | ✅ Done | `commodity_collector.py` using Yahoo Finance (`HG=F`, `ALI=F`); free, no key |
| Sentiment-based alert rules | ✅ Done | `SENTIMENT_NEGATIVE` rule type; threshold format: `TOPIC:pct` (e.g. `COPPER:0.60`) |
| Alert rules management UI | ✅ Done | `AlertsPanel` component — list, enable/disable, create, delete, manual check, event log |
| News sentiment summary endpoint | ✅ Done | `GET /api/v1/news/sentiment-summary` + `SentimentBar` stacked bar per topic |

**Decisions made during Phase 2:**
- torch `2.12.0+cpu` (117 MB) installed via PyTorch CPU wheel index — avoids 2.5 GB GPU wheel.
- FinBERT loads lazily on first call; `SENTIMENT_ENABLED=false` skips it entirely. Model download (~400 MB) happens on first use.
- Open-Meteo weather collector runs in all modes (debug and prod) — it's free and keyless, making it safe to always run.
- All other live collectors are gated: FX requires `FX_API_KEY`, news requires `NEWSAPI_KEY`, commodities uses an unofficial Yahoo Finance endpoint (no key, but fragile — mark as paid-fallback candidate in Phase 3 audit).
- Leaflet map uses `CircleMarker` (not default Marker) to avoid Vite icon resolution issues.
- `CostHistory` joins daily commodity prices to nearest FX rate by calendar date — lookback of up to 7 days if FX reading is missing for a given day.

### UI Refactor Progress (completed 2026-05-13)

| Task | Status | Notes |
|------|--------|-------|
| Tailwind CSS v3 + PostCSS config | ✅ Done | `tailwind.config.js`, `postcss.config.cjs`; `darkMode: ["class"]` |
| shadcn/ui components | ✅ Done | Button, Badge, Card, Input, Label, Switch, Select, Dialog, Tabs, Separator, ScrollArea, Tooltip, Skeleton — all hand-written in `src/components/ui/` |
| `@/` path alias | ✅ Done | `vite.config.ts` + `tsconfig.app.json` paths |
| Centralised CSS token system | ✅ Done | `src/styles/globals.css` — `--c-*` semantic vars + Tailwind raw HSL tokens; `:root` light, `.dark` dark |
| ACL brand colours | ✅ Done | Blue `hsl(220,77%,48%)`, Gold `hsl(43,92%,52%)` wired as primary and accent |
| Legacy CSS var aliases | ✅ Done | `--bg`, `--surface`, `--surface-2`, `--text`, `--text-muted`, `--green`, `--red`, `--yellow`, `--orange` aliased to `--c-*`. `--border` and `--accent` are NOT aliased (see decisions below). |
| CSS module updates | ✅ Done | All 8 CSS modules updated: `var(--border)` → `var(--c-border)`, `var(--accent)` → `var(--c-primary)`. Recharts inline props updated in `FXPanel.tsx`, `CommodityPanel.tsx`, `CostHistory.tsx`. |
| Light / dark mode | ✅ Done | `useTheme` hook; persists to `localStorage`; respects `prefers-color-scheme` on first visit. Light mode shows white/near-white backgrounds. |
| Sidebar navigation | ✅ Done | `AppSidebar.tsx` — branded dark ACL sidebar, 4 nav items, theme toggle, mobile hamburger |
| React Router v7 | ✅ Done | `BrowserRouter` + 4 routes in `App.tsx` |
| Home page | ✅ Done | All stat panels in responsive grid |
| Calculator page | ✅ Done | shadcn form with Select/Input/Label; methodology card; CostHistory chart |
| Alerts page | ✅ Done | Event table with search, row limit selector, and severity-based row coloring |
| Alert severity coloring | ✅ Done | Fetches rules + events; joins by `rule_id`; colors rows: Critical→red, High→orange, Medium→yellow, Favourable→green, FX→blue |
| Configurations page | ✅ Done | Tabs: Alert Rules (CRUD with Dialog), App Settings (env vars), Model Tuning (FinBERT + manual scoring) |

**Decisions made during UI refactor:**
- Sidebar is always dark (ACL branded navy) in both light and dark modes — consistent with enterprise dashboard conventions.
- shadcn components written by hand (no `npx shadcn add`) to avoid interactive CLI in Windows PowerShell.
- `postcss.config.cjs` (not `.js`) because `package.json` has `"type": "module"` — CJS extension bypasses ESM parsing.
- `baseUrl`/`paths` required `"ignoreDeprecations": "6.0"` in TypeScript 6 to suppress the deprecation warning while keeping the `@/` alias working.

**Decisions made during CSS fix (v0.5):**
- `--border` and `--accent` are intentionally NOT added to the legacy alias section. These names are reserved by Tailwind's `hsl(var(--border))` pattern; aliasing them to full `hsl()` values would create `hsl(hsl(...))` — invalid CSS — breaking all Tailwind-generated borders and accent classes.
- Instead, existing CSS modules were updated to reference `var(--c-border)` and `var(--c-primary)` directly; Recharts `stroke` and `contentStyle` props similarly updated.
- `html, body` background uses `var(--c-bg)` and `var(--c-text)` directly rather than `@apply bg-background text-foreground` — avoids Tailwind processing indirection and ensures light mode (white) and dark mode (dark navy) reliably apply.
- Global `input`/`select` element styles added to `globals.css` using `--c-*` vars so native form elements adapt to both modes. Scoped to elements without a Tailwind class prefix to avoid fighting shadcn Input component styles.

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

### Trigger FinBERT scoring manually
```bash
cd backend
# via API (POST, returns count scored):
curl -X POST http://localhost:8000/api/v1/news/score-now
# or directly:
uv run python -c "
from app.database import SessionLocal
from app.services.sentiment_service import score_unscored_news
db = SessionLocal(); print(score_unscored_news(db, 200)); db.close()
"
```

---

*Last updated: 2026-05-13 | Current phase: UI refactor complete (v0.5) — Phase 3 (validation & handover) next*
