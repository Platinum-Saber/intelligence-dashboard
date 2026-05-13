# ACL Cables Procurement Intelligence Dashboard — Deployment Runbook

> **Audience:** System administrators and developers deploying or maintaining the dashboard.
> **Version:** Phase 3 | Last updated: 2026-05-13

---

## Prerequisites

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| Python | 3.12 | Backend runtime |
| uv | 0.4+ | Python package manager |
| Node.js | 20 LTS | Frontend build |
| npm | 10+ | Frontend package manager |
| Docker | 24+ | Optional — for containerised deployment |
| Docker Compose | 2.x | Optional — for multi-container setup |

---

## Local Development Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd "Intelligence Dashboard"
```

### 2. Backend

```bash
cd backend

# Install dependencies (creates .venv automatically)
uv sync

# Copy environment template
cp .env.example .env
# Edit .env — see Environment Variables section below

# Start the backend (debug mode by default)
uv run uvicorn app.main:app --reload
```

API available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

On first startup in debug mode the database is auto-seeded with 365 days of generated data. This takes ~5–10 seconds.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at: `http://localhost:5173`

---

## Environment Variables (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | No | `true` | `true` = generated data; `false` = live API calls |
| `DATABASE_URL` | No | `sqlite:///./procurement_intel.db` | SQLite for dev; PostgreSQL URL for prod |
| `SEED_DAYS` | No | `365` | Days of generated data on first startup |
| `FX_API_KEY` | Prod only | `""` | exchangerate-api.com key (required when `DEBUG=false`) |
| `NEWSAPI_KEY` | Prod only | `""` | newsapi.org key (required when `DEBUG=false`) |
| `SENTIMENT_ENABLED` | No | `true` | Enable FinBERT scoring. Set `false` to skip the 400 MB model download. |
| `SMTP_HOST` | Optional | `smtp.gmail.com` | SMTP server for email alerts |
| `SMTP_PORT` | Optional | `587` | SMTP port |
| `SMTP_USER` | Optional | `""` | SMTP username / email address |
| `SMTP_PASSWORD` | Optional | `""` | SMTP password or app-specific password |
| `ALERT_FROM_EMAIL` | Optional | `""` | From address for alert emails |
| `FRONTEND_URL` | No | `http://localhost:5173` | CORS allowed origin |

### Example production `.env`

```env
DEBUG=false
DATABASE_URL=postgresql://acl_user:password@localhost:5432/procurement_intel
SEED_DAYS=365
FX_API_KEY=your-exchangerate-api-key
NEWSAPI_KEY=your-newsapi-key
SENTIMENT_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@acl.lk
SMTP_PASSWORD=app-specific-password
ALERT_FROM_EMAIL=alerts@acl.lk
FRONTEND_URL=https://procurement-dashboard.acl.lk
```

---

## Database Setup

### Development (SQLite)

No setup required. SQLite file is created automatically at `backend/procurement_intel.db`.

### Production (PostgreSQL)

1. Install PostgreSQL 15+ and optionally TimescaleDB for time-series optimisation

```sql
-- As postgres superuser:
CREATE USER acl_user WITH PASSWORD 'your-password';
CREATE DATABASE procurement_intel OWNER acl_user;
```

2. Set `DATABASE_URL=postgresql://acl_user:password@localhost:5432/procurement_intel` in `.env`

3. Tables are created automatically on first startup (`Base.metadata.create_all`)

### Reseeding the database

```bash
# Option 1: Delete the SQLite file and restart (dev only)
rm backend/procurement_intel.db
uv run uvicorn app.main:app --reload

# Option 2: Run the seed script directly
cd backend
uv run python -m debug.seed
```

---

## Production Deployment (Docker Compose)

### 1. Build and start

```bash
docker-compose up -d --build
```

This starts:
- `backend` — FastAPI on port 8000
- `frontend` — Vite/Nginx on port 80

### 2. Environment variables for Docker

