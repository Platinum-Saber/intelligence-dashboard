"""
Idempotent schema migrations run at startup after create_all().

Each entry is a SQL statement that adds a column only if it doesn't already
exist (PostgreSQL 9.6+ syntax). SQLite does not support IF NOT EXISTS on
ALTER TABLE — errors are silently swallowed so debug mode is unaffected.

Add a new entry here whenever a new nullable column is introduced on an
existing table. Migrations are applied in order; keep them append-only.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine


MIGRATIONS: list[str] = [
    # Phase 4 — Sprint 4.2: sustained-condition window for FX and weather alerts
    "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS trend_window_hours INTEGER",
    # Phase 4 — Sprint 4.3: rolling 14-day drought risk level per weather reading
    "ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS drought_risk VARCHAR(20)",
    # Phase 5 — Sprint 5.4: composite multi-condition alert rule payload
    "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS composite_condition TEXT",
]


def run_migrations(engine: Engine) -> None:
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
            except Exception:
                pass  # SQLite ALTER TABLE has no IF NOT EXISTS — safe to ignore
        conn.commit()
