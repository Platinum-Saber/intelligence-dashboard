"""
APScheduler job definitions.
Collectors run live in production; in DEBUG mode they log but don't hit external APIs
(exception: Open-Meteo weather which is free and keyless — runs regardless of DEBUG).
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


# ── Data collection ───────────────────────────────────────────────────────────

def _collect_fx() -> None:
    if settings.debug and not settings.fx_api_key:
        return
    from app.collectors.fx_collector import fetch_usd_lkr
    from app.database import SessionLocal
    from app.models.fx import FXRate
    from datetime import datetime

    rate = fetch_usd_lkr()
    if rate is not None:
        db = SessionLocal()
        try:
            db.add(FXRate(usd_lkr=rate, source="exchangerate-api", timestamp=datetime.utcnow()))
            db.commit()
            logger.info(f"[scheduler] FX collected: {rate}")
        finally:
            db.close()


def _collect_commodities() -> None:
    if settings.debug:
        return
    from app.collectors.commodity_collector import fetch_copper_price, fetch_aluminium_price
    from app.database import SessionLocal
    from app.models.commodities import CommodityPrice
    from datetime import datetime

    db = SessionLocal()
    try:
        for symbol, fn in [("COPPER", fetch_copper_price), ("ALUMINIUM", fetch_aluminium_price)]:
            price = fn()
            if price is not None:
                db.add(CommodityPrice(symbol=symbol, price_usd=price, source="yahoo-finance", timestamp=datetime.utcnow()))
        db.commit()
    finally:
        db.close()


def _collect_weather() -> None:
    """Open-Meteo is free + keyless — runs in all modes."""
    from app.collectors.weather_collector import fetch_sri_lanka_weather, fetch_supplier_port_weather
    from app.database import SessionLocal
    from app.models.weather import WeatherReading

    all_readings = fetch_sri_lanka_weather() + fetch_supplier_port_weather()
    if not all_readings:
        return

    db = SessionLocal()
    try:
        db.bulk_insert_mappings(WeatherReading, all_readings)
        db.commit()
        logger.info(f"[scheduler] Weather collected: {len(all_readings)} locations")
    finally:
        db.close()


def _collect_news() -> None:
    if not settings.newsapi_key:
        return
    from app.collectors.news_collector import fetch_supply_chain_news
    from app.database import SessionLocal
    from app.models.news import NewsItem

    articles = fetch_supply_chain_news()
    if not articles:
        return

    db = SessionLocal()
    try:
        db.bulk_insert_mappings(NewsItem, articles)
        db.commit()
        logger.info(f"[scheduler] News collected: {len(articles)} articles")
    finally:
        db.close()


# ── Sentiment scoring ─────────────────────────────────────────────────────────

def _score_sentiment() -> None:
    if not settings.sentiment_enabled:
        return
    from app.database import SessionLocal
    from app.services.sentiment_service import score_unscored_news

    db = SessionLocal()
    try:
        scored = score_unscored_news(db, batch_size=100)
        if scored:
            logger.info(f"[scheduler] Sentiment scored: {scored} items")
    finally:
        db.close()


# ── Alert evaluation ──────────────────────────────────────────────────────────

def _check_alerts() -> None:
    from app.database import SessionLocal
    from app.services.alert_service import check_alerts

    db = SessionLocal()
    try:
        triggered = check_alerts(db)
        if triggered:
            logger.info(f"[scheduler] {len(triggered)} alert(s) triggered")
    finally:
        db.close()


# ── Startup ───────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    now = datetime.now()
    scheduler.add_job(_collect_fx,          "interval", minutes=20,  id="collect_fx",          next_run_time=now)
    scheduler.add_job(_collect_commodities, "interval", hours=1,     id="collect_commodities", next_run_time=now)
    scheduler.add_job(_collect_weather,     "interval", hours=1,     id="collect_weather",     next_run_time=now)
    scheduler.add_job(_collect_news,        "interval", hours=3,     id="collect_news",        next_run_time=now)
    scheduler.add_job(_score_sentiment,     "interval", hours=2,     id="score_sentiment")
    scheduler.add_job(_check_alerts,        "interval", minutes=15,  id="check_alerts")
    scheduler.start()
    logger.info("[scheduler] Started (6 jobs)")
