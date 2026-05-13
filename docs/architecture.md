# ACL Cables Procurement Intelligence Dashboard — Architecture Document

> **Version:** 1.0 | **Date:** 2026-05-13 | **Status:** Phase 3 (all phases complete)

---

## 1. System Overview

The Procurement Intelligence Dashboard is a three-tier web application that aggregates external market data, processes it through an intelligence layer, and presents it to procurement decision-makers via a browser-based dashboard.

```mermaid
graph TB
    subgraph EXT["External Data Sources"]
        FX["exchangerate-api.com<br/>USD/LKR rates"]
        YF["Yahoo Finance<br/>LME Copper & Aluminium"]
        OM["Open-Meteo<br/>Weather / Flood risk"]
        NA["NewsAPI.org<br/>Supply chain news"]
    end

    subgraph BACKEND["Backend — Python / FastAPI"]
        SCH["APScheduler<br/>(6 background jobs)"]
        COL["Collectors<br/>fx · commodity · weather · news"]
        SVC["Services<br/>fx · commodity · weather · news · alert · sentiment · backtest"]
        NLP["FinBERT NLP<br/>(ProsusAI/finbert)"]
        API["REST API<br/>(FastAPI / OpenAPI)"]
        DB[("SQLite (dev)<br/>PostgreSQL (prod)")]
    end

    subgraph FRONTEND["Frontend — React / TypeScript"]
        PAGES["Pages<br/>Home · Calculator · Alerts · Backtesting · Config"]
        QUERY["@tanstack/react-query<br/>Data fetching & caching"]
        CHARTS["Recharts + Leaflet<br/>Charts & weather map"]
    end

    BROWSER["Procurement Team<br/>(Browser)"]

    EXT --> COL
    COL --> DB
    SCH --> COL
    SCH --> NLP
    SCH --> SVC
    NLP --> DB
    DB --> SVC
    SVC --> API
    API -->|"REST / JSON"| QUERY
    QUERY --> PAGES
    PAGES --> CHARTS
    CHARTS --> BROWSER
```

---

## 2. Layer Architecture

```mermaid
graph LR
    subgraph "Presentation Layer"
        UI_HOME["Home Page"]
        UI_CALC["Calculator Page"]
        UI_ALERTS["Alerts Page"]
        UI_BACKTEST["Backtesting Page"]
        UI_CONFIG["Config Page"]
    end

    subgraph "API Layer (FastAPI Routers)"
        R_FX["/api/v1/fx"]
        R_COMM["/api/v1/commodities"]
        R_WX["/api/v1/weather"]
        R_NEWS["/api/v1/news"]
        R_ALERTS["/api/v1/alerts"]
        R_CALC["/api/v1/calculator"]
        R_BT["/api/v1/backtest"]
        R_DS["/api/v1/datasources"]
    end

    subgraph "Service Layer"
        S_FX["fx_service"]
        S_COMM["commodity_service"]
        S_WX["weather_service"]
        S_NEWS["news_service"]
        S_ALERT["alert_service"]
        S_SENT["sentiment_service"]
        S_BT["backtest_service"]
        S_DS["datasource_service"]
    end

    subgraph "Data Layer"
        M_FX["FXRate"]
        M_COMM["CommodityPrice"]
        M_WX["WeatherReading"]
        M_NEWS["NewsItem"]
        M_RULES["AlertRule"]
        M_EVENTS["AlertEvent"]
    end

    UI_HOME & UI_CALC --> R_FX & R_COMM & R_WX & R_NEWS & R_CALC
    UI_ALERTS --> R_ALERTS
    UI_BACKTEST --> R_BT
    UI_CONFIG --> R_ALERTS & R_DS & R_NEWS

    R_FX --> S_FX --> M_FX
    R_COMM --> S_COMM --> M_COMM
    R_WX --> S_WX --> M_WX
    R_NEWS --> S_NEWS & S_SENT --> M_NEWS
    R_ALERTS --> S_ALERT --> M_RULES & M_EVENTS
    R_CALC --> S_FX & S_COMM
    R_BT --> S_BT --> M_FX & M_COMM & M_WX & M_NEWS & M_RULES
    R_DS --> S_DS --> M_FX & M_COMM & M_WX & M_NEWS
```

---

## 3. Data Collection & Scheduler Flow

