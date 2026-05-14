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
| 0.6 | 2026-05-13 | Phase 3 complete — backtesting service, UAT scenarios, data source audit, Backtest page, docs |
| 0.7 | 2026-05-14 | Bug fixes — unit test infrastructure added; `sentiment_service.py` pipeline import fix; `datetime.utcnow()` deprecation resolved across all services and tests |
| 0.8 | 2026-05-14 | Production config — Docker Compose PostgreSQL/TimescaleDB enabled; `psycopg2-binary` added; `.dockerignore` created; live API keys wired for FX and News; scheduler intervals tuned; collectors fire on startup; unused TS import fixed |
| 0.9 | 2026-05-14 | Production data fixes — timezone mismatch resolved; news collector extended to 24h; historical backfill script; daily deduplication across all chart series; landed cost alert engine; 4 live alert rules; FinBERT enabled; App Settings live endpoint; UAT scenarios redesigned |
| 1.0 | 2026-05-14 | Phase 4 complete — sentiment guard, per-rule email, FX % change + sustained alerts, drought/heatwave/seasonal climate signals, migrations.py, API client URL fixes, ConfigPage query key fix, 6-scenario UAT covering all 7 rules |
| 1.1 | 2026-05-14 | Phase 5 complete — content-based news topic classification, CBSL rate overlay on FX chart, SLFRS S2 climate export (JSON+CSV), composite cross-signal alert builder; buyer-perspective FinBERT sentiment fix; NewsAPI rate-limit optimisation (2 broad queries, 72h lookback, pageSize=100); startup backfill for 7-day FX+commodity history; weather map height increased |

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
| Backtest alert rules against historical DB data | ✅ Done | `app/services/backtest_service.py` + `app/routers/backtest.py`; endpoint: `POST /api/v1/backtest/run`; evaluates all rules across historical snapshots |
| UAT Scenarios | ✅ Done | 5 pre-built scenarios in `backtest_service.py`; endpoint: `POST /api/v1/backtest/scenario/run`; UI in `/backtest` page (UAT Scenarios tab) |
| System documentation and user guide | ✅ Done | `docs/user_guide.md` — procurement team guide covering all pages, alert thresholds, FAQ |
| Data source reliability audit | ✅ Done | `app/services/datasource_service.py` + `app/routers/datasources.py`; endpoint: `GET /api/v1/datasources/audit`; UI tab in Configurations page |
| Deployment runbook | ✅ Done | `docs/deployment_runbook.md` — dev setup, Docker, VPS/EC2, PostgreSQL, HTTPS, security checklist, troubleshooting |
| ERP integration scoping (optional) | Deferred | Discovery meeting with ACL IT — no code; informs Phase 4 |

**Decisions made during Phase 3:**
- Backtesting pre-fetches all historical data for the date range in one pass (avoids N+1 per-day queries); processes entirely in Python — performant enough for 365 days on SQLite.
- SEED_DAYS default raised from 90 to 365 to give backtesting a full year of generated data.
- UAT scenarios are hardcoded in the service layer (not DB-stored) — they're test fixtures, not user configuration.
- Data source audit derives status from DB freshness (last reading timestamp + 24h count) rather than live API calls — avoids consuming API quota on every audit request.
- Phase badge updated from "Phase 2" to "Phase 3" in `App.tsx` and `AppSidebar.tsx`.

---

### Bug Fixes (2026-05-14)

| Fix | Files Changed | Notes |
|-----|---------------|-------|
| Unit test infrastructure | `pyproject.toml` | Added `pytest` as a dev dependency (`uv add --dev pytest`); added `[tool.pytest.ini_options] pythonpath = ["."]` so pytest resolves the `app` package |
| `sentiment_service` pipeline mockability | `app/services/sentiment_service.py` | `from transformers import pipeline` moved to module level (with `try/except ImportError` fallback); previously a local import inside `_get_pipeline()` meant `patch("app.services.sentiment_service.pipeline")` raised `AttributeError` in all 4 `TestGetPipeline` tests |
| `datetime.utcnow()` deprecation | `app/services/sentiment_service.py`, `app/services/news_service.py`, `app/services/weather_service.py`, `tests/test_sentiment_service.py`, `tests/test_news_service.py`, `tests/test_weather_service.py`, `tests/conftest.py` | Replaced all `datetime.utcnow()` calls with `datetime.now(UTC)` and updated imports to include `UTC`; Python 3.12 flags `utcnow()` as deprecated |

