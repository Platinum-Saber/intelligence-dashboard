"""
Run standalone:   uv run python -m debug.seed
Or called from app startup when DEBUG=true and the DB is empty.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import FXRate, CommodityPrice, WeatherReading, NewsItem, AlertRule
from app.database import Base
from app.config import settings

from debug.generators.fx_generator import generate_fx_rates
from debug.generators.commodity_generator import generate_copper_prices, generate_aluminium_prices
from debug.generators.weather_generator import generate_weather
from debug.generators.news_generator import generate_news


def _default_alert_rules() -> list[AlertRule]:
    return [
        AlertRule(
            name="FX favourable — USD/LKR below 290",
            rule_type="FX_THRESHOLD",
            metric="usd_lkr",
            comparison="lt",
            threshold_value=290.0,
            enabled=True,
            email_recipients="",
        ),
        AlertRule(
            name="FX pressure — USD/LKR above 310",
            rule_type="FX_THRESHOLD",
            metric="usd_lkr",
            comparison="gt",
            threshold_value=310.0,
            enabled=True,
            email_recipients="",
        ),
        AlertRule(
            name="Copper dip >2% in 24h",
            rule_type="COMMODITY_DIP",
            metric="copper_price",
            comparison="lt",
            threshold_value=-2.0,   # interpreted as % change
            enabled=True,
            email_recipients="",
        ),
        AlertRule(
            name="Flood risk — Western Province HIGH or above",
            rule_type="WEATHER_RISK",
            metric="flood_risk",
            comparison="eq",
            threshold_text="HIGH",
            enabled=True,
            email_recipients="",
        ),
    ]


def seed_all(db: Session | None = None) -> None:
    close_after = db is None
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

    try:
        days = settings.seed_days
        print(f"[seed] Generating {days} days of debug data...")

        db.bulk_save_objects(generate_fx_rates(days))
        db.bulk_save_objects(generate_copper_prices(days))
        db.bulk_save_objects(generate_aluminium_prices(days))
        db.bulk_save_objects(generate_weather(days))
        db.bulk_save_objects(generate_news(days))
        db.bulk_save_objects(_default_alert_rules())

        db.commit()
        print("[seed] Done.")
    finally:
        if close_after:
            db.close()


if __name__ == "__main__":
    seed_all()