```mermaid
sequenceDiagram
    participant SCH as APScheduler
    participant COL as Collectors
    participant EXT as External APIs
    participant DB  as Database
    participant NLP as FinBERT
    participant AE  as Alert Engine

    Note over SCH: Server startup → 6 jobs registered

    loop Every 15 minutes
        SCH->>COL: _collect_fx()
        COL->>EXT: GET exchangerate-api.com/v6/{key}/pair/USD/LKR
        EXT-->>COL: { conversion_rate: 298.46 }
        COL->>DB: INSERT fx_rates

        SCH->>AE: _check_alerts()
        AE->>DB: SELECT alert_rules WHERE enabled=true
        AE->>DB: SELECT latest fx, commodity, weather, news
        AE->>DB: INSERT alert_events (if triggered)
        AE-->>SCH: triggered count
    end

    loop Every 1 hour
        SCH->>COL: _collect_commodities()
        COL->>EXT: GET finance.yahoo.com/v8/finance/chart/HG=F
        COL->>EXT: GET finance.yahoo.com/v8/finance/chart/ALI=F
        EXT-->>COL: { regularMarketPrice }
        COL->>DB: INSERT commodity_prices (×2)

        SCH->>COL: _collect_weather()
        COL->>EXT: GET api.open-meteo.com (×13 locations)
        EXT-->>COL: { daily.precipitation_sum, temperature_2m_max }
        COL->>DB: INSERT weather_readings (×13)

        SCH->>COL: _collect_news()
        COL->>EXT: GET newsapi.org/v2/everything (×5 queries)
        EXT-->>COL: { articles[] }
        COL->>DB: INSERT news_items
    end

    loop Every 2 hours
        SCH->>NLP: _score_sentiment()
        NLP->>DB: SELECT news_items WHERE sentiment IS NULL LIMIT 100
        DB-->>NLP: unscored headlines[]
        NLP->>NLP: FinBERT inference (batch)
        NLP->>DB: UPDATE news_items SET sentiment=label
    end
```

---

## 4. Alert Evaluation Flow

```mermaid
flowchart TD
    START([Scheduler trigger<br/>every 15 min]) --> LOAD_RULES

    LOAD_RULES["Load all enabled<br/>alert_rules from DB"] --> LOAD_DATA

    LOAD_DATA["Load current snapshots:<br/>• latest fx_rates<br/>• commodity_service.get_summary(COPPER)<br/>• commodity_service.get_summary(ALUMINIUM)<br/>• weather_service.get_high_risk()<br/>• sentiment_service.get_sentiment_summary(days=1)"]

    LOAD_DATA --> FOR_EACH

    FOR_EACH{"For each rule"} --> CHECK_METRIC

    CHECK_METRIC{"rule.metric?"} -->|"usd_lkr"| FX_CHECK
    CHECK_METRIC -->|"copper_price"| CU_CHECK
    CHECK_METRIC -->|"aluminium_price"| AL_CHECK
    CHECK_METRIC -->|"flood_risk"| WX_CHECK
    CHECK_METRIC -->|"news_sentiment"| SENT_CHECK

    FX_CHECK["Compare usd_lkr<br/>with threshold_value<br/>via (lt/gt/eq)"]
    CU_CHECK["Compare copper change_24h_pct<br/>with threshold_value"]
    AL_CHECK["Compare aluminium change_24h_pct<br/>with threshold_value"]
    WX_CHECK["Any location with<br/>flood_risk == threshold_text?"]
    SENT_CHECK["Parse TOPIC:pct<br/>Check negative fraction >= pct<br/>in last 24h news"]

    FX_CHECK & CU_CHECK & AL_CHECK & WX_CHECK & SENT_CHECK --> TRIGGERED{"Condition<br/>met?"}

    TRIGGERED -->|"No"| NEXT_RULE
    TRIGGERED -->|"Yes"| CREATE_EVENT

    CREATE_EVENT["INSERT alert_events<br/>(triggered_at, rule_id, message)"] --> NOTIFY

    NOTIFY{"SMTP<br/>configured?"} -->|"Yes"| SEND_EMAIL["Send email to<br/>email_recipients"]
    NOTIFY -->|"No"| NEXT_RULE

    SEND_EMAIL --> NEXT_RULE
    NEXT_RULE{"More rules?"} -->|"Yes"| FOR_EACH
    NEXT_RULE -->|"No"| END([Done])
```

---

## 5. Backtest Algorithm Flow