**Running the unit tests:**
```bash
cd backend
uv run pytest tests/ -v
# 82 passed; remaining warnings are SQLAlchemy internals (not actionable)
```

---

### Production Data Fixes (2026-05-14, v0.9)

| Fix | Files Changed | Notes |
|-----|---------------|-------|
| Timezone mismatch in service layer | `app/services/news_service.py`, `app/services/sentiment_service.py`, `app/services/weather_service.py` | PostgreSQL stores naive UTC timestamps; `datetime.now(UTC)` returns timezone-aware. Fixed with `.replace(tzinfo=None)` so SQLAlchemy comparisons no longer raise errors or return empty results |
| News collector lookback extended | `app/collectors/news_collector.py` | Changed 6h → 24h lookback window; `fetched_at` field (collection timestamp) now explicitly set in article dicts — required because `bulk_insert_mappings` bypasses ORM column defaults |
| Datasource audit uses `fetched_at` | `app/services/datasource_service.py` | News freshness check now uses `fetched_at` (actual collection time) instead of `published_at` (NewsAPI free tier has 24h publication delay, so `published_at` always appeared stale) |
| Historical data backfill script | `backend/backfill_history.py` (new) | One-shot script using Yahoo Finance historical chart API (`range=9d`) for USDLKR=X, HG=F, ALI=F and NewsAPI date-range queries; deduplicates by date; run via `uv run python backfill_history.py` inside the container |
| Daily deduplication — FX history | `app/services/fx_service.py` | `get_history()` now groups rows by calendar date (last-write-wins) before returning; prevents duplicate x-axis points in `FXPanel` chart |
| Daily deduplication — commodity history | `app/services/commodity_service.py` | Same pattern as FX: `get_history()` deduplicates by date before returning |
| Daily deduplication — landed cost history | `app/routers/calculator.py` | `/calculator/history` endpoint has its own raw DB query (bypasses service layer); `comm_by_date` dict added to deduplicate commodity rows before building the response |
| Landed cost alert engine | `app/services/alert_service.py` | Rewrote `check_alerts()` to evaluate copper and aluminium alerts on **landed cost** (LME price × USD/LKR rate) rather than raw USD price change. Added `_price_before(db, model, cutoff)` helper (queries `timestamp <= cutoff ORDER BY DESC LIMIT 1`) to retrieve the prior-day reading reliably. Added `_landed_cost_change_pct(price_now, fx_now, price_ref, fx_ref)` helper. Alert messages now report LKR/tonne values and % landed cost change |
| 4 alert rules created in production DB | `app/services/alert_service.py` (logic), DB rows | Rule 1: Copper buy window (landed cost 24h change < -2%); Rule 2: Aluminium buy window (landed cost 24h change < -2%); Rule 3: Sri Lanka flood risk (weather HIGH trigger); Rule 4: Adverse FX (USD/LKR > 330) |
| FinBERT sentiment enabled | `docker-compose.yml` | `SENTIMENT_ENABLED=false` → `SENTIMENT_ENABLED=true`; model downloads ~400 MB on first startup |
| App Settings live endpoint | `app/main.py` | Added `GET /api/v1/settings`; reads `settings.*` config values and live APScheduler job intervals via `scheduler.get_jobs()`; replaces the previously hard-coded frontend display |
| App Settings frontend rewrite | `frontend/src/api/settings.ts` (new), `frontend/src/pages/ConfigPage.tsx` | `settings.ts` exports `fetchAppSettings()` using the new endpoint; `AppSettingsTab` in `ConfigPage.tsx` rewritten from a static array to `useQuery({ queryKey: ["app-settings"], queryFn: fetchAppSettings })`; badge colours now reflect live values (red for false/not configured, green for true) |
| UAT scenarios redesigned | `app/services/backtest_service.py` | All 5 UAT scenarios replaced to match the 4 actual production alert rules: (1) `aluminium_buy_window` — Rule 2 only, (2) `copper_market_dip` — Rules 1+2, (3) `monsoon_disruption` — Rule 3, (4) `fx_adverse_rate` — Rule 4, (5) `combined_peak_stress` — all 4 rules |
| Backtest engine: landed cost computation | `app/services/backtest_service.py` | Historical backtest loop now computes copper and aluminium landed cost change using actual FX rate for both current and prior day; scenario parameters renamed `copper_landed_change_pct` / `aluminium_landed_change_pct` for clarity |

