from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.commodities import CommodityPrice
from app.models.fx import FXRate
from app.models.news import NewsItem
from app.models.weather import WeatherReading


def _audit_source(
    last_ts: datetime | None,
    count_24h: int,
    source_name: str,
    fragility_rating: str,
    fragility_reason: str,
    paid_fallback: str | None,
    notes: str,
) -> dict:
    now = datetime.utcnow()
    if last_ts is None:
        status = "down"
    elif (now - last_ts).total_seconds() > 3 * 3600:
        status = "degraded"
    else:
        status = "ok"

    return {
        "source_name": source_name,
        "status": status,
        "data_points_24h": count_24h,
        "last_data_timestamp": last_ts,
        "fragility_rating": fragility_rating,
        "fragility_reason": fragility_reason,
        "paid_fallback": paid_fallback,
        "notes": notes,
    }


def get_datasource_audit(db: Session) -> dict:
    since_24h = datetime.utcnow() - timedelta(hours=24)

    # FX
    fx_last = db.query(FXRate).order_by(FXRate.timestamp.desc()).first()
    fx_count = db.query(FXRate).filter(FXRate.timestamp >= since_24h).count()

    # Copper
    cu_last = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == "COPPER")
        .order_by(CommodityPrice.timestamp.desc())
        .first()
    )
    cu_count = db.query(CommodityPrice).filter(
        CommodityPrice.symbol == "COPPER", CommodityPrice.timestamp >= since_24h
    ).count()

    # Aluminium
    al_last = (
        db.query(CommodityPrice)
        .filter(CommodityPrice.symbol == "ALUMINIUM")
        .order_by(CommodityPrice.timestamp.desc())
        .first()
    )
    al_count = db.query(CommodityPrice).filter(
        CommodityPrice.symbol == "ALUMINIUM", CommodityPrice.timestamp >= since_24h
    ).count()

    # Weather
    wx_last = db.query(WeatherReading).order_by(WeatherReading.timestamp.desc()).first()
    wx_count = db.query(WeatherReading).filter(WeatherReading.timestamp >= since_24h).count()

    # News
    news_last = db.query(NewsItem).order_by(NewsItem.published_at.desc()).first()
    news_count = db.query(NewsItem).filter(NewsItem.published_at >= since_24h).count()

    sources = [
        _audit_source(
            last_ts=fx_last.timestamp if fx_last else None,
            count_24h=fx_count,
            source_name="FX Rate — exchangerate-api.com",
            fragility_rating="MEDIUM",
            fragility_reason="Freemium tier: 1,500 req/month. Exceeding limit causes 429 errors.",
            paid_fallback="Open Exchange Rates (paid) or CBSL API (Sri Lanka central bank, free but manual scrape)",
            notes="Requires FX_API_KEY env var. Runs every 15 min = ~2,880 req/month — exceeds free tier. Consider upgrading or switching to CBSL.",
        ),
        _audit_source(
            last_ts=cu_last.timestamp if cu_last else None,
            count_24h=cu_count,
            source_name="LME Copper — Yahoo Finance (HG=F)",
            fragility_rating="HIGH",
            fragility_reason="Unofficial endpoint with no SLA. Yahoo Finance has broken this endpoint before without notice.",
            paid_fallback="Metals-API.com (paid) or Quandl LME feed (paid)",
            notes="No API key required but endpoint may return stale or malformed data. Add freshness check and alerting if data is >2h old.",
        ),
        _audit_source(
            last_ts=al_last.timestamp if al_last else None,
            count_24h=al_count,
            source_name="LME Aluminium — Yahoo Finance (ALI=F)",
            fragility_rating="HIGH",
            fragility_reason="Same as copper — unofficial Yahoo Finance endpoint, no SLA, no versioning.",
            paid_fallback="Metals-API.com (paid) or Quandl LME feed (paid)",
            notes="Consider consolidating copper and aluminium under a single paid commodities API for reliability.",
        ),
        _audit_source(
            last_ts=wx_last.timestamp if wx_last else None,
            count_24h=wx_count,
            source_name="Weather — Open-Meteo",
            fragility_rating="LOW",
            fragility_reason="Official free API with published uptime SLA. No key required. Runs in all modes.",
            paid_fallback=None,
            notes="Most reliable data source in the stack. Covers both Sri Lanka districts and supplier ports. No action needed.",
        ),
        _audit_source(
            last_ts=news_last.published_at if news_last else None,
            count_24h=news_count,
            source_name="News — NewsAPI.org",
            fragility_rating="MEDIUM",
            fragility_reason="Developer plan: 100 req/day, articles delayed by 24h. Production plan required for real-time news.",
            paid_fallback="GNews API (paid), Bloomberg RSS (free limited), Reuters RSS (free limited)",
            notes="Requires NEWSAPI_KEY env var. Free tier has a 24h delay — may miss same-day market events. Upgrade for real-time procurement signals.",
        ),
    ]

    return {
        "sources": sources,
        "audit_timestamp": datetime.utcnow(),
        "overall_health": _overall_health(sources),
    }


def _overall_health(sources: list[dict]) -> str:
    statuses = [s["status"] for s in sources]
    if all(s == "ok" for s in statuses):
        return "ok"
    if any(s == "down" for s in statuses):
        return "degraded"
    return "degraded"
