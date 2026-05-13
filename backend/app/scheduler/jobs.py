"""
APScheduler job definitions.
In DEBUG mode these log without touching external APIs.
In production mode the collectors do real fetches and persist results.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _collect_fx() -> None:
    if settings.debug:
        logger.debug("[scheduler] FX collect skipped (debug mode)")
        return
    from app.collectors.fx_collector import fetch_usd_lkr
    from app.database import SessionLocal
    from app.models.fx import FXRate
    from datetime import datetime

    rate = fetch_usd_lkr()
    if rate is not None:
        db = SessionLocal()
        try:
            db.add(FXRate(usd_lkr=rate, source="exchangerate-api"))
            db.commit()
        finally:
            db.close()


def _collect_commodities() -> None:
    if settings.debug:
        logger.debug("[scheduler] Commodity collect skipped (debug mode)")
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
                db.add(CommodityPrice(symbol=symbol, price_usd=price, source="yahoo-finance"))
        db.commit()
    finally:
        db.close()


def _collect_weather() -> None:
    if settings.debug:
        logger.debug("[scheduler] Weather collect skipped (debug mode)")
        return
    from app.collectors.weather_collector import fetch_sri_lanka_weather
    # Phase 2: persist results
    fetch_sri_lanka_weather()


def _collect_news() -> None:
    if settings.debug:
        logger.debug("[scheduler] News collect skipped (debug mode)")
        return
    from app.collectors.news_collector import fetch_supply_chain_news
    fetch_supply_chain_news()


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


def start_scheduler() -> None:
    scheduler.add_job(_collect_fx, "interval", minutes=15, id="collect_fx")
    scheduler.add_job(_collect_commodities, "interval", hours=1, id="collect_commodities")
    scheduler.add_job(_collect_weather, "interval", hours=1, id="collect_weather")
    scheduler.add_job(_collect_news, "interval", hours=1, id="collect_news")
    scheduler.add_job(_check_alerts, "interval", minutes=15, id="check_alerts")
    scheduler.start()
    logger.info("[scheduler] Started")