```mermaid
flowchart TD
    REQ["BacktestRequest<br/>{start_date, end_date, rule_ids}"] --> PREFETCH

    PREFETCH["Pre-fetch all data<br/>for date range + 7-day lookback:<br/>• all fx_rates<br/>• all commodity_prices (COPPER)<br/>• all commodity_prices (ALUMINIUM)<br/>• all weather_readings<br/>• all news_items"] --> ITER

    ITER["For each day in<br/>[start_date … end_date]"] --> SNAPSHOT

    SNAPSHOT["Build daily snapshot:<br/>• Latest FX ≤ day_end<br/>• Commodity today vs prev day → change_pct<br/>• Latest weather per location ≤ day_end<br/>• News sentiment counts for this day"]

    SNAPSHOT --> EVAL["Evaluate each rule<br/>against snapshot<br/>(same logic as live alert check)"]

    EVAL --> RECORD["Record:<br/>• fired rule names<br/>• fire count per rule<br/>• fire dates per rule"]

    RECORD --> MORE{"More days?"}
    MORE -->|"Yes"| ITER
    MORE -->|"No"| SUMMARISE

    SUMMARISE["Build BacktestResult:<br/>• rule_summaries (total_fires, fire_rate_pct, first/last date)<br/>• daily_results (date, alerts_fired, fx_rate, prices)<br/>• total_alerts_fired"] --> RETURN

    RETURN["Return to frontend<br/>for chart + table rendering"]
```

---

## 6. Database Entity-Relationship Diagram

```mermaid
erDiagram
    FX_RATES {
        INTEGER id PK
        DATETIME timestamp "indexed"
        FLOAT usd_lkr
        STRING source
    }

    COMMODITY_PRICES {
        INTEGER id PK
        DATETIME timestamp "indexed"
        STRING symbol "COPPER | ALUMINIUM, indexed"
        FLOAT price_usd
        STRING unit "per_tonne"
        STRING source
    }

    WEATHER_READINGS {
        INTEGER id PK
        DATETIME timestamp "indexed"
        STRING location_type "sri_lanka_district | supplier_port"
        STRING location_name "indexed"
        FLOAT rainfall_mm
        STRING flood_risk "LOW | MEDIUM | HIGH | CRITICAL"
        FLOAT temperature_c
        STRING source
    }

    NEWS_ITEMS {
        INTEGER id PK
        DATETIME published_at "indexed"
        DATETIME fetched_at
        STRING headline "max 500 chars"
        TEXT summary
        STRING url "max 500 chars"
        STRING source
        STRING topic "FX | COPPER | ALUMINIUM | TRADE | LOGISTICS, indexed"
        FLOAT relevance_score
        STRING sentiment "POSITIVE | NEGATIVE | NEUTRAL | NULL"
    }

    ALERT_RULES {
        INTEGER id PK
        DATETIME created_at
        STRING name "max 100 chars"
        STRING rule_type "FX_THRESHOLD | COMMODITY_DIP | WEATHER_RISK | SENTIMENT_NEGATIVE, indexed"
        STRING metric "usd_lkr | copper_price | aluminium_price | flood_risk | news_sentiment"
        STRING comparison "lt | gt | eq"
        FLOAT threshold_value "nullable"
        STRING threshold_text "nullable, e.g. HIGH or COPPER:0.60"
        BOOLEAN enabled
        TEXT email_recipients "comma-separated"
    }

    ALERT_EVENTS {
        INTEGER id PK
        DATETIME triggered_at
        INTEGER rule_id "indexed, FK to alert_rules"
        STRING rule_name "denormalised for audit log integrity"
        TEXT message
        BOOLEAN notified
    }

    ALERT_EVENTS }o--|| ALERT_RULES : "rule_id → id (soft FK)"
```

---

## 7. Frontend Component Tree

```mermaid
graph TD
    APP["App.tsx<br/>QueryClientProvider + BrowserRouter"]

    APP --> SHELL["AppShell<br/>AppSidebar + header + main"]

    SHELL --> HOME["HomePage"]
    SHELL --> CALC["CalculatorPage"]
    SHELL --> ALERTS["AlertsPage"]
    SHELL --> BT["BacktestPage"]
    SHELL --> CONFIG["ConfigPage"]

    HOME --> OV["Overview<br/>(stat cards)"]
    HOME --> FX["FXPanel<br/>(line chart)"]
    HOME --> COMM["CommodityPanel<br/>(line chart)"]
    HOME --> CH["CostHistory<br/>(area chart)"]
    HOME --> WM["WeatherMap<br/>(Leaflet map)"]
    HOME --> NF["NewsFeed<br/>(topic filter + sentiment badges)"]

    CALC --> CC["CostCalculator<br/>(shadcn form)"]
    CALC --> CH2["CostHistory<br/>(area chart)"]

    ALERTS --> AEL["Alert Event Log<br/>(table + search + severity colours)"]

    BT --> TAB_BT["Alert Backtesting tab<br/>(date range + bar chart + rule table)"]
    BT --> TAB_UAT["UAT Scenarios tab<br/>(5 scenario cards + run results)"]

    CONFIG --> TAB_RULES["Alert Rules tab<br/>(CRUD + toggle + Dialog)"]
    CONFIG --> TAB_APP["App Settings tab<br/>(read-only env vars)"]
    CONFIG --> TAB_MODEL["Model Tuning tab<br/>(FinBERT status + manual score)"]
    CONFIG --> TAB_DS["Data Sources tab<br/>(live audit cards)"]

    subgraph "Shared UI (shadcn/ui)"
        UI["Button · Badge · Card · Input · Label<br/>Switch · Select · Dialog · Tabs<br/>Separator · ScrollArea · Tooltip · Skeleton"]
    end
```

