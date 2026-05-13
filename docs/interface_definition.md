# ACL Cables Procurement Intelligence Dashboard — Interface Definition Document

> **Version:** 1.0 | **Date:** 2026-05-13
> This document defines every interface boundary in the system: Frontend ↔ Backend REST API, Backend ↔ External data sources, Backend ↔ Database, and Backend ↔ FinBERT NLP model.

---

## Table of Contents

1. [Frontend ↔ Backend REST API](#1-frontend--backend-rest-api)
2. [Backend ↔ External Data Sources](#2-backend--external-data-sources)
3. [Backend ↔ Database (ORM)](#3-backend--database-orm)
4. [Backend ↔ FinBERT NLP Model](#4-backend--finbert-nlp-model)

---

## 1. Frontend ↔ Backend REST API

**Base URL:** `http://localhost:8000` (dev) / `https://<domain>` (prod)  
**Protocol:** HTTP/1.1, JSON request and response bodies  
**Auth:** None (internal network deployment assumed)  
**CORS:** Configured for `FRONTEND_URL` env var (default `http://localhost:5173`)  
**Docs:** Interactive Swagger UI at `GET /docs`; OpenAPI schema at `GET /openapi.json`

All timestamps are UTC ISO-8601. All monetary values in their stated currency. HTTP errors follow `{ "detail": "message" }`.

---

### 1.1 FX Rates — `/api/v1/fx`

#### `GET /api/v1/fx/latest`

Returns the most recent USD/LKR rate in the database.

**Response `200 OK`**
```json
{
  "id": 1421,
  "timestamp": "2026-05-13T08:45:00",
  "usd_lkr": 298.46,
  "source": "exchangerate-api"
}
```

**Response `404 Not Found`**
```json
{ "detail": "No FX data available" }
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-increment primary key |
| `timestamp` | datetime (UTC) | When the rate was recorded |
| `usd_lkr` | float | Units of LKR per 1 USD |
| `source` | string | Data origin (`exchangerate-api` or `debug`) |

---

#### `GET /api/v1/fx/history`

Returns historical FX rates for the past N days.

**Query Parameters**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `days` | integer | `30` | 1–365 | Lookback window |

**Response `200 OK`** — array of `FXRateOut` (same schema as `/latest`), ascending by `timestamp`.

---

#### `GET /api/v1/fx/summary`

Returns aggregated statistics for the most recent 30-day window.

**Response `200 OK`**
```json
{
  "current": 298.46,
  "change_24h": -1.23,
  "change_24h_pct": -0.41,
  "high_30d": 312.10,
  "low_30d": 285.50,
  "avg_30d": 299.87
}
```

| Field | Type | Description |
|-------|------|-------------|
| `current` | float | Latest USD/LKR rate |
| `change_24h` | float | Absolute change in last 24 h |
| `change_24h_pct` | float | Percentage change in last 24 h |
| `high_30d` | float | 30-day high |
| `low_30d` | float | 30-day low |
| `avg_30d` | float | 30-day average |

---

### 1.2 Commodity Prices — `/api/v1/commodities`

`{symbol}` is `COPPER` or `ALUMINIUM` (case-insensitive).

#### `GET /api/v1/commodities/{symbol}/latest`

**Response `200 OK`**
```json
{
  "id": 890,
  "timestamp": "2026-05-13T08:00:00",
  "symbol": "COPPER",
  "price_usd": 9273.94,
  "unit": "per_tonne",
  "source": "yahoo-finance"
}
```

**Response `404 Not Found`** if no data available for symbol.

---

#### `GET /api/v1/commodities/{symbol}/history`

**Query Parameters**

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `days` | integer | `30` | 1–365 |

**Response `200 OK`** — array of commodity price objects, ascending by `timestamp`.

---

#### `GET /api/v1/commodities/{symbol}/summary`

**Response `200 OK`**
```json
{
  "symbol": "COPPER",
  "current_price_usd": 9273.94,
  "change_24h": 48.20,
  "change_24h_pct": 0.52,
  "high_30d": 9680.00,
  "low_30d": 8900.00,
  "avg_30d": 9310.45
}
```

---

### 1.3 Weather — `/api/v1/weather`

#### `GET /api/v1/weather/latest`

Returns the most recent reading for every tracked location.

**Response `200 OK`** — array of:
```json
{
  "location_name": "Western",
  "location_type": "sri_lanka_district",
  "timestamp": "2026-05-13T07:00:00",
  "rainfall_mm": 42.3,
  "flood_risk": "HIGH",
  "temperature_c": 28.5
}
```

| `location_type` values | Meaning |
|------------------------|---------|
| `sri_lanka_district` | One of 9 Sri Lanka provinces |
| `supplier_port` | Dubai, Shanghai, Ho Chi Minh, Singapore |

| `flood_risk` values | Rainfall threshold |
|---------------------|--------------------|
| `LOW` | < 10 mm/day |
| `MEDIUM` | 10–29 mm/day |
| `HIGH` | 30–59 mm/day |
| `CRITICAL` | ≥ 60 mm/day |

---

#### `GET /api/v1/weather/high-risk`

Same schema as `/latest` but filtered to locations where `flood_risk` is `MEDIUM`, `HIGH`, or `CRITICAL`.

---

#### `GET /api/v1/weather/history`

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `location` | string | Yes | Exact `location_name` value |
| `days` | integer | No (default 30) | Lookback window, 1–365 |

**Response `200 OK`** — array of full `WeatherReadingOut`:
```json
{
  "id": 5621,
  "timestamp": "2026-05-12T07:00:00",
  "location_type": "sri_lanka_district",
  "location_name": "Western",
  "rainfall_mm": 35.1,
  "flood_risk": "HIGH",
  "temperature_c": 29.0,
  "source": "open-meteo"
}
```

---

### 1.4 News — `/api/v1/news`

#### `GET /api/v1/news/`

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | `7` | Lookback window |
| `topic` | string | `null` | Filter: `FX`, `COPPER`, `ALUMINIUM`, `TRADE`, `LOGISTICS` |
| `limit` | integer | `50` | Max articles returned |

**Response `200 OK`** — array of:
```json
{
  "id": 3201,
  "published_at": "2026-05-13T06:30:00",
  "fetched_at": "2026-05-13T07:00:00",
  "headline": "LME Copper Falls on China Demand Concerns",
  "summary": "London Metal Exchange copper futures declined 1.2%...",
  "url": "https://example.com/article",
  "source": "Reuters",
  "topic": "COPPER",
  "relevance_score": 0.8,
  "sentiment": "NEGATIVE"
}
```

| `sentiment` values | Description |
|-------------------|-------------|
| `POSITIVE` | Favourable market development |
| `NEGATIVE` | Adverse development |
| `NEUTRAL` | Factual / ambiguous |
| `null` | Not yet scored by FinBERT |

---

#### `GET /api/v1/news/sentiment-summary`

Aggregated sentiment counts per topic.

**Query Parameters**

| Parameter | Type | Default |
|-----------|------|---------|
| `days` | integer | `7` |

**Response `200 OK`** — array of:
```json
{
  "topic": "COPPER",
  "positive": 14,
  "negative": 22,
  "neutral": 8,
  "unscored": 3,
  "period_days": 7
}
```

---

#### `POST /api/v1/news/score-now`

Manually triggers FinBERT scoring of unscored news items (up to 100 in one batch).

**Request body:** none  
**Response `200 OK`**
```json
{ "scored": 47 }
```

---

### 1.5 Alerts — `/api/v1/alerts`

#### `GET /api/v1/alerts/rules`

**Response `200 OK`** — array of `AlertRuleOut`:
```json
{
  "id": 3,
  "created_at": "2026-05-13T00:00:00",
  "name": "FX favourable — USD/LKR below 290",
  "rule_type": "FX_THRESHOLD",
  "metric": "usd_lkr",
  "comparison": "lt",
  "threshold_value": 290.0,
  "threshold_text": null,
  "enabled": true,
  "email_recipients": "procurement@acl.lk"
}
```

| `rule_type` | `metric` | Threshold field used |
|-------------|----------|---------------------|
| `FX_THRESHOLD` | `usd_lkr` | `threshold_value` (float) |
| `COMMODITY_DIP` | `copper_price` or `aluminium_price` | `threshold_value` (% change) |
| `WEATHER_RISK` | `flood_risk` | `threshold_text` (`HIGH` or `CRITICAL`) |
| `SENTIMENT_NEGATIVE` | `news_sentiment` | `threshold_text` (`TOPIC:fraction`, e.g. `COPPER:0.60`) |

| `comparison` | Meaning |
|-------------|---------|
| `lt` | Metric is less than threshold |
| `gt` | Metric is greater than threshold |
| `eq` | Metric equals threshold |

---

#### `POST /api/v1/alerts/rules`

Creates a new alert rule.

**Request body:**
```json
{
  "name": "Copper dip >3% in 24h",
  "rule_type": "COMMODITY_DIP",
  "metric": "copper_price",
  "comparison": "lt",
  "threshold_value": -3.0,
  "threshold_text": null,
  "enabled": true,
  "email_recipients": "procurement@acl.lk,manager@acl.lk"
}
```

All fields except `threshold_value` and `threshold_text` are required. Exactly one of the two threshold fields should be populated based on `metric`.

**Response `200 OK`** — created `AlertRuleOut` with `id` and `created_at`.

---

#### `PUT /api/v1/alerts/rules/{id}`

Full replacement update of an existing rule. Same request body as POST.

**Response `200 OK`** — updated `AlertRuleOut`.  
**Response `404 Not Found`** if rule ID does not exist.

---

#### `DELETE /api/v1/alerts/rules/{id}`

**Response `204 No Content`** on success.  
**Response `404 Not Found`** if rule ID does not exist.

---

#### `GET /api/v1/alerts/events`

Returns triggered alert events in reverse-chronological order.

**Query Parameters**

| Parameter | Type | Default |
|-----------|------|---------|
| `limit` | integer | `50` |

**Response `200 OK`** — array of:
```json
{
  "id": 812,
  "triggered_at": "2026-05-13T09:15:00",
  "rule_id": 3,
  "rule_name": "FX favourable — USD/LKR below 290",
  "message": "USD/LKR is 287.42 — lt threshold 290.0",
  "notified": false
}
```

---

#### `POST /api/v1/alerts/check`

Manually triggers alert evaluation against current data.

**Request body:** none  
**Response `200 OK`** — array of `AlertEventOut` for any rules that fired during this check.

---

### 1.6 Calculator — `/api/v1/calculator`

#### `POST /api/v1/calculator/landed-cost`

Calculates the LKR landed cost of an import order.

**Request body:**
```json
{
  "material": "COPPER",
  "quantity_tonnes": 50.0,
  "custom_lme_price_usd": null,
  "custom_fx_rate": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `material` | string | Yes | `COPPER` or `ALUMINIUM` |
| `quantity_tonnes` | float | Yes | Order size in metric tonnes |
| `custom_lme_price_usd` | float \| null | No | Override LME price; uses DB latest if null |
| `custom_fx_rate` | float \| null | No | Override FX rate; uses DB latest if null |

**Formula:** `total_lkr = quantity_tonnes × lme_price_usd × usd_lkr`

**Response `200 OK`:**
```json
{
  "material": "COPPER",
  "quantity_tonnes": 50.0,
  "lme_price_usd_per_tonne": 9273.94,
  "usd_lkr_rate": 298.46,
  "total_usd": 463697.0,
  "total_lkr": 138369000.62,
  "calculated_at": "2026-05-13T09:30:00"
}
```

**Response `400 Bad Request`** if material is not `COPPER` or `ALUMINIUM`.  
**Response `404 Not Found`** if no commodity or FX data available and no custom values were provided.

---

#### `GET /api/v1/calculator/history`

Returns daily landed cost for a hypothetical recurring order over a historical period.

**Query Parameters**

| Parameter | Type | Required | Default | Constraints |
|-----------|------|----------|---------|-------------|
| `material` | string | Yes | — | `COPPER` or `ALUMINIUM` |
| `quantity_tonnes` | float | No | `50.0` | > 0 |
| `days` | integer | No | `90` | 1–365 |

**Join logic:** For each commodity price row, the closest FX rate on the same calendar date is used. If no FX rate exists for that date, looks back up to 7 days.

**Response `200 OK`** — array of:
```json
{
  "date": "2026-03-01",
  "lme_price_usd": 9180.50,
  "usd_lkr": 301.20,
  "landed_cost_lkr": 138116820.0
}
```

---

### 1.7 Backtesting — `/api/v1/backtest`

#### `POST /api/v1/backtest/run`

Simulates alert rule evaluation against historical database data.

**Request body:**
```json
{
  "rule_ids": null,
  "start_date": "2026-02-01",
  "end_date": "2026-05-13"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rule_ids` | integer[] \| null | Specific rule IDs to test. `null` = all rules |
| `start_date` | date (YYYY-MM-DD) | Start of backtest period |
| `end_date` | date (YYYY-MM-DD) | End of backtest period (inclusive) |

**Constraints:** `start_date` ≤ `end_date`; range ≤ 730 days.

**Response `200 OK`:**
```json
{
  "start_date": "2026-02-01",
  "end_date": "2026-05-13",
  "total_days": 101,
  "total_alerts_fired": 47,
  "rule_summaries": [
    {
      "rule_id": 4,
      "rule_name": "Flood risk — Western Province HIGH or above",
      "rule_type": "WEATHER_RISK",
      "total_fires": 23,
      "fire_rate_pct": 22.8,
      "first_fire_date": "2026-02-08",
      "last_fire_date": "2026-05-11"
    }
  ],
  "daily_results": [
    {
      "date": "2026-02-01",
      "triggered_rules": [],
      "alerts_fired": 0,
      "fx_rate": 305.20,
      "copper_price": 9100.40,
      "aluminium_price": 2340.80
    }
  ]
}
```

**Response `400 Bad Request`** if dates are invalid or range exceeds 2 years.

---

#### `GET /api/v1/backtest/scenarios`

Returns the 5 pre-built UAT procurement scenarios.

**Response `200 OK`** — array of:
```json
{
  "id": "copper_market_dip",
  "name": "Copper Market Dip",
  "description": "LME Copper drops 5.4% in 24h with negative market sentiment...",
  "conditions": {
    "usd_lkr": 308.5,
    "copper_change_pct": -5.4,
    "aluminium_change_pct": -1.2,
    "high_risk_locations": [],
    "sentiment_by_topic": {
      "COPPER": { "positive": 10, "negative": 72, "neutral": 18 }
    }
  }
}
```

**Available scenario IDs:**

| ID | Name |
|----|------|
| `fx_buying_window` | FX Buying Window (USD/LKR = 283) |
| `copper_market_dip` | Copper Market Dip (−5.4% 24h) |
| `monsoon_disruption` | Monsoon Supply Chain Disruption |
| `geopolitical_alert` | Geopolitical Supply Risk |
| `combined_risk_event` | Combined Risk Event |

---

#### `POST /api/v1/backtest/scenario/run`

Evaluates all enabled alert rules against a supplied set of market conditions (does not write to the database).

**Request body:**
```json
{
  "conditions": {
    "usd_lkr": 283.0,
    "copper_change_pct": -0.3,
    "aluminium_change_pct": 0.1,
    "high_risk_locations": [],
    "sentiment_by_topic": {
      "FX": { "positive": 60, "negative": 15, "neutral": 25 }
    }
  }
}
```

**Response `200 OK`:**
```json
{
  "total_fired": 1,
  "fired_rules": [
    {
      "rule_id": 1,
      "rule_name": "FX favourable — USD/LKR below 290",
      "rule_type": "FX_THRESHOLD",
      "message": "USD/LKR is 283.00 — lt threshold 290.0"
    }
  ],
  "conditions": { ... }
}
```

---

### 1.8 Data Source Audit — `/api/v1/datasources`

#### `GET /api/v1/datasources/audit`

Returns reliability status of all external data sources, derived from database freshness (no live API calls are made during the audit).

**Response `200 OK`:**
```json
{
  "audit_timestamp": "2026-05-13T09:45:00",
  "overall_health": "ok",
  "sources": [
    {
      "source_name": "FX Rate — exchangerate-api.com",
      "status": "ok",
      "data_points_24h": 96,
      "last_data_timestamp": "2026-05-13T09:30:00",
      "fragility_rating": "MEDIUM",
      "fragility_reason": "Freemium tier: 1,500 req/month...",
      "paid_fallback": "Open Exchange Rates (paid) or CBSL API",
      "notes": "Requires FX_API_KEY env var..."
    }
  ]
}
```

| `status` | Condition |
|----------|-----------|
| `ok` | Last reading within 3 hours |
| `degraded` | Last reading > 3 hours ago |
| `down` | No readings in database |

| `fragility_rating` | Meaning |
|-------------------|---------|
| `LOW` | Official API, free, no key, high uptime (Open-Meteo) |
| `MEDIUM` | Freemium with rate limits or 24h delay (exchangerate-api, NewsAPI) |
| `HIGH` | Unofficial endpoint, no SLA, may break without notice (Yahoo Finance) |

| `overall_health` | Meaning |
|-----------------|---------|
| `ok` | All sources reporting `ok` |
| `degraded` | One or more sources degraded or down |

---

### 1.9 Health Check

#### `GET /health`

**Response `200 OK`:**
```json
{ "status": "ok", "debug": true }
```

---

## 2. Backend ↔ External Data Sources

### 2.1 exchangerate-api.com (FX Rate)

**Module:** `backend/app/collectors/fx_collector.py`  
**Triggered by:** Scheduler every 15 minutes  
**Requires:** `FX_API_KEY` environment variable

#### Request

```
GET https://v6.exchangerate-api.com/v6/{FX_API_KEY}/pair/USD/LKR
```

No query parameters. No request body.

**Headers:** None (API key is in the URL path)

#### Response (success)

```json
{
  "result": "success",
  "documentation": "https://www.exchangerate-api.com/docs",
  "terms_of_use": "https://www.exchangerate-api.com/terms",
  "time_last_update_unix": 1747123200,
  "time_last_update_utc": "Tue, 13 May 2026 00:00:01 +0000",
  "time_next_update_unix": 1747209600,
  "time_next_update_utc": "Wed, 14 May 2026 00:00:01 +0000",
  "base_code": "USD",
  "target_code": "LKR",
  "conversion_rate": 298.46
}
```

**Fields used:** `result` (must equal `"success"`), `conversion_rate` (stored as `usd_lkr`)

#### Response (error)

```json
{ "result": "error", "error-type": "invalid-key" }
```

**Common error types:** `invalid-key`, `inactive-account`, `quota-reached`

#### Error handling

- Non-`"success"` result → logs warning, returns `None`, no DB write
- HTTP error or network timeout → logs warning, returns `None`
- `FX_API_KEY` not set → returns `None` immediately (no HTTP call)

#### Rate limits

| Plan | Requests/month | Update frequency |
|------|----------------|-----------------|
| Free | 1,500 | Daily |
| Pro | 30,000+ | Hourly |

At 15-minute polling: ~2,880 req/month — **exceeds free tier**. Recommend Pro plan or switching to CBSL API.

---

### 2.2 Yahoo Finance v8 (Commodity Prices)

**Module:** `backend/app/collectors/commodity_collector.py`  
**Triggered by:** Scheduler every 1 hour  
**Requires:** Nothing (no API key; unofficial endpoint)

#### Request

```
GET https://query1.finance.yahoo.com/v8/finance/chart/{ticker}
    ?interval=1d&range=1d
```

| Ticker | Commodity | Unit returned | Unit stored |
|--------|-----------|---------------|-------------|
| `HG=F` | LME Copper futures | USD/lb | USD/tonne (×2204.62) |
| `ALI=F` | LME Aluminium futures | USD/tonne | USD/tonne |

**Headers:** `User-Agent: Mozilla/5.0` (required — Yahoo blocks default Python agent)

#### Response (abbreviated)

```json
{
  "chart": {
    "result": [
      {
        "meta": {
          "regularMarketPrice": 4.207,
          "currency": "USD",
          "symbol": "HG=F"
        }
      }
    ],
    "error": null
  }
}
```

**Fields used:** `chart.result[0].meta.regularMarketPrice`

**Copper conversion:**
```
price_usd_per_tonne = regularMarketPrice × 2204.62
```

#### Error handling

- Any exception (network, JSON parse, missing key) → logs warning, returns `None`
- No automatic retry; next scheduler run will attempt again

#### Fragility note

This is an **unofficial** endpoint. Yahoo Finance has changed or removed it without notice in the past. If prices stop updating, check this endpoint first.

---

### 2.3 Open-Meteo (Weather)

**Module:** `backend/app/collectors/weather_collector.py`  
**Triggered by:** Scheduler every 1 hour  
**Requires:** Nothing (free, no API key)  
**Runs in:** All modes (including `DEBUG=true`)

#### Request

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}&longitude={lon}
    &daily=precipitation_sum,temperature_2m_max
    &timezone=auto
    &forecast_days=1
```

**Called 13 times per scheduler run** (9 Sri Lanka districts + 4 supplier ports):

| Location | Coordinates |
|----------|-------------|
| Western (Sri Lanka) | 6.9271, 79.8612 |
| Southern | 6.0535, 80.2210 |
| Northern | 9.6615, 80.0255 |
| Eastern | 8.5874, 81.2152 |
| North Western | 7.9403, 80.3500 |
| North Central | 8.3347, 80.4000 |
| Uva | 6.9934, 81.0550 |
| Sabaragamuwa | 6.6828, 80.3992 |
| Central | 7.2906, 80.6337 |
| Dubai Port (UAE) | 25.0657, 55.1713 |
| Shanghai Port (China) | 31.3725, 121.5168 |
| Ho Chi Minh Port (Vietnam) | 10.7769, 106.7009 |
| Singapore Port | 1.2868, 103.8545 |

#### Response

```json
{
  "latitude": 6.9271,
  "longitude": 79.8612,
  "timezone": "Asia/Colombo",
  "daily": {
    "time": ["2026-05-13"],
    "precipitation_sum": [42.3],
    "temperature_2m_max": [28.5]
  }
}
```

**Fields used:** `daily.precipitation_sum[0]`, `daily.temperature_2m_max[0]`

#### Flood risk classification

| Rainfall (mm/day) | `flood_risk` stored |
|-------------------|-------------------|
| < 10 | `LOW` |
| 10–29 | `MEDIUM` |
| 30–59 | `HIGH` |
| ≥ 60 | `CRITICAL` |
| `null` | `LOW` |

#### Error handling

- Per-location failure → logs warning, that location skipped, others continue
- All locations attempted independently

---

### 2.4 NewsAPI.org (News Headlines)

**Module:** `backend/app/collectors/news_collector.py`  
**Triggered by:** Scheduler every 1 hour  
**Requires:** `NEWSAPI_KEY` environment variable

#### Request

```
GET https://newsapi.org/v2/everything
    ?q={query}
    &from={since}
    &sortBy=publishedAt
    &language=en
    &pageSize=10
    &apiKey={NEWSAPI_KEY}
```

**Called 5 times per scheduler run**, one per topic:

| `topic` stored | Query string sent |
|----------------|-------------------|
| `FX` | `USD LKR OR rupee dollar Sri Lanka` |
| `COPPER` | `LME copper price` |
| `ALUMINIUM` | `LME aluminium price` |
| `TRADE` | `UAE Vietnam China supply chain shipping` |
| `LOGISTICS` | `Sri Lanka port logistics flood` |

`since` = UTC timestamp 6 hours before collection time.

#### Response

```json
{
  "status": "ok",
  "totalResults": 8,
  "articles": [
    {
      "source": { "id": "reuters", "name": "Reuters" },
      "title": "LME Copper Falls on China Demand Concerns",
      "description": "London Metal Exchange copper futures declined 1.2%...",
      "url": "https://www.reuters.com/...",
      "publishedAt": "2026-05-13T06:30:00Z"
    }
  ]
}
```

**Fields mapped to `news_items` table:**

| API field | DB column |
|-----------|-----------|
| `articles[].publishedAt` | `published_at` (parsed, UTC, timezone stripped) |
| `articles[].title` | `headline` (truncated to 500 chars) |
| `articles[].description` | `summary` (truncated to 1000 chars) |
| `articles[].url` | `url` |
| `articles[].source.name` | `source` |
| query topic | `topic` |
| hardcoded `0.8` | `relevance_score` |
| `null` | `sentiment` (filled later by FinBERT) |

#### Error handling

- Per-topic failure → logs warning, other topics continue
- `NEWSAPI_KEY` not set → returns empty list immediately

#### Rate limits (free developer plan)

| Limit | Value |
|-------|-------|
| Requests/day | 100 |
| Article delay | 24 hours (free tier) |
| Max results per request | 100 |

At 5 topics × 24 hourly runs = 120 req/day — **exceeds free tier**. Reduce to every 3 hours for dev, or upgrade plan for production real-time use.

---

## 3. Backend ↔ Database (ORM)

**ORM:** SQLAlchemy 2.x declarative models  
**Dev:** SQLite (`procurement_intel.db` in project root)  
**Prod:** PostgreSQL 15 + TimescaleDB (swap via `DATABASE_URL` env var)  
**Session management:** `get_db()` dependency injection per request; scheduler jobs use `SessionLocal()` with manual close in `finally`

### 3.1 Table: `fx_rates`

```sql
CREATE TABLE fx_rates (
    id        INTEGER     PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME    NOT NULL DEFAULT (datetime('now')),
    usd_lkr   REAL        NOT NULL,
    source    VARCHAR(50)
);
CREATE INDEX ix_fx_rates_id        ON fx_rates (id);
CREATE INDEX ix_fx_rates_timestamp ON fx_rates (timestamp);
```

**Write path:** Scheduler `_collect_fx()` → `db.add(FXRate(...))` → `db.commit()`  
**Read path:** `fx_service.get_latest()`, `get_history()`, `get_summary()`; also joined in `calculator.cost_history`

---

### 3.2 Table: `commodity_prices`

```sql
CREATE TABLE commodity_prices (
    id        INTEGER     PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME    NOT NULL DEFAULT (datetime('now')),
    symbol    VARCHAR(20) NOT NULL,   -- COPPER | ALUMINIUM
    price_usd REAL        NOT NULL,
    unit      VARCHAR(20) DEFAULT 'per_tonne',
    source    VARCHAR(50)
);
CREATE INDEX ix_commodity_prices_id        ON commodity_prices (id);
CREATE INDEX ix_commodity_prices_timestamp ON commodity_prices (timestamp);
CREATE INDEX ix_commodity_prices_symbol    ON commodity_prices (symbol);
```

**Write path:** Scheduler `_collect_commodities()` → `db.add(CommodityPrice(...))` × 2  
**Read path:** `commodity_service.*`; backtest pre-fetch; calculator history

---

### 3.3 Table: `weather_readings`

```sql
CREATE TABLE weather_readings (
    id            INTEGER      PRIMARY KEY AUTOINCREMENT,
    timestamp     DATETIME     NOT NULL DEFAULT (datetime('now')),
    location_type VARCHAR(30),          -- sri_lanka_district | supplier_port
    location_name VARCHAR(100),
    rainfall_mm   REAL,
    flood_risk    VARCHAR(20),          -- LOW | MEDIUM | HIGH | CRITICAL
    temperature_c REAL,
    source        VARCHAR(50)
);
CREATE INDEX ix_weather_readings_id            ON weather_readings (id);
CREATE INDEX ix_weather_readings_timestamp     ON weather_readings (timestamp);
CREATE INDEX ix_weather_readings_location_name ON weather_readings (location_name);
```

**Write path:** Scheduler `_collect_weather()` → `db.bulk_insert_mappings(WeatherReading, readings)`  
**Read path:** `weather_service.get_latest_all()` uses a subquery grouping by `location_name` to get latest per location; `get_high_risk()` filters on `flood_risk`

---

### 3.4 Table: `news_items`

```sql
CREATE TABLE news_items (
    id              INTEGER      PRIMARY KEY AUTOINCREMENT,
    published_at    DATETIME,
    fetched_at      DATETIME     DEFAULT (datetime('now')),
    headline        VARCHAR(500) NOT NULL,
    summary         TEXT,
    url             VARCHAR(500),
    source          VARCHAR(100),
    topic           VARCHAR(50),          -- FX | COPPER | ALUMINIUM | TRADE | LOGISTICS
    relevance_score REAL         DEFAULT 0.5,
    sentiment       VARCHAR(20)           -- POSITIVE | NEGATIVE | NEUTRAL | NULL
);
CREATE INDEX ix_news_items_id           ON news_items (id);
CREATE INDEX ix_news_items_published_at ON news_items (published_at);
CREATE INDEX ix_news_items_topic        ON news_items (topic);
```

**Write path (collect):** Scheduler `_collect_news()` → `db.bulk_insert_mappings(NewsItem, articles)` — `sentiment` is `NULL`  
**Write path (score):** Scheduler `_score_sentiment()` → `sentiment_service.score_unscored_news()` → `row.sentiment = label` → `db.commit()`  
**Read path:** `news_service.get_recent()`; `sentiment_service.get_sentiment_summary()` uses `GROUP BY topic, sentiment`

---

### 3.5 Table: `alert_rules`

```sql
CREATE TABLE alert_rules (
    id               INTEGER      PRIMARY KEY AUTOINCREMENT,
    created_at       DATETIME     DEFAULT (datetime('now')),
    name             VARCHAR(100) NOT NULL,
    rule_type        VARCHAR(50),
    metric           VARCHAR(50),
    comparison       VARCHAR(10),         -- lt | gt | eq
    threshold_value  REAL,               -- nullable; used for numeric thresholds
    threshold_text   VARCHAR(50),        -- nullable; used for text thresholds
    enabled          BOOLEAN      DEFAULT 1,
    email_recipients TEXT                -- comma-separated email addresses
);
CREATE INDEX ix_alert_rules_id        ON alert_rules (id);
CREATE INDEX ix_alert_rules_rule_type ON alert_rules (rule_type);
```

**Write path:** CRUD via `alert_service.create_rule()`, `update_rule()`, `delete_rule()`; pre-seeded with 5 default rules by `debug/seed.py`  
**Read path:** `alert_service.check_alerts()` loads all `enabled=True` rules every 15 min; backtesting loads rules per `rule_ids` filter

---

### 3.6 Table: `alert_events`

```sql
CREATE TABLE alert_events (
    id           INTEGER      PRIMARY KEY AUTOINCREMENT,
    triggered_at DATETIME     DEFAULT (datetime('now')),
    rule_id      INTEGER,                -- soft FK to alert_rules.id
    rule_name    VARCHAR(100),           -- denormalised for audit log integrity
    message      TEXT,
    notified     BOOLEAN      DEFAULT 0
);
CREATE INDEX ix_alert_events_id      ON alert_events (id);
CREATE INDEX ix_alert_events_rule_id ON alert_events (rule_id);
```

**Write path:** `alert_service.check_alerts()` → `db.add(AlertEvent(...))` for each triggered rule  
**Read path:** `alert_service.list_events(limit)` ordered by `triggered_at DESC`

**Note on soft FK:** `rule_id` references `alert_rules.id` but there is no SQL-level foreign key constraint. `rule_name` is stored alongside to preserve the audit record even if the rule is deleted.

---

### 3.7 Session & Transaction Pattern

```python
# Request-scoped (via FastAPI dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Scheduler-scoped (manual session lifecycle)
db = SessionLocal()
try:
    # ... operations ...
    db.commit()
except Exception:
    db.rollback()
    raise
finally:
    db.close()
```

---

## 4. Backend ↔ FinBERT NLP Model

**Module:** `backend/app/services/sentiment_service.py`  
**Model:** `ProsusAI/finbert` (HuggingFace Hub)  
**Runtime:** PyTorch 2.12 CPU-only (`device=-1`)  
**Loading:** Lazy — loaded on first call, cached as module-level `_pipeline`  
**Toggle:** `SENTIMENT_ENABLED=false` in `.env` skips all loading and scoring

### 4.1 Model Initialisation

```python
from transformers import pipeline as hf_pipeline

_pipeline = hf_pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert",
    device=-1,           # -1 = CPU; 0+ = GPU index
    truncation=True,
    max_length=512,
)
```

**First-run behaviour:**
1. `transformers` downloads model weights to `~/.cache/huggingface/` (~400 MB)
2. Subsequent runs load from local cache; no download
3. Load time: ~5–15 seconds on first call; ~1–3 seconds from cache

### 4.2 Single-text Scoring

**Function:** `score_text(text: str) → tuple[str, float] | tuple[None, None]`

```python
result = _pipeline(text[:512])[0]
# result = { "label": "negative", "score": 0.927 }
label  = result["label"].upper()   # POSITIVE | NEGATIVE | NEUTRAL
conf   = round(result["score"], 3)
```

**Input:** Raw text string (headline). Truncated to 512 characters before passing to the pipeline (the tokeniser also enforces `max_length=512` tokens).

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | `POSITIVE`, `NEGATIVE`, or `NEUTRAL` |
| `score` | float | Confidence score 0.0–1.0 |

Returns `(None, None)` if pipeline is not loaded or inference fails.

### 4.3 Batch Scoring (Scheduler)

**Function:** `score_unscored_news(db, batch_size=50) → int`

```python
# 1. Fetch unscored rows
rows = db.query(NewsItem).filter(NewsItem.sentiment.is_(None)).limit(batch_size).all()
texts = [r.headline for r in rows]

# 2. Batch inference
results = _pipeline(texts, truncation=True, max_length=512)
# results = [{"label": "negative", "score": 0.91}, ...]

# 3. Write back
for row, result in zip(rows, results):
    row.sentiment = result["label"].upper()
db.commit()
```

**Batch size:** Default 100 (scheduler), configurable via API for manual scoring.  
**Performance:** Approximately 1–3 seconds per 10 headlines on modern CPU.

### 4.4 Sentiment Summary Query (No Model Call)

**Function:** `get_sentiment_summary(db, days=7) → list[dict]`

This function reads pre-computed `sentiment` values from the database — it does **not** call the FinBERT model.

```python
rows = db.query(
    NewsItem.topic,
    NewsItem.sentiment,
    func.count(NewsItem.id).label("cnt"),
).filter(
    NewsItem.published_at >= since,
    NewsItem.topic.isnot(None),
).group_by(NewsItem.topic, NewsItem.sentiment).all()
```

**Output per topic:**
```json
{
  "topic": "COPPER",
  "positive": 14,
  "negative": 22,
  "neutral": 8,
  "unscored": 3,
  "period_days": 7
}
```

### 4.5 FinBERT Model Specification

| Property | Value |
|----------|-------|
| Model ID | `ProsusAI/finbert` |
| Architecture | BERT-base (12 layers, 768 hidden, 12 heads) |
| Parameters | ~110 million |
| Training data | Financial news, earnings calls, analyst reports |
| Labels | `positive`, `negative`, `neutral` |
| Max token length | 512 |
| Input format | Plain text (headline or short paragraph) |
| Output format | `[{"label": str, "score": float}]` |
| Inference device | CPU (no GPU required) |
| Approximate disk size | ~400 MB (weights + tokeniser) |
| HuggingFace pipeline task | `sentiment-analysis` |

### 4.6 Limitations

| Limitation | Implication |
|-----------|------------|
| Trained on general financial text, not Sri Lankan procurement news | May misclassify region-specific headlines |
| Short headlines may be ambiguous | Lower confidence scores on short text |
| No fine-tuning on ACL-specific corpus | Treat output as directional signal only |
| CPU inference is slow at scale | Batch processing; not real-time per article |
| `score` reflects model confidence, not external accuracy | High-confidence wrong predictions are possible |

---

*Interface Definition Document v1.0 — ACL Cables Procurement Intelligence Dashboard*