Pass environment variables via `docker-compose.yml` or a `.env` file at the project root. Example `docker-compose.yml` override:

```yaml
services:
  backend:
    environment:
      - DEBUG=false
      - DATABASE_URL=postgresql://acl_user:password@db:5432/procurement_intel
      - FX_API_KEY=${FX_API_KEY}
      - NEWSAPI_KEY=${NEWSAPI_KEY}
      - SENTIMENT_ENABLED=true
      - FRONTEND_URL=https://your-domain.com
  frontend:
    environment:
      - VITE_API_URL=https://your-domain.com/api
```

### 3. Adding PostgreSQL to Docker Compose

Uncomment the `db` service block in `docker-compose.yml`:

```yaml
  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: acl_user
      POSTGRES_PASSWORD: your-password
      POSTGRES_DB: procurement_intel
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  pgdata:
```

---

## VPS / AWS EC2 Deployment

### Recommended instance

- **AWS EC2:** t3.medium (2 vCPU, 4 GB RAM) minimum
- **OS:** Ubuntu 22.04 LTS
- **Ports:** 80 (HTTP), 443 (HTTPS), 22 (SSH)

### Setup steps

```bash
# 1. Update system and install Docker
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu

# 2. Clone the repository
git clone <repo-url>
cd "Intelligence Dashboard"

# 3. Create .env file with production values
cp backend/.env.example backend/.env
nano backend/.env   # fill in API keys, DB URL, SMTP config

# 4. Build and start
docker-compose up -d --build

# 5. Verify
docker-compose ps
curl http://localhost:8000/health
```

### Reverse proxy (Nginx)

For HTTPS and a clean domain name, place Nginx in front:

```nginx
server {
    listen 80;
    server_name procurement-dashboard.acl.lk;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name procurement-dashboard.acl.lk;

    ssl_certificate /etc/letsencrypt/live/procurement-dashboard.acl.lk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/procurement-dashboard.acl.lk/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:80;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Use `certbot` to provision Let's Encrypt SSL certificates.

---

## FinBERT Model Setup

On first use with `SENTIMENT_ENABLED=true`, the FinBERT model downloads ~400 MB from HuggingFace. In a production environment:

1. **Pre-download:** Run `POST /api/v1/news/score-now` once after deployment to trigger the download while monitoring
2. **Offline environments:** Download the model on a machine with internet access and mount it as a Docker volume:

```bash
# Download model to a local directory
pip install transformers torch
python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('ProsusAI/finbert', cache_dir='./finbert_cache'); AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert', cache_dir='./finbert_cache')"

# Mount the cache in Docker Compose:
# backend:
#   volumes:
#     - ./finbert_cache:/root/.cache/huggingface
```

---

## Scheduler Jobs

The APScheduler runs in-process with the FastAPI backend. Jobs run on the following schedule:

| Job | Interval | Notes |
|-----|----------|-------|
| FX rate collection | Every 15 min | Requires `FX_API_KEY` |
| Alert rule check | Every 15 min | Evaluates rules, creates events, sends emails |
| Commodity prices | Every 1 hour | Unofficial Yahoo Finance endpoint |
| Weather collection | Every 1 hour | Open-Meteo, always runs |
| News collection | Every 1 hour | Requires `NEWSAPI_KEY` |
| Sentiment scoring | Every 2 hours | Requires `SENTIMENT_ENABLED=true` |

Jobs run as daemon threads. If the backend process is killed, all jobs stop. Restart the backend to resume.

---

## Troubleshooting

### Backend won't start

```bash
# Check for Python/dependency issues
cd backend && uv run python -c "from app.main import app; print('OK')"

# Check environment file
cat backend/.env

# Check for port conflict
netstat -an | findstr 8000  # Windows
lsof -i :8000               # Linux/Mac
```

### Database errors

```bash
# SQLite: delete and reseed
rm backend/procurement_intel.db
cd backend && uv run uvicorn app.main:app --reload