---

## 8. Deployment Architecture

```mermaid
graph TB
    subgraph INTERNET["Internet"]
        BROWSER["Procurement Team<br/>Browser (LAN/VPN)"]
        FX_EXT["exchangerate-api.com"]
        YF_EXT["Yahoo Finance"]
        OM_EXT["Open-Meteo"]
        NA_EXT["NewsAPI.org"]
        HF_EXT["HuggingFace<br/>(model download, first run only)"]
    end

    subgraph SERVER["VPS / AWS EC2 (Ubuntu 22.04)"]
        NGINX["Nginx<br/>Reverse Proxy + TLS<br/>:443 → :80 / :8000"]

        subgraph DOCKER["Docker Compose"]
            FE_C["frontend container<br/>Nginx + React build<br/>:80"]
            BE_C["backend container<br/>uvicorn + FastAPI<br/>:8000"]
            PG_C["postgres container<br/>PostgreSQL 15 + TimescaleDB<br/>:5432 (internal only)"]
        end

        ENV[".env<br/>(API keys, DB URL, SMTP)"]
    end

    BROWSER -->|"HTTPS :443"| NGINX
    NGINX -->|"/ → :80"| FE_C
    NGINX -->|"/api/ → :8000"| BE_C
    BE_C <-->|"SQLAlchemy"| PG_C
    BE_C --> ENV
    BE_C -->|"HTTPS"| FX_EXT & YF_EXT & OM_EXT & NA_EXT & HF_EXT
```

### Development Setup

```mermaid
graph LR
    subgraph DEV["Developer Machine"]
        FE_DEV["npm run dev<br/>Vite dev server :5173"]
        BE_DEV["uv run uvicorn --reload<br/>FastAPI :8000"]
        SQLITE[("SQLite file<br/>procurement_intel.db")]
        DEBUG_GEN["Debug generators<br/>(365 days synthetic data<br/>auto-seeded on first run)"]
    end

    BROWSER_DEV["Browser<br/>localhost:5173"] --> FE_DEV
    FE_DEV -->|"proxy /api"| BE_DEV
    BE_DEV <--> SQLITE
    DEBUG_GEN --> SQLITE
```

---

## 9. Technology Stack Summary

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Backend runtime | Python | 3.12 | Server-side language |
| Web framework | FastAPI | 0.136 | REST API, auto OpenAPI docs |
| Package manager | uv | 0.4+ | Python deps & virtualenv |
| ORM | SQLAlchemy | 2.x | Database abstraction |
| Database (dev) | SQLite | 3.x | Zero-setup local storage |
| Database (prod) | PostgreSQL + TimescaleDB | 15 | Time-series optimised |
| Scheduler | APScheduler | 3.11 | In-process background jobs |
| NLP model | FinBERT (ProsusAI) | — | Financial sentiment scoring |
| ML runtime | PyTorch (CPU) | 2.12 | FinBERT inference |
| HTTP client | httpx | 0.28 | Async-compatible collector requests |
| Frontend framework | React | 19 | Component-based UI |
| Language | TypeScript | 6 | Type-safe frontend |
| Build tool | Vite | 8 | Dev server + production bundler |
| Styling | Tailwind CSS | v3 | Utility-first CSS |
| Component library | shadcn/ui (hand-written) | — | Accessible UI primitives |
| Charts | Recharts | 3 | Line, area, bar charts |
| Maps | react-leaflet | — | Weather map (Leaflet.js) |
| Data fetching | @tanstack/react-query | v5 | Server state, caching |
| Routing | react-router-dom | v7 | Client-side navigation |
| Container | Docker + Docker Compose | 24+ | Dev & prod packaging |
| Reverse proxy | Nginx | 1.24+ | TLS termination, routing |

---

*Architecture document v1.0 — ACL Cables Procurement Intelligence Dashboard*
