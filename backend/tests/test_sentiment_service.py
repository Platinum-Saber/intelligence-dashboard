"""
Comprehensive unit tests for sentiment_service.py
Tests cover sentiment scoring, batch processing, pipeline loading, error handling, and edge cases.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from app.services.sentiment_service import (
    score_text,
    score_unscored_news,
    get_sentiment_summary,
    _get_pipeline,
)
from app.models.news import NewsItem


class TestGetPipeline:
    """Test _get_pipeline function - lazy-loads FinBERT model."""

    def test_get_pipeline_when_disabled(self, mock_settings_sentiment_disabled):
        """Should return None when sentiment is disabled."""
        # Reset global state
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        result = _get_pipeline()

        assert result is None

    def test_get_pipeline_successful_load(self, mock_settings_sentiment_enabled):
        """Should successfully load FinBERT pipeline."""
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        # Mock the pipeline function directly
        with patch("app.services.sentiment_service.pipeline") as mock_pipeline_func:
            mock_pipeline = MagicMock()
            mock_pipeline_func.return_value = mock_pipeline

            result = _get_pipeline()

            assert result is mock_pipeline
            mock_pipeline_func.assert_called_once()
            call_kwargs = mock_pipeline_func.call_args[1]
            assert call_kwargs["model"] == "ProsusAI/finbert"
            assert call_kwargs["device"] == -1
            assert call_kwargs["truncation"] is True
            assert call_kwargs["max_length"] == 512

    def test_get_pipeline_load_error_handling(self, mock_settings_sentiment_enabled):
        """Should gracefully handle pipeline load errors."""
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        with patch("app.services.sentiment_service.pipeline") as mock_pipeline_func:
            mock_pipeline_func.side_effect = Exception("Model not found")

            result = _get_pipeline()

            assert result is None

    def test_get_pipeline_caches_result(self, mock_settings_sentiment_enabled):
        """Should cache pipeline after first load."""
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        with patch("app.services.sentiment_service.pipeline") as mock_pipeline_func:
            mock_pipeline = MagicMock()
            mock_pipeline_func.return_value = mock_pipeline

            result1 = _get_pipeline()
            result2 = _get_pipeline()

            assert result1 is result2
            mock_pipeline_func.assert_called_once()  # Only called once due to caching

    def test_get_pipeline_respects_load_attempted_flag(self, mock_settings_sentiment_enabled):
        """Should not reload if _load_attempted is already True."""
        import app.services.sentiment_service as ss_module
        ss_module._load_attempted = True
        ss_module._pipeline = None

        with patch("app.services.sentiment_service.pipeline") as mock_pipeline_func:
            result = _get_pipeline()

            assert result is None
            mock_pipeline_func.assert_not_called()


class TestScoreText:
    """Test score_text function - scores individual text strings."""

    def test_score_text_pipeline_unavailable(self, mock_settings_sentiment_disabled):
        """Should return (None, None) when pipeline is unavailable."""
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        result = score_text("Some text")

        assert result == (None, None)

    def test_score_text_positive_sentiment(self, mock_settings_sentiment_enabled):
        """Should correctly score positive sentiment."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "positive", "score": 0.95}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("Great news on the market!")

        assert label == "POSITIVE"
        assert confidence == 0.95

    def test_score_text_negative_sentiment(self, mock_settings_sentiment_enabled):
        """Should correctly score negative sentiment."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "negative", "score": 0.87}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("Market crash feared")

        assert label == "NEGATIVE"
        assert confidence == 0.87

    def test_score_text_neutral_sentiment(self, mock_settings_sentiment_enabled):
        """Should correctly score neutral sentiment."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "neutral", "score": 0.62}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("The market remains stable")

        assert label == "NEUTRAL"
        assert confidence == 0.62

    def test_score_text_truncates_long_text(self, mock_settings_sentiment_enabled):
        """Should truncate text to 512 characters."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "positive", "score": 0.8}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        long_text = "a" * 1000
        score_text(long_text)

        # Check that truncation was applied
        call_args = mock_pipeline.call_args[0]
        assert len(call_args[0]) == 512

    def test_score_text_confidence_rounded(self, mock_settings_sentiment_enabled):
        """Should round confidence to 3 decimal places."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "positive", "score": 0.9567384}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("Good news")

        assert confidence == 0.957

    def test_score_text_exception_handling(self, mock_settings_sentiment_enabled):
        """Should return (None, None) on scoring exception."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.side_effect = Exception("Scoring failed")
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        result = score_text("Some text")

        assert result == (None, None)

    def test_score_text_empty_string(self, mock_settings_sentiment_enabled):
        """Should handle empty string input."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "neutral", "score": 0.5}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("")

        assert label == "NEUTRAL"
        assert confidence == 0.5

    def test_score_text_label_case_conversion(self, mock_settings_sentiment_enabled):
        """Should convert returned labels to uppercase."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        # Test various case variations
        mock_pipeline.return_value = [{"label": "PoSiTiVe", "score": 0.9}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        label, confidence = score_text("Good news")

        assert label == "POSITIVE"


class TestScoreUnscoredNews:
    """Test score_unscored_news function - batch scores unscored news items."""

    def test_score_unscored_news_pipeline_unavailable(self, test_db: Session, mock_settings_sentiment_disabled):
        """Should return 0 when pipeline is unavailable."""
        import app.services.sentiment_service as ss_module
        ss_module._pipeline = None
        ss_module._load_attempted = False

        result = score_unscored_news(test_db)

        assert result == 0

    def test_score_unscored_news_empty_database(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should return 0 when no unscored items exist."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        result = score_unscored_news(test_db)

        assert result == 0

    def test_score_unscored_news_single_item(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should score single unscored news item."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "positive", "score": 0.85}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="Good market news",
            summary="Summary",
            url="https://example.com",
            source="Source",
            topic="FX",
            relevance_score=0.8,
            sentiment=None,  # Unscored
        ))
        test_db.commit()

        result = score_unscored_news(test_db)

        assert result == 1
        scored_item = test_db.query(NewsItem).first()
        assert scored_item.sentiment == "POSITIVE"

    def test_score_unscored_news_multiple_items(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should score multiple unscored items."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [
            {"label": "positive", "score": 0.85},
            {"label": "negative", "score": 0.90},
            {"label": "neutral", "score": 0.60},
        ]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        for i, sentiment in enumerate(["positive", "negative", "neutral"]):
            test_db.add(NewsItem(
                published_at=datetime.now(UTC) - timedelta(hours=i),
                headline=f"Headline {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                topic="FX",
                relevance_score=0.8,
                sentiment=None,  # Unscored
            ))
        test_db.commit()

        result = score_unscored_news(test_db)

        assert result == 3
        items = test_db.query(NewsItem).order_by(NewsItem.published_at.desc()).all()
        assert items[0].sentiment == "POSITIVE"
        assert items[1].sentiment == "NEGATIVE"
        assert items[2].sentiment == "NEUTRAL"

    def test_score_unscored_news_respects_batch_size(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should respect batch_size limit."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        # Create 10 unscored items
        for i in range(10):
            test_db.add(NewsItem(
                published_at=datetime.now(UTC) - timedelta(hours=i),
                headline=f"Headline {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                topic="FX",
                relevance_score=0.8,
                sentiment=None,
            ))
        test_db.commit()

        # Set up mock to return enough results for batch_size
        mock_pipeline.return_value = [
            {"label": "positive", "score": 0.8} for _ in range(5)
        ]

        result = score_unscored_news(test_db, batch_size=5)

        assert result == 5

    def test_score_unscored_news_skips_already_scored(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should skip items that already have sentiment."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"label": "positive", "score": 0.8}]
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        # Add scored item
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="Already scored",
            summary="Summary",
            url="https://example.com/scored",
            source="Source",
            topic="FX",
            relevance_score=0.8,
            sentiment="NEGATIVE",
        ))
        # Add unscored item
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="Unscored",
            summary="Summary",
            url="https://example.com/unscored",
            source="Source",
            topic="FX",
            relevance_score=0.8,
            sentiment=None,
        ))
        test_db.commit()

        result = score_unscored_news(test_db)

        assert result == 1  # Only scored the one unscored item
        scored_item = test_db.query(NewsItem).filter_by(headline="Unscored").first()
        assert scored_item.sentiment == "POSITIVE"

    def test_score_unscored_news_batch_scoring_exception(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should handle batch scoring exceptions gracefully."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        mock_pipeline.side_effect = Exception("Batch scoring failed")
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="News",
            summary="Summary",
            url="https://example.com",
            source="Source",
            topic="FX",
            relevance_score=0.8,
            sentiment=None,
        ))
        test_db.commit()

        result = score_unscored_news(test_db)

        assert result == 0  # Exception handled, no items scored

    def test_score_unscored_news_default_batch_size_50(self, test_db: Session, mock_settings_sentiment_enabled):
        """Should default to batch_size of 50."""
        import app.services.sentiment_service as ss_module

        mock_pipeline = MagicMock()
        ss_module._pipeline = mock_pipeline
        ss_module._load_attempted = True

        # Create many items
        for i in range(60):
            test_db.add(NewsItem(
                published_at=datetime.now(UTC) - timedelta(hours=i),
                headline=f"Headline {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                topic="FX",
                relevance_score=0.8,
                sentiment=None,
            ))
        test_db.commit()

        mock_pipeline.return_value = [{"label": "positive", "score": 0.8} for _ in range(50)]

        result = score_unscored_news(test_db)  # No batch_size specified

        assert result == 50


class TestGetSentimentSummary:
    """Test get_sentiment_summary function - aggregates sentiment by topic."""

    def test_get_sentiment_summary_empty_database(self, test_db: Session):
        """Should return empty list when no data exists."""
        result = get_sentiment_summary(test_db)

        assert result == []
        assert isinstance(result, list)

    def test_get_sentiment_summary_single_topic(self, test_db: Session):
        """Should return summary for single topic."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="FX News",
            summary="Summary",
            url="https://example.com",
            source="Source",
            topic="FX",
            relevance_score=0.8,
            sentiment="POSITIVE",
        ))
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["topic"] == "FX"
        assert result[0]["positive"] == 1
        assert result[0]["negative"] == 0
        assert result[0]["neutral"] == 0
        assert result[0]["unscored"] == 0

    def test_get_sentiment_summary_multiple_sentiments(self, test_db: Session):
        """Should count items by sentiment."""
        items = [
            NewsItem(published_at=datetime.now(UTC), headline="P1", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="P2", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="N1", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEGATIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="N2", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEUTRAL"),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["positive"] == 2
        assert result[0]["negative"] == 1
        assert result[0]["neutral"] == 1
        assert result[0]["unscored"] == 0

    def test_get_sentiment_summary_unscored_items(self, test_db: Session):
        """Should count items with None sentiment as 'unscored'."""
        items = [
            NewsItem(published_at=datetime.now(UTC), headline="P1", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="U1", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment=None),
            NewsItem(published_at=datetime.now(UTC), headline="U2", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment=None),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["positive"] == 1
        assert result[0]["unscored"] == 2

    def test_get_sentiment_summary_multiple_topics(self, test_db: Session):
        """Should aggregate separately for each topic."""
        items = [
            NewsItem(published_at=datetime.now(UTC), headline="FX1", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="FX2", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEGATIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="CU1", summary="S", url="u", source="s", topic="COPPER", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="CU2", summary="S", url="u", source="s", topic="COPPER", relevance_score=0.8, sentiment="POSITIVE"),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 2
        by_topic = {r["topic"]: r for r in result}
        assert by_topic["FX"]["positive"] == 1
        assert by_topic["FX"]["negative"] == 1
        assert by_topic["COPPER"]["positive"] == 2

    def test_get_sentiment_summary_default_days_7(self, test_db: Session):
        """Should default to 7 days when not specified."""
        now = datetime.now(UTC)
        items = [
            NewsItem(published_at=now - timedelta(days=3), headline="Recent", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=now - timedelta(days=10), headline="Old", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEGATIVE"),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["positive"] == 1
        assert result[0]["negative"] == 0

    def test_get_sentiment_summary_custom_days(self, test_db: Session):
        """Should filter by custom days parameter."""
        now = datetime.now(UTC)
        items = [
            NewsItem(published_at=now - timedelta(days=15), headline="Recent", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=now - timedelta(days=40), headline="Old", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEGATIVE"),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db, days=30)

        assert len(result) == 1
        assert result[0]["positive"] == 1
        assert result[0]["negative"] == 0

    def test_get_sentiment_summary_excludes_none_topic(self, test_db: Session):
        """Should exclude items with None topic."""
        items = [
            NewsItem(published_at=datetime.now(UTC), headline="WithTopic", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE"),
            NewsItem(published_at=datetime.now(UTC), headline="NoTopic", summary="S", url="u", source="s", topic=None, relevance_score=0.8, sentiment="POSITIVE"),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["topic"] == "FX"

    def test_get_sentiment_summary_includes_period_days(self, test_db: Session):
        """Should include period_days in result."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="News",
            summary="S",
            url="u",
            source="s",
            topic="FX",
            relevance_score=0.8,
            sentiment="POSITIVE",
        ))
        test_db.commit()

        result = get_sentiment_summary(test_db, days=14)

        assert len(result) == 1
        assert result[0]["period_days"] == 14

    def test_get_sentiment_summary_complex_aggregation(self, test_db: Session):
        """Should handle complex aggregation with multiple topics and sentiments."""
        now = datetime.now(UTC)
        items = [
            # FX: 3 positive, 2 negative, 1 neutral, 1 unscored
            NewsItem(published_at=now - timedelta(days=i), headline=f"FX_P{i}", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="POSITIVE")
            for i in range(3)
        ] + [
            NewsItem(published_at=now - timedelta(days=i), headline=f"FX_N{i}", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEGATIVE")
            for i in range(2)
        ] + [
            NewsItem(published_at=now - timedelta(days=5), headline="FX_NET", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment="NEUTRAL"),
            NewsItem(published_at=now - timedelta(days=6), headline="FX_U", summary="S", url="u", source="s", topic="FX", relevance_score=0.8, sentiment=None),
        ] + [
            # COPPER: 2 positive
            NewsItem(published_at=now - timedelta(days=i), headline=f"CU_P{i}", summary="S", url="u", source="s", topic="COPPER", relevance_score=0.8, sentiment="POSITIVE")
            for i in range(2)
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_sentiment_summary(test_db, days=30)

        assert len(result) == 2
        by_topic = {r["topic"]: r for r in result}
        
        fx_summary = by_topic["FX"]
        assert fx_summary["positive"] == 3
        assert fx_summary["negative"] == 2
        assert fx_summary["neutral"] == 1
        assert fx_summary["unscored"] == 1
        
        copper_summary = by_topic["COPPER"]
        assert copper_summary["positive"] == 2
        assert copper_summary["negative"] == 0
        assert copper_summary["neutral"] == 0
        assert copper_summary["unscored"] == 0

    def test_get_sentiment_summary_invalid_sentiment_mapped_to_unscored(self, test_db: Session):
        """Should map invalid sentiment values to 'unscored'."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="Invalid",
            summary="S",
            url="u",
            source="s",
            topic="FX",
            relevance_score=0.8,
            sentiment="MIXED",  # Invalid value
        ))
        test_db.commit()

        result = get_sentiment_summary(test_db)

        assert len(result) == 1
        assert result[0]["unscored"] == 1
        assert result[0]["positive"] == 0
        assert result[0]["negative"] == 0
        assert result[0]["neutral"] == 0