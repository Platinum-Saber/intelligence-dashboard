"""
Unit tests for app/scheduler/jobs.py
Covers 100% of statements, branches, exceptions, and the start_scheduler wiring.
"""
import sys
import pytest
from unittest.mock import MagicMock, patch, call

# ── stub apscheduler so it doesn't need to be installed in the test env ───────
_aps_bg_mod = MagicMock()
_mock_scheduler_instance = MagicMock()
_aps_bg_mod.BackgroundScheduler.return_value = _mock_scheduler_instance
sys.modules.setdefault("apscheduler", MagicMock())
sys.modules.setdefault("apscheduler.schedulers", MagicMock())
sys.modules["apscheduler.schedulers.background"] = _aps_bg_mod

# Ensure the module is imported so patch() can resolve 'app.scheduler.jobs.*'
import app.scheduler.jobs  # noqa: E402  (must come after sys.modules stubs)
from app.scheduler.jobs import (
    _collect_fx,
    _collect_commodities,
    _collect_weather,
    _collect_news,
    _score_sentiment,
    _check_alerts,
    start_scheduler,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_db():
    """Return a lightweight mock that mimics a SQLAlchemy Session."""
    db = MagicMock()
    return db


def _db_factory(db):
    """Return a callable that produces *db* when invoked (mocks SessionLocal)."""
    return MagicMock(return_value=db)


# ══════════════════════════════════════════════════════════════════════════════
# _collect_fx
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectFx:
    """Tests for _collect_fx() — FX rate collection job."""

    def test_early_return_debug_true_no_api_key(self):
        """debug=True and empty fx_api_key → function exits before any import."""
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr") as mock_fetch:
            mock_cfg.debug = True
            mock_cfg.fx_api_key = ""

            from app.scheduler.jobs import _collect_fx
            _collect_fx()

            mock_fetch.assert_not_called()

    def test_runs_when_debug_true_but_api_key_set(self):
        """debug=True but fx_api_key is present → should NOT short-circuit."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=320.5), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.fx.FXRate") as MockFXRate:
            mock_cfg.debug = True
            mock_cfg.fx_api_key = "some-key"

            from app.scheduler.jobs import _collect_fx
            _collect_fx()

            db.add.assert_called_once()
            db.commit.assert_called_once()
            db.close.assert_called_once()

    def test_runs_when_debug_false(self):
        """debug=False → runs regardless of fx_api_key."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=305.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.fx.FXRate"):
            mock_cfg.debug = False
            mock_cfg.fx_api_key = ""

            from app.scheduler.jobs import _collect_fx
            _collect_fx()

            db.add.assert_called_once()
            db.commit.assert_called_once()
            db.close.assert_called_once()

    def test_rate_none_skips_db_insert(self):
        """fetch_usd_lkr returns None → DB session is never opened."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=None), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.debug = False
            mock_cfg.fx_api_key = ""

            from app.scheduler.jobs import _collect_fx
            _collect_fx()

            db.add.assert_not_called()
            db.commit.assert_not_called()
            db.close.assert_not_called()

    def test_rate_stored_creates_fx_rate_record(self):
        """Valid rate → FXRate instantiated with correct fields and persisted."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=318.75), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.fx.FXRate") as MockFXRate:
            mock_cfg.debug = False
            mock_cfg.fx_api_key = ""

            from app.scheduler.jobs import _collect_fx
            _collect_fx()

            MockFXRate.assert_called_once()
            kwargs = MockFXRate.call_args.kwargs
            assert kwargs["usd_lkr"] == 318.75
            assert kwargs["source"] == "exchangerate-api"

    def test_rate_stored_logs_info(self, caplog):
        """Valid rate → logger.info message emitted."""
        import logging
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=315.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.fx.FXRate"):
            mock_cfg.debug = False
            mock_cfg.fx_api_key = ""

            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _collect_fx
                _collect_fx()

            assert any("315.0" in r.message for r in caplog.records)

    def test_db_commit_exception_still_closes_session(self):
        """Exception during commit → finally block must close the DB session."""
        db = _make_db()
        db.commit.side_effect = RuntimeError("DB commit failed")
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.fx_collector.fetch_usd_lkr", return_value=300.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.fx.FXRate"):
            mock_cfg.debug = False
            mock_cfg.fx_api_key = ""

            from app.scheduler.jobs import _collect_fx
            with pytest.raises(RuntimeError, match="DB commit failed"):
                _collect_fx()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# _collect_commodities
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectCommodities:
    """Tests for _collect_commodities() — copper & aluminium price collection."""

    def test_early_return_when_debug(self):
        """debug=True → returns immediately, no collectors called."""
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price") as mock_cu, \
             patch("app.collectors.commodity_collector.fetch_aluminium_price") as mock_al:
            mock_cfg.debug = True

            from app.scheduler.jobs import _collect_commodities
            _collect_commodities()

            mock_cu.assert_not_called()
            mock_al.assert_not_called()

    def test_both_prices_stored(self):
        """debug=False, both collectors return prices → two CommodityPrice rows added."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price", return_value=9500.0), \
             patch("app.collectors.commodity_collector.fetch_aluminium_price", return_value=2400.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.commodities.CommodityPrice") as MockCP:
            mock_cfg.debug = False

            from app.scheduler.jobs import _collect_commodities
            _collect_commodities()

            assert db.add.call_count == 2
            db.commit.assert_called_once()
            db.close.assert_called_once()

    def test_copper_none_skips_copper_insert(self):
        """fetch_copper_price returns None → only aluminium row added."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price", return_value=None), \
             patch("app.collectors.commodity_collector.fetch_aluminium_price", return_value=2400.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.commodities.CommodityPrice"):
            mock_cfg.debug = False

            from app.scheduler.jobs import _collect_commodities
            _collect_commodities()

            assert db.add.call_count == 1
            db.commit.assert_called_once()

    def test_both_prices_none_no_inserts(self):
        """Both collectors return None → db.add never called."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price", return_value=None), \
             patch("app.collectors.commodity_collector.fetch_aluminium_price", return_value=None), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.commodities.CommodityPrice"):
            mock_cfg.debug = False

            from app.scheduler.jobs import _collect_commodities
            _collect_commodities()

            db.add.assert_not_called()
            db.commit.assert_called_once()

    def test_commodity_price_fields(self):
        """CommodityPrice is constructed with correct symbol and source."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price", return_value=9100.0), \
             patch("app.collectors.commodity_collector.fetch_aluminium_price", return_value=None), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.commodities.CommodityPrice") as MockCP:
            mock_cfg.debug = False

            from app.scheduler.jobs import _collect_commodities
            _collect_commodities()

            MockCP.assert_called_once()
            kwargs = MockCP.call_args.kwargs
            assert kwargs["symbol"] == "COPPER"
            assert kwargs["source"] == "yahoo-finance"
            assert kwargs["price_usd"] == 9100.0

    def test_db_exception_closes_session(self):
        """Exception during commit → finally closes DB session."""
        db = _make_db()
        db.commit.side_effect = RuntimeError("commit error")
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.commodity_collector.fetch_copper_price", return_value=9000.0), \
             patch("app.collectors.commodity_collector.fetch_aluminium_price", return_value=2300.0), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.commodities.CommodityPrice"):
            mock_cfg.debug = False

            from app.scheduler.jobs import _collect_commodities
            with pytest.raises(RuntimeError):
                _collect_commodities()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# _collect_weather
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectWeather:
    """Tests for _collect_weather() — Open-Meteo readings (always runs)."""

    def test_empty_readings_skips_db(self):
        """Both collectors return [] → bulk_insert_mappings never called."""
        db = _make_db()
        with patch("app.collectors.weather_collector.fetch_sri_lanka_weather", return_value=[]), \
             patch("app.collectors.weather_collector.fetch_supplier_port_weather", return_value=[]), \
             patch("app.database.SessionLocal", _db_factory(db)):
            from app.scheduler.jobs import _collect_weather
            _collect_weather()

            db.bulk_insert_mappings.assert_not_called()
            db.commit.assert_not_called()

    def test_readings_bulk_inserted_and_committed(self):
        """Readings from both collectors → merged, bulk inserted, committed."""
        db = _make_db()
        sl_readings = [{"location_name": "Colombo", "rainfall_mm": 12.0}]
        port_readings = [{"location_name": "Shanghai", "rainfall_mm": 5.0}]
        with patch("app.collectors.weather_collector.fetch_sri_lanka_weather", return_value=sl_readings), \
             patch("app.collectors.weather_collector.fetch_supplier_port_weather", return_value=port_readings), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.weather.WeatherReading") as MockWR:
            from app.scheduler.jobs import _collect_weather
            _collect_weather()

            db.bulk_insert_mappings.assert_called_once_with(MockWR, sl_readings + port_readings)
            db.commit.assert_called_once()
            db.close.assert_called_once()

    def test_weather_logs_count(self, caplog):
        """Successful collection → log message includes reading count."""
        import logging
        db = _make_db()
        readings = [{"location_name": "Galle", "rainfall_mm": 0.0}] * 3
        with patch("app.collectors.weather_collector.fetch_sri_lanka_weather", return_value=readings), \
             patch("app.collectors.weather_collector.fetch_supplier_port_weather", return_value=[]), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.weather.WeatherReading"):
            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _collect_weather
                _collect_weather()

            assert any("3" in r.message for r in caplog.records)

    def test_only_sri_lanka_data_returned(self):
        """fetch_supplier_port_weather returns [] — only SL data inserted."""
        db = _make_db()
        sl_readings = [{"location_name": "Kandy", "rainfall_mm": 20.0}]
        with patch("app.collectors.weather_collector.fetch_sri_lanka_weather", return_value=sl_readings), \
             patch("app.collectors.weather_collector.fetch_supplier_port_weather", return_value=[]), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.weather.WeatherReading") as MockWR:
            from app.scheduler.jobs import _collect_weather
            _collect_weather()

            db.bulk_insert_mappings.assert_called_once_with(MockWR, sl_readings)

    def test_db_exception_closes_session(self):
        """Exception during bulk_insert_mappings → finally closes DB."""
        db = _make_db()
        db.bulk_insert_mappings.side_effect = RuntimeError("bulk insert failed")
        readings = [{"location_name": "Colombo", "rainfall_mm": 5.0}]
        with patch("app.collectors.weather_collector.fetch_sri_lanka_weather", return_value=readings), \
             patch("app.collectors.weather_collector.fetch_supplier_port_weather", return_value=[]), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.weather.WeatherReading"):
            from app.scheduler.jobs import _collect_weather
            with pytest.raises(RuntimeError):
                _collect_weather()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# _collect_news
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectNews:
    """Tests for _collect_news() — NewsAPI article ingestion."""

    def test_early_return_no_newsapi_key(self):
        """newsapi_key is empty → fetch never called."""
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.news_collector.fetch_supply_chain_news") as mock_fetch:
            mock_cfg.newsapi_key = ""

            from app.scheduler.jobs import _collect_news
            _collect_news()

            mock_fetch.assert_not_called()

    def test_early_return_empty_articles(self):
        """newsapi_key set but fetch returns [] → bulk_insert never called."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.news_collector.fetch_supply_chain_news", return_value=[]), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.newsapi_key = "abc123"

            from app.scheduler.jobs import _collect_news
            _collect_news()

            db.bulk_insert_mappings.assert_not_called()

    def test_articles_bulk_inserted_and_committed(self):
        """newsapi_key set, articles returned → bulk inserted and committed."""
        db = _make_db()
        articles = [{"headline": "Trade News", "topic": "TRADE"}] * 5
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.news_collector.fetch_supply_chain_news", return_value=articles), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.news.NewsItem") as MockNI:
            mock_cfg.newsapi_key = "abc123"

            from app.scheduler.jobs import _collect_news
            _collect_news()

            db.bulk_insert_mappings.assert_called_once_with(MockNI, articles)
            db.commit.assert_called_once()
            db.close.assert_called_once()

    def test_news_logs_article_count(self, caplog):
        """Successful news collection → log contains article count."""
        import logging
        db = _make_db()
        articles = [{"headline": f"Article {i}"} for i in range(7)]
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.news_collector.fetch_supply_chain_news", return_value=articles), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.news.NewsItem"):
            mock_cfg.newsapi_key = "key"

            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _collect_news
                _collect_news()

            assert any("7" in r.message for r in caplog.records)

    def test_db_exception_closes_session(self):
        """Exception during bulk_insert → finally closes DB session."""
        db = _make_db()
        db.bulk_insert_mappings.side_effect = RuntimeError("insert error")
        articles = [{"headline": "X"}]
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.collectors.news_collector.fetch_supply_chain_news", return_value=articles), \
             patch("app.database.SessionLocal", _db_factory(db)), \
             patch("app.models.news.NewsItem"):
            mock_cfg.newsapi_key = "key"

            from app.scheduler.jobs import _collect_news
            with pytest.raises(RuntimeError):
                _collect_news()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# _score_sentiment
# ══════════════════════════════════════════════════════════════════════════════

class TestScoreSentiment:
    """Tests for _score_sentiment() — FinBERT batch scoring job."""

    def test_early_return_when_disabled(self):
        """sentiment_enabled=False → score_unscored_news never called."""
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news") as mock_score:
            mock_cfg.sentiment_enabled = False

            from app.scheduler.jobs import _score_sentiment
            _score_sentiment()

            mock_score.assert_not_called()

    def test_scores_when_enabled_and_logs_if_nonzero(self, caplog):
        """sentiment_enabled=True, scored > 0 → log message emitted."""
        import logging
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news", return_value=42), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.sentiment_enabled = True

            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _score_sentiment
                _score_sentiment()

            assert any("42" in r.message for r in caplog.records)
            db.close.assert_called_once()

    def test_no_log_when_scored_zero(self, caplog):
        """scored=0 → no log, but DB session still closed."""
        import logging
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news", return_value=0), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.sentiment_enabled = True

            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _score_sentiment
                _score_sentiment()

            assert not any("scored" in r.message.lower() for r in caplog.records)
            db.close.assert_called_once()

    def test_no_log_when_scored_none(self, caplog):
        """scored=None (falsy) → no log, DB session still closed."""
        import logging
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news", return_value=None), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.sentiment_enabled = True

            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _score_sentiment
                _score_sentiment()

            assert not any("scored" in r.message.lower() for r in caplog.records)
            db.close.assert_called_once()

    def test_score_unscored_news_called_with_db_and_batch(self):
        """score_unscored_news must receive the DB session and batch_size=100."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news", return_value=0) as mock_score, \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.sentiment_enabled = True

            from app.scheduler.jobs import _score_sentiment
            _score_sentiment()

            mock_score.assert_called_once_with(db, batch_size=100)

    def test_db_exception_closes_session(self):
        """Exception during scoring → finally closes DB session."""
        db = _make_db()
        with patch("app.scheduler.jobs.settings") as mock_cfg, \
             patch("app.services.sentiment_service.score_unscored_news", side_effect=RuntimeError("NLP crash")), \
             patch("app.database.SessionLocal", _db_factory(db)):
            mock_cfg.sentiment_enabled = True

            from app.scheduler.jobs import _score_sentiment
            with pytest.raises(RuntimeError, match="NLP crash"):
                _score_sentiment()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# _check_alerts
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckAlerts:
    """Tests for _check_alerts() — alert evaluation job."""

    def test_no_log_when_no_alerts_triggered(self, caplog):
        """check_alerts returns [] → no log message, DB closed."""
        import logging
        db = _make_db()
        with patch("app.services.alert_service.check_alerts", return_value=[]) as mock_check, \
             patch("app.database.SessionLocal", _db_factory(db)):
            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _check_alerts
                _check_alerts()

            assert not any("alert" in r.message.lower() for r in caplog.records)
            mock_check.assert_called_once_with(db)
            db.close.assert_called_once()

    def test_logs_when_alerts_triggered(self, caplog):
        """check_alerts returns a non-empty list → log message with count emitted."""
        import logging
        db = _make_db()
        fake_alerts = [MagicMock(), MagicMock(), MagicMock()]
        with patch("app.services.alert_service.check_alerts", return_value=fake_alerts), \
             patch("app.database.SessionLocal", _db_factory(db)):
            with caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
                from app.scheduler.jobs import _check_alerts
                _check_alerts()

            assert any("3" in r.message for r in caplog.records)
            db.close.assert_called_once()

    def test_check_alerts_called_with_db_session(self):
        """check_alerts must be invoked with the DB session object."""
        db = _make_db()
        with patch("app.services.alert_service.check_alerts", return_value=[]) as mock_check, \
             patch("app.database.SessionLocal", _db_factory(db)):
            from app.scheduler.jobs import _check_alerts
            _check_alerts()

            mock_check.assert_called_once_with(db)

    def test_db_exception_closes_session(self):
        """Exception inside check_alerts → finally closes DB session."""
        db = _make_db()
        with patch("app.services.alert_service.check_alerts", side_effect=RuntimeError("alert crash")), \
             patch("app.database.SessionLocal", _db_factory(db)):
            from app.scheduler.jobs import _check_alerts
            with pytest.raises(RuntimeError, match="alert crash"):
                _check_alerts()

            db.close.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# start_scheduler
