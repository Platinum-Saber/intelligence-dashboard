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
    from app.collectors.weather_collector import fetch_sri_lanka_weather, fetch_supplier_port_weather, SL_DISTRICTS
    from app.database import SessionLocal
    from app.models.weather import WeatherReading
    from app.services import weather_service

    sl_readings = fetch_sri_lanka_weather()
    port_readings = fetch_supplier_port_weather()
    all_readings = sl_readings + port_readings
    if not all_readings:
        return

    db = SessionLocal()
    try:
        db.bulk_insert_mappings(WeatherReading, all_readings)
        db.commit()
        # Compute 14-day rolling drought risk and stamp it on the just-inserted SL district readings
        for name in SL_DISTRICTS:
            weather_service.update_drought_risk_latest(db, name)
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


# ── Historical backfill ───────────────────────────────────────────────────────

def _backfill_history() -> None:
    """On startup, ensure at least 7 days of FX and commodity data exist.
    Only inserts dates that are missing — safe to call on every restart."""
    from datetime import timedelta
    from app.database import SessionLocal
    from app.models.fx import FXRate
    from app.models.commodities import CommodityPrice
    from app.collectors.fx_collector import fetch_usd_lkr_history
    from app.collectors.commodity_collector import fetch_commodity_history

    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=8)

        # FX backfill
        existing_fx = {
            r.timestamp.date()
            for r in db.query(FXRate).filter(FXRate.timestamp >= since).all()
        }
        if len(existing_fx) < 7:
            history = fetch_usd_lkr_history(days=7)
            added = 0
            for entry in history:
                if entry["date"] not in existing_fx:
                    ts = datetime(entry["date"].year, entry["date"].month, entry["date"].day, 12, 0, 0)
                    db.add(FXRate(usd_lkr=entry["rate"], source="yahoo-finance-history", timestamp=ts))
                    added += 1
            if added:
                db.commit()
                logger.info(f"[backfill] FX: added {added} historical day(s)")

        # Commodity backfill
        for symbol in ["COPPER", "ALUMINIUM"]:
            existing = {
                r.timestamp.date()
                for r in db.query(CommodityPrice)
                .filter(CommodityPrice.symbol == symbol, CommodityPrice.timestamp >= since)
                .all()
            }
            if len(existing) < 7:
                history = fetch_commodity_history(symbol, days=7)
                added = 0
                for entry in history:
                    if entry["date"] not in existing:
                        ts = datetime(entry["date"].year, entry["date"].month, entry["date"].day, 12, 0, 0)
                        db.add(CommodityPrice(
                            symbol=symbol,
                            price_usd=entry["price_usd"],
                            source="yahoo-finance-history",
                            timestamp=ts,
                        ))
                        added += 1
                if added:
                    db.commit()
                    logger.info(f"[backfill] {symbol}: added {added} historical day(s)")

    except Exception as exc:
        logger.error(f"[backfill] failed: {exc}")
    finally:
        db.close()


# ── Startup ───────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    now = datetime.now()
    _backfill_history()  # Ensure 7-day history before live collection starts
    scheduler.add_job(_collect_fx,          "interval", minutes=20,  id="collect_fx",          next_run_time=now)
    scheduler.add_job(_collect_commodities, "interval", hours=1,     id="collect_commodities", next_run_time=now)
    scheduler.add_job(_collect_weather,     "interval", hours=1,     id="collect_weather",     next_run_time=now)
    scheduler.add_job(_collect_news,        "interval", hours=3,     id="collect_news",        next_run_time=now)
    scheduler.add_job(_score_sentiment,     "interval", hours=2,     id="score_sentiment")
    scheduler.add_job(_check_alerts,        "interval", minutes=15,  id="check_alerts")
    scheduler.start()
    logger.info("[scheduler] Started (6 jobs)")