**Decisions made during v0.9 fixes:**
- Deduplication is applied at the service/router layer only — raw DB retains all intraday readings for alert evaluation and audit purposes. A unique-per-day DB constraint was explicitly avoided because it would interfere with the scheduler's continuous insert pattern.
- `_price_before()` uses `timestamp <= cutoff ORDER BY DESC LIMIT 1` rather than `get_history(days=1)` because the Yahoo Finance backfill inserts daily prices with 04:00 UTC timestamps; a 24h lookback computed at midday would miss those entries.
- `fetched_at` is explicitly set in news collector article dicts rather than relying on DB defaults, because `bulk_insert_mappings` bypasses SQLAlchemy ORM column defaults.
- `SENTIMENT_ENABLED=true` in `docker-compose.yml` persists across container restarts; no manual step needed for future deployments.
- The `/api/v1/settings` endpoint reads `scheduler.get_jobs()` at request time so job intervals are always accurate, even if scheduler configuration changes.

---

### Phase 4 Progress (2026-05-14, v1.0)

#### Sprint 4.1 — Bug Fixes

| Fix | Files Changed | Notes |
|-----|---------------|-------|
| Sentiment min-article guard | `alert_service.py`, `backtest_service.py` | `SENTIMENT_MIN_ARTICLES` env var (default 5); guard applied identically in both services; article count included in alert message |
| Per-rule email recipients | `alert_service.py` | `_try_notify(event, rule)` now reads `rule.email_recipients`, splits on comma, falls back to `settings.alert_from_email`; `rule` object threaded from `check_alerts()` call site |

#### Sprint 4.2 — FX Alert Enhancements

| Feature | Files Changed | Notes |
|---------|---------------|-------|
| FX daily % change alert | `alert_service.py`, `ConfigPage.tsx`, `schemas/alerts.py`, `types/index.ts` | New `usd_lkr_change_pct` metric; switches `get_latest()` → `get_summary()` so both absolute rate and % change are available from one query; `ConfigPage` shows `(%)` unit label |
| FX multi-day sustained alert | `models/alerts.py`, `migrations.py`, `fx_service.py`, `alert_service.py`, `ConfigPage.tsx` | `trend_window_hours` column on `AlertRule` (shared with weather trend); `rate_sustained_above(db, threshold, hours)` in `fx_service.py`; backwards-compatible: `NULL` falls back to snapshot check; `ConfigPage` shows optional "Sustained for (hours)" input |
| Schema migration infrastructure | `backend/app/migrations.py` (NEW) | `MIGRATIONS` list of idempotent `ALTER TABLE … IF NOT EXISTS` SQL statements; `run_migrations(engine)` called from `lifespan` after `create_all`; handles both PostgreSQL (native IF NOT EXISTS) and SQLite (swallows unsupported syntax silently) |

#### Sprint 4.3 — Climate Alert Enhancements