# ══════════════════════════════════════════════════════════════════════════════

class TestStartScheduler:
    """Tests for start_scheduler() — APScheduler wiring."""

    def test_registers_exactly_six_jobs(self):
        """start_scheduler must call add_job exactly 6 times."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            assert mock_sched.add_job.call_count == 6

    def test_scheduler_start_called(self):
        """scheduler.start() must be invoked."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            mock_sched.start.assert_called_once()

    def test_job_ids_are_unique(self):
        """Every add_job call must use a distinct id= keyword argument."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            ids = [c.kwargs["id"] for c in mock_sched.add_job.call_args_list]
            assert len(ids) == len(set(ids)), "Duplicate job IDs found"

    def test_expected_job_ids_present(self):
        """All six expected job IDs must be registered."""
        expected_ids = {
            "collect_fx",
            "collect_commodities",
            "collect_weather",
            "collect_news",
            "score_sentiment",
            "check_alerts",
        }
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            registered = {c.kwargs["id"] for c in mock_sched.add_job.call_args_list}
            assert registered == expected_ids

    def test_collect_fx_interval_minutes(self):
        """collect_fx job must fire every 20 minutes."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            fx_call = next(
                c for c in mock_sched.add_job.call_args_list
                if c.kwargs.get("id") == "collect_fx"
            )
            assert fx_call.kwargs["minutes"] == 20

    def test_collect_news_interval_hours(self):
        """collect_news job must fire every 3 hours."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            news_call = next(
                c for c in mock_sched.add_job.call_args_list
                if c.kwargs.get("id") == "collect_news"
            )
            assert news_call.kwargs["hours"] == 3

    def test_check_alerts_interval_minutes(self):
        """check_alerts job must fire every 15 minutes."""
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            alert_call = next(
                c for c in mock_sched.add_job.call_args_list
                if c.kwargs.get("id") == "check_alerts"
            )
            assert alert_call.kwargs["minutes"] == 15

    def test_immediate_jobs_have_next_run_time(self):
        """collect_fx, collect_commodities, collect_weather, collect_news must have next_run_time set."""
        immediate_ids = {"collect_fx", "collect_commodities", "collect_weather", "collect_news"}
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            for c in mock_sched.add_job.call_args_list:
                jid = c.kwargs.get("id")
                if jid in immediate_ids:
                    assert "next_run_time" in c.kwargs, f"{jid} is missing next_run_time"

    def test_deferred_jobs_have_no_next_run_time(self):
        """score_sentiment and check_alerts must NOT have next_run_time."""
        deferred_ids = {"score_sentiment", "check_alerts"}
        with patch("app.scheduler.jobs.scheduler") as mock_sched:
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

            for c in mock_sched.add_job.call_args_list:
                jid = c.kwargs.get("id")
                if jid in deferred_ids:
                    assert "next_run_time" not in c.kwargs, f"{jid} should not have next_run_time"

    def test_logs_started_message(self, caplog):
        """start_scheduler must log a 'Started' message."""
        import logging
        with patch("app.scheduler.jobs.scheduler"), \
             caplog.at_level(logging.INFO, logger="app.scheduler.jobs"):
            from app.scheduler.jobs import start_scheduler
            start_scheduler()

        assert any("started" in r.message.lower() for r in caplog.records)
