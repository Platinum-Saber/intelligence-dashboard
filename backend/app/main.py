from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import FXRate  # ensure all models are registered
from app.routers import fx, commodities, weather, news, alerts, calculator, backtest, datasources
from app.scheduler.jobs import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    if settings.debug:
        db = SessionLocal()
        try:
            if db.query(FXRate).count() == 0:
                from debug.seed import seed_all
                seed_all(db)
        finally:
            db.close()

    start_scheduler()
    yield


app = FastAPI(
    title="ACL Procurement Intelligence Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fx.router, prefix="/api/v1/fx", tags=["FX"])
app.include_router(commodities.router, prefix="/api/v1/commodities", tags=["Commodities"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(calculator.router, prefix="/api/v1/calculator", tags=["Calculator"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["Backtest"])
app.include_router(datasources.router, prefix="/api/v1/datasources", tags=["DataSources"])


@app.get("/health")
def health():
    return {"status": "ok", "debug": settings.debug}


@app.get("/api/v1/settings")
def app_settings():
    from app.scheduler.jobs import scheduler

    def _fmt_interval(job) -> str:
        try:
            secs = int(job.trigger.interval.total_seconds())
        except Exception:
            return "unknown"
        if secs < 3600:
            mins = secs // 60
            return f"Every {mins} min"
        hours = secs // 3600
        return f"Every {hours} hour{'s' if hours > 1 else ''}"

    jobs_out = []
    _labels = {
        "collect_fx":          "FX collection",
        "collect_commodities": "Commodity prices",
        "collect_weather":     "Weather (Open-Meteo)",
        "collect_news":        "News collection",
        "score_sentiment":     "Sentiment scoring",
        "check_alerts":        "Alert check",
    }
    for job in scheduler.get_jobs():
        jobs_out.append({
            "id": job.id,
            "name": _labels.get(job.id, job.id),
            "interval": _fmt_interval(job),
        })

    return {
        "debug": settings.debug,
        "fx_api_key_configured": bool(settings.fx_api_key),
        "newsapi_key_configured": bool(settings.newsapi_key),
        "sentiment_enabled": settings.sentiment_enabled,
        "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
        "scheduler_jobs": jobs_out,
    }