| Feature | Files Changed | Notes |
|---------|---------------|-------|
| Drought risk detection | `models/weather.py`, `schemas/weather.py`, `weather_service.py`, `alert_service.py`, `scheduler/jobs.py`, `migrations.py` | `drought_risk VARCHAR(20)` column on `WeatherReading`; `get_drought_risk()` computes 14-day rolling deficit against 5 mm/day baseline; `update_drought_risk_latest()` stamps the most recent reading; scheduler calls update after every bulk insert |
| Heatwave alert rule | `weather_service.py`, `alert_service.py`, `ConfigPage.tsx` | `consecutive_hot_days(db, location, threshold_c, window=3)` counts days above threshold in a rolling window; alert fires when count ≥ 3 at any Sri Lanka district |
| Multi-day weather trend alert | `weather_service.py`, `alert_service.py` | `location_elevated_for_hours(db, location, min_risk, hours)` checks every reading in the window is ≥ `min_risk`; used when `rule.trend_window_hours` is set — backwards-compatible |
| Seasonal / monsoon baseline | `backend/app/utils/seasonal_baseline.py` (NEW), `alert_service.py`, `AlertsPage.tsx` | `MONSOON_CALENDAR` dict (Southwest: May–Sep Western/Southern; Northeast: Oct–Jan Northern/Eastern); `seasonal_context()` appends `[Seasonal context: …]` suffix to weather alert messages; `SeasonalBadge` component in `AlertsPage` parses suffix and shows green "Seasonal" or red "Anomalous" chip |

#### UI & Integration Fixes