# PostgreSQL: check connection
psql postgresql://acl_user:password@localhost:5432/procurement_intel -c "\dt"
```

### Frontend can't reach the backend

1. Verify the backend is running: `curl http://localhost:8000/health`
2. Check CORS: `FRONTEND_URL` in `.env` must match the frontend's origin exactly
3. Check `VITE_API_URL` in `frontend/.env` — defaults to `http://localhost:8000`

### FinBERT download fails

```bash
# Test HuggingFace connectivity
curl https://huggingface.co/ProsusAI/finbert

# Disable sentiment if model download is blocked
# Set SENTIMENT_ENABLED=false in .env and restart
```

### Stale data / API failures

Check **Configurations → Data Sources** in the dashboard. If a source shows as "degraded" or "down":

- **FX rate stale:** Check `FX_API_KEY` is set and not rate-limited (1,500 req/month on free tier)
- **Commodity prices stale:** Yahoo Finance endpoint may be down — this is a known fragility; restart the backend to retry
- **News stale:** Check `NEWSAPI_KEY` and daily request quota (100 req/day on free tier)
- **Weather stale:** Open-Meteo is the most reliable source; if this is down, it is an upstream outage

### Alert emails not sending

1. Verify SMTP settings in `.env`
2. For Gmail: use an App Password, not your account password (requires 2FA enabled)
3. Test manually:

```python
# cd backend && uv run python
import smtplib
from app.config import settings
with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
    s.starttls()
    s.login(settings.smtp_user, settings.smtp_password)
    print("SMTP OK")
```

---

## Monitoring & Maintenance

### Health check endpoint

```bash
curl http://localhost:8000/health
# → {"status": "ok", "debug": false}
```

### Data source audit

```bash
curl http://localhost:8000/api/v1/datasources/audit | python -m json.tool
```

### Database size

```bash
# SQLite
ls -lh backend/procurement_intel.db

# PostgreSQL
psql ... -c "SELECT pg_size_pretty(pg_database_size('procurement_intel'));"
```

### Log rotation

The backend logs to stdout. In Docker, logs are managed by the Docker logging driver. For production, configure log rotation:

```bash
docker-compose logs --tail=100 backend
```

### Backup

```bash
# SQLite
cp backend/procurement_intel.db procurement_intel_$(date +%Y%m%d).db

# PostgreSQL
pg_dump postgresql://acl_user:password@localhost:5432/procurement_intel > backup_$(date +%Y%m%d).sql
```

---

## Security Checklist (Pre-Production)

- [ ] `DEBUG=false` in production `.env`
- [ ] Strong `SMTP_PASSWORD` (use app-specific password for Gmail)
- [ ] Database password is strong and not the default
- [ ] HTTPS configured via reverse proxy (Certbot / Let's Encrypt)
- [ ] `FRONTEND_URL` set to the production domain only (not `*`)
- [ ] API keys stored only in `.env`, never in source code
- [ ] `.env` excluded from version control (check `.gitignore`)
- [ ] EC2 security group allows only ports 80, 443, 22 from authorised IPs
- [ ] SSH key-based authentication only (no password login)
- [ ] Regular backup schedule in place for the database

---

## Phase 4 Scoping (ERP Integration)

The following information is needed before ERP integration can be scoped:

1. **ERP system in use at ACL Cables** — SAP, Sage, custom, or other?
2. **API or data export capabilities** — Does the ERP expose a REST API? Can it export CSV/Excel on a schedule?
3. **Data required from ERP** — Purchase orders, GRNs, inventory levels, supplier master data
4. **IT contact** — Name and email of the ACL IT team member responsible for the ERP
5. **Network architecture** — Is the ERP on-premises or cloud? Will the dashboard be able to reach it?

A discovery meeting should be scheduled with the ACL IT team before any code is written for Phase 4.

---

*For end-user guidance, see `docs/user_guide.md`. For API reference, visit `http://localhost:8000/docs` when the backend is running.*