| Fix | Files Changed | Notes |
|-----|---------------|-------|
| API client absolute URLs | `api/client.ts`, `api/alerts.ts` | Added `put<T>` and `del` helpers using `BASE_URL` (`http://localhost:8000`); `toggleAlertRule` and `deleteAlertRule` in `alerts.ts` now use these instead of raw `fetch` with relative paths (nginx on port 5173 has no proxy config — relative paths silently 404'd) |
| Check Now query key mismatch | `ConfigPage.tsx` | `checkMutation.onSuccess` now invalidates both `["alert-events"]` and `["alert-events-full"]`; previously `AlertsPage` (which uses `["alert-events-full", limit]`) never refreshed after a manual check |
| Score Now fetch | `ConfigPage.tsx` | `ModelTuningTab.scoreNow()` now uses `apiPost` from `client.ts` instead of raw `fetch` with a relative path |
| Drought badge on flood alerts | `AlertsPage.tsx` | `getSeverity` now strips the `[Seasonal context:]` suffix from the message before keyword classification; the suffix contains "flood/drought risk" text that was mis-matching the drought branch |
| Phase label | `App.tsx`, `AppSidebar.tsx` | Updated from "Phase 3 · Debug Mode" to "Phase 4 · Debug Mode" in both header and sidebar footer |

#### UAT Scenarios & Backtest Engine Update

| Change | Files Changed | Notes |
|--------|---------------|-------|
| 6-scenario UAT covering all 7 Phase 4 rules | `backtest_service.py` | Replaced old 5 scenarios; added "Drought & Heatwave Advisory" (Rules 5+6) and "FX Rate Shock" (Rules 4+7, replaces broken "FX Adverse Rate"); updated "Combined Peak Stress Event" to trigger all 7 rules simultaneously |
| ScenarioConditions extended | `schemas/backtest.py`, `api/backtest.ts` | Added `usd_lkr_change_pct`, `drought_risk_locations`, `max_temp_c` fields (all optional with defaults); Pydantic backwards-compatible |
| Backtest engine: new per-day metrics | `backtest_service.py` | Historical loop now computes `usd_lkr_change_pct` from consecutive FX readings; `drought_risk_locations` and `max_temp_c` from `weather_readings` per day; all three passed to `_evaluate_rule_against_snapshot` |
| Scenario card chips | `BacktestPage.tsx` | Added blue FX-change chip (highlighted when > 1.5%), orange drought chip, red temperature chip (shown when > 35 °C) |

**Decisions made during Phase 4:**
- `migrations.py` kept separate from `main.py` by design — migration SQL is a concern of the data layer, not application startup orchestration.
- Drought risk is computed as a two-pass operation: bulk insert all weather readings first, then compute the 14-day rolling deficit and stamp `drought_risk` on the most recently inserted row. This keeps the collection and aggregation phases cleanly separated.
- Seasonal context is appended to alert messages as a `[Seasonal context: …]` suffix rather than a separate DB field — preserves the existing `AlertEvent.message` schema without migration, and the frontend can split on the delimiter to display it separately.
- `rate_sustained_above` and `location_elevated_for_hours` share the same `trend_window_hours` column and the same UI control ("Sustained for (hours)") — one schema field handles both FX and weather trend rules.
- 3 new Phase 4 alert rules added via `POST /api/v1/alerts/rules`: Sri Lanka Drought Risk (drought_risk eq HIGH), Sri Lanka Heatwave Risk (heatwave gt 35 °C), FX Daily Volatility (usd_lkr_change_pct gt 1.5%).

---

### Phase 5 Progress (2026-05-14, v1.1)

#### Sprint 5.1 — News Intelligence Upgrade

| Change | Files Changed | Notes |
|--------|---------------|-------|
| Content-based topic classification | `news_collector.py` | `TOPIC_KEYWORDS` dict (FX, COPPER, ALUMINIUM, TRADE, LOGISTICS); `reclassify_topic(headline, summary)` scores keyword hits — assigns topic only on ≥2 hits; called on every collected article |
| Broad query consolidation | `news_collector.py` | Replaced 5 per-topic queries with 2 broad queries; `pageSize=100` (API max); 72h lookback (clears 24h free-tier publication delay); URL deduplication via `seen_urls` set; reduces daily API usage from ~40 req to ~16 req |
| FinBERT headline+summary scoring | `sentiment_service.py` | `score_unscored_news()` now scores on `headline + summary` (up to 512 chars) instead of headline only — richer signal for short headlines |
| Buyer-perspective sentiment | `sentiment_service.py` | `_buyer_key(topic, raw_label)` inverts POSITIVE↔NEGATIVE for COPPER and ALUMINIUM topics before writing to DB — procurement buyers pay more when commodity prices rise; DB stores the procurement-correct label; no read-time inversion anywhere |
| Backfill endpoint | `routers/news.py` | `POST /api/v1/news/reclassify-all` calls `reclassify_all_topics(db)` to backfill topic classification on existing articles |

#### Sprint 5.2 — CBSL Rate Overlay

| Change | Files Changed | Notes |
|--------|---------------|-------|
| `CBSLRate` model | `models/cbsl.py` (new) | `id`, `effective_date (Date, indexed)`, `rate (Float)`, `note (String 200)` |
| CBSL router | `routers/cbsl.py` (new) | Full CRUD: `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`; `GET /history?days=N` |
| FX chart step-function overlay | `FXPanel.tsx` | `fetchCBSLHistory(days)` query; `buildCBSLSteps()` maps CBSL entries onto market date axis; second Recharts `<Line type="stepAfter">` in gold dashed style; `<Legend>` added |
| CBSL Rates Config tab | `ConfigPage.tsx` | New tab with list of rates, add/edit/delete dialog (date picker + rate + note fields) |
| Registration | `main.py`, `models/__init__.py`, `migrations.py` | Router mounted at `/api/v1/fx/cbsl`; `CBSLRate` imported so `create_all` picks it up; no migration needed (table created fresh) |

#### Sprint 5.3 — SLFRS S2 Climate Export

| Change | Files Changed | Notes |
|--------|---------------|-------|
| `climate_report_service.py` | `services/climate_report_service.py` (new) | `generate_report(db, start_date, end_date)` aggregates: HIGH/CRITICAL flood days per district, MEDIUM+ drought days per district, temperature extremes, supplier port disruption days, alert events by severity; `generate_csv()` serialises same data as CSV string |
| Climate router | `routers/climate_report.py` (new) | `GET /api/v1/climate/report` → JSON; `GET /api/v1/climate/report/csv` → `StreamingResponse` CSV download |
| Climate Report Config tab | `ConfigPage.tsx` | Date range pickers, Generate Report button, summary table, Download CSV button; SLFRS S2 disclaimer note |
| Registration | `main.py` | Router mounted at `/api/v1/climate` |

#### Sprint 5.4 — Cross-Signal Composite Alerts

| Change | Files Changed | Notes |
|--------|---------------|-------|
| `composite_condition` column | `models/alerts.py`, `migrations.py` | `TEXT` column on `AlertRule`; stores JSON array of sub-conditions `[{metric, op, value}]`; `ALTER TABLE … IF NOT EXISTS` migration |
| `_eval_single_metric()` | `alert_service.py` | Extracted reusable per-metric evaluator used by both individual rules and composite evaluation |
| `evaluate_composite()` | `alert_service.py` | Deserialises `composite_condition`; evaluates all sub-conditions with AND semantics — any failure short-circuits; returns `(triggered, [desc_strings])` |
| COMPOSITE rule type branch | `alert_service.py` | `elif rule.rule_type == "COMPOSITE"` block in `check_alerts()` calls `evaluate_composite()` before the sentiment branch |
| Composite rule builder UI | `ConfigPage.tsx` | `COMPOSITE` added to rule type dropdown; when selected, single-condition row replaced with dynamic list (metric + op + value per row); Add/Remove condition buttons; minimum 2 sub-conditions; serialised to JSON on submit |
| Schema + types | `schemas/alerts.py`, `types/index.ts` | `composite_condition: str | None` added to `AlertRuleIn`, `AlertRuleOut`; `CompositeCondition` interface in TypeScript |

#### Additional Fixes & Infrastructure (Phase 5 session)

| Fix | Files Changed | Notes |
|-----|---------------|-------|
| Startup 7-day backfill | `scheduler/jobs.py`, `fx_collector.py`, `commodity_collector.py` | `_backfill_history()` runs synchronously before scheduler starts; checks last 8 days; inserts only missing dates; FX via Yahoo Finance `USDLKR=X`, commodities via `HG=F`/`ALI=F` with `range=7d`; idempotent — safe on every restart |
| `fetch_usd_lkr_history()` | `fx_collector.py` | New function using Yahoo Finance `USDLKR=X` free chart endpoint; returns `[{date, rate}]` |
| `fetch_commodity_history()` | `commodity_collector.py` | New function using Yahoo Finance chart `range=Nd`; returns `[{date, price_usd}]`; converts copper lb→tonne |
| Weather map height | `WeatherMap.module.css` | `.mapWrap` height increased from `320px` → `700px` (portrait aspect ratio) |
| Alert rules recreated | via `curl POST /api/v1/alerts/rules` | All 7 production rules restored after DB wipe: Copper Buy Window, Aluminium Buy Window, Sri Lanka Flood Risk, Adverse FX Rate (>330), Sri Lanka Drought Risk, Sri Lanka Heatwave Risk (>35°C ×3 days), FX Daily Volatility (>1.5%/day) |

**Decisions made during Phase 5:**
- Buyer-perspective sentiment is stored in DB (not computed at read time) — DB always reflects procurement-correct labels; `get_recent()` and `get_sentiment_summary()` both read as-is with no inversion logic; single source of truth.
- NewsAPI rate limit mitigation: 2 broad queries cover all 5 topics; `reclassify_topic()` handles per-article classification from content, not from which query returned it. Free tier budget: ~16 req/day (well under 100 req/day cap).
- Startup backfill uses Yahoo Finance historical chart API for both FX and commodities — avoids consuming the paid exchangerate-api.com quota for historical lookups. Weekend market closure days are naturally absent (no Yahoo Finance data for Sat/Sun).
- `composite_condition` stored as JSON `TEXT` rather than a relational sub-table — avoids schema complexity for a variable-length list; serialised/deserialised in the service layer; UI renders it as parsed "metric op value AND …" text.
- CBSL rates are manually entered (not scraped) — CBSL announces rate changes only a few times per year, making manual entry the correct UX choice.

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

*Last updated: 2026-05-14 | Current phase: Phase 5 complete (v1.1)*
