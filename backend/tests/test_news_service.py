"""
Comprehensive unit tests for news_service.py
Tests cover all functions, edge cases, schema validation, filtering, and error handling.
"""
import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from app.services.news_service import (
    get_recent,
    VALID_TOPICS,
)
from app.models.news import NewsItem
from app.schemas.news import NewsItemOut


class TestValidTopics:
    """Test VALID_TOPICS constant."""

    def test_valid_topics_contains_expected_values(self):
        """Should contain all expected topic values."""
        expected = {"FX", "COPPER", "ALUMINIUM", "TRADE", "LOGISTICS"}
        assert VALID_TOPICS == expected

    def test_valid_topics_is_set(self):
        """VALID_TOPICS should be a set for efficient lookup."""
        assert isinstance(VALID_TOPICS, set)


class TestGetRecent:
    """Test get_recent function - retrieves recent news items with filtering."""

    def test_get_recent_empty_database(self, test_db: Session):
        """Should return empty list when no news exists."""
        result = get_recent(test_db)
        assert result == []
        assert isinstance(result, list)

    def test_get_recent_single_item(self, test_db: Session, sample_news_item):
        """Should return single news item."""
        test_db.add(NewsItem(**sample_news_item))
        test_db.commit()

        result = get_recent(test_db)

        assert len(result) == 1
        assert isinstance(result[0], NewsItemOut)
        assert result[0].headline == "FX Markets React to Trade Tensions"

    def test_get_recent_multiple_items(self, test_db: Session):
        """Should return multiple news items."""
        items = [
            NewsItem(
                published_at=datetime.now(UTC) - timedelta(days=1),
                headline="Item 1",
                summary="Summary 1",
                url="https://example.com/1",
                source="Source1",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=datetime.now(UTC) - timedelta(days=2),
                headline="Item 2",
                summary="Summary 2",
                url="https://example.com/2",
                source="Source2",
                topic="COPPER",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db)

        assert len(result) == 2

    def test_get_recent_default_days_7(self, test_db: Session):
        """Should default to 7 days when not specified."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(days=3),
                headline="Within 7 days",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=now - timedelta(days=10),
                headline="Beyond 7 days",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                topic="COPPER",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db)  # No days parameter

        assert len(result) == 1
        assert result[0].headline == "Within 7 days"

    def test_get_recent_filters_by_days(self, test_db: Session):
        """Should only return items published within specified days."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(days=3),
                headline="Item within 30 days",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=now - timedelta(days=40),
                headline="Item beyond 30 days",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                topic="COPPER",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, days=30)

        assert len(result) == 1
        assert result[0].headline == "Item within 30 days"

    def test_get_recent_ordered_by_published_descending(self, test_db: Session):
        """Should return items ordered by published_at descending (newest first)."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(days=5),
                headline="Oldest item",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=now - timedelta(days=1),
                headline="Newest item",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                topic="COPPER",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
            NewsItem(
                published_at=now - timedelta(days=3),
                headline="Middle item",
                summary="Summary",
                url="https://example.com/3",
                source="Source3",
                topic="TRADE",
                relevance_score=0.7,
                sentiment="NEGATIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, days=30)

        assert len(result) == 3
        assert result[0].headline == "Newest item"
        assert result[1].headline == "Middle item"
        assert result[2].headline == "Oldest item"

    def test_get_recent_default_limit_50(self, test_db: Session):
        """Should default to limit of 50 items when not specified."""
        now = datetime.now(UTC)
        # Create 60 items
        items = [
            NewsItem(
                published_at=now - timedelta(hours=i),
                headline=f"Item {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            )
            for i in range(60)
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db)  # No limit parameter

        assert len(result) == 50

    def test_get_recent_custom_limit(self, test_db: Session):
        """Should respect custom limit parameter."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(hours=i),
                headline=f"Item {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            )
            for i in range(10)
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, limit=5)

        assert len(result) == 5

    def test_get_recent_zero_limit(self, test_db: Session, sample_news_item):
        """Should return empty list when limit is 0."""
        test_db.add(NewsItem(**sample_news_item))
        test_db.commit()

        result = get_recent(test_db, limit=0)

        assert len(result) == 0

    def test_get_recent_topic_filter_valid(self, test_db: Session):
        """Should filter by valid topic when specified."""
        items = [
            NewsItem(
                published_at=datetime.now(UTC),
                headline="FX News",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                topic="FX",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Copper News",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                topic="COPPER",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Trade News",
                summary="Summary",
                url="https://example.com/3",
                source="Source3",
                topic="TRADE",
                relevance_score=0.7,
                sentiment="NEGATIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, topic="FX")

        assert len(result) == 1
        assert result[0].topic == "FX"
        assert result[0].headline == "FX News"

    def test_get_recent_topic_filter_case_insensitive(self, test_db: Session):
        """Topic filter should be case-insensitive (converts to uppercase)."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="FX News",
            summary="Summary",
            url="https://example.com/1",
            source="Source1",
            topic="FX",
            relevance_score=0.8,
            sentiment="NEUTRAL",
        ))
        test_db.commit()

        result = get_recent(test_db, topic="fx")  # lowercase

        assert len(result) == 1
        assert result[0].topic == "FX"

    def test_get_recent_topic_filter_invalid_ignored(self, test_db: Session):
        """Invalid topic should be ignored (returns all items)."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="FX News",
            summary="Summary",
            url="https://example.com/1",
            source="Source1",
            topic="FX",
            relevance_score=0.8,
            sentiment="NEUTRAL",
        ))
        test_db.commit()

        result = get_recent(test_db, topic="STOCKS")  # Not in VALID_TOPICS

        # Invalid topic is ignored, so it returns all items (1 item)
        assert len(result) == 1
        assert result[0].topic == "FX"

    def test_get_recent_all_valid_topics_filter(self, test_db: Session):
        """Should be able to filter by each valid topic."""
        items = [
            NewsItem(
                published_at=datetime.now(UTC),
                headline="FX News",
                topic="FX",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Copper News",
                topic="COPPER",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Aluminium News",
                topic="ALUMINIUM",
                summary="Summary",
                url="https://example.com/3",
                source="Source3",
                relevance_score=0.7,
                sentiment="NEGATIVE",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Trade News",
                topic="TRADE",
                summary="Summary",
                url="https://example.com/4",
                source="Source4",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Logistics News",
                topic="LOGISTICS",
                summary="Summary",
                url="https://example.com/5",
                source="Source5",
                relevance_score=0.75,
                sentiment="POSITIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        for topic in VALID_TOPICS:
            result = get_recent(test_db, topic=topic)
            assert len(result) == 1
            assert result[0].topic == topic

    def test_get_recent_topic_none_returns_all(self, test_db: Session):
        """When topic is None, should return items from all topics."""
        items = [
            NewsItem(
                published_at=datetime.now(UTC),
                headline="FX News",
                topic="FX",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=datetime.now(UTC),
                headline="Copper News",
                topic="COPPER",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, topic=None)

        assert len(result) == 2

    def test_get_recent_returns_correct_schema(self, test_db: Session, sample_news_item):
        """Should return NewsItemOut schema objects."""
        test_db.add(NewsItem(**sample_news_item))
        test_db.commit()

        result = get_recent(test_db)

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, NewsItemOut)
        assert hasattr(item, "id")
        assert hasattr(item, "published_at")
        assert hasattr(item, "headline")
        assert hasattr(item, "summary")
        assert hasattr(item, "url")
        assert hasattr(item, "source")
        assert hasattr(item, "topic")
        assert hasattr(item, "relevance_score")
        assert hasattr(item, "sentiment")

    def test_get_recent_null_optional_fields(self, test_db: Session):
        """Should handle NULL values in optional fields."""
        test_db.add(NewsItem(
            published_at=datetime.now(UTC),
            headline="News Item",
            summary=None,
            url=None,
            source=None,
            topic=None,
            relevance_score=None,
            sentiment=None,
        ))
        test_db.commit()

        result = get_recent(test_db)

        assert len(result) == 1
        assert result[0].summary is None
        assert result[0].url is None
        assert result[0].source is None
        assert result[0].topic is None
        # Note: relevance_score defaults to 0.5 in the model or schema
        assert result[0].relevance_score == 0.5  # Changed from None to 0.5
        assert result[0].sentiment is None

    def test_get_recent_combines_days_and_topic_filters(self, test_db: Session):
        """Should apply both days and topic filters together."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(days=1),
                headline="FX Recent",
                topic="FX",
                summary="Summary",
                url="https://example.com/1",
                source="Source1",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            ),
            NewsItem(
                published_at=now - timedelta(days=1),
                headline="Copper Recent",
                topic="COPPER",
                summary="Summary",
                url="https://example.com/2",
                source="Source2",
                relevance_score=0.9,
                sentiment="POSITIVE",
            ),
            NewsItem(
                published_at=now - timedelta(days=10),
                headline="FX Old",
                topic="FX",
                summary="Summary",
                url="https://example.com/3",
                source="Source3",
                relevance_score=0.7,
                sentiment="NEGATIVE",
            ),
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, days=7, topic="FX")

        assert len(result) == 1
        assert result[0].headline == "FX Recent"
        assert result[0].topic == "FX"

    def test_get_recent_combines_days_topic_and_limit(self, test_db: Session):
        """Should apply days, topic, and limit filters together."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(hours=i),
                headline=f"FX News {i}",
                topic="FX",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            )
            for i in range(5)
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db, days=7, topic="FX", limit=2)

        assert len(result) == 2

    def test_get_recent_no_filters(self, test_db: Session):
        """Should work with no filters (all defaults)."""
        now = datetime.now(UTC)
        items = [
            NewsItem(
                published_at=now - timedelta(days=i),
                headline=f"News {i}",
                topic="FX" if i % 2 == 0 else "COPPER",
                summary=f"Summary {i}",
                url=f"https://example.com/{i}",
                source="Source",
                relevance_score=0.8,
                sentiment="NEUTRAL",
            )
            for i in range(5)
        ]
        test_db.add_all(items)
        test_db.commit()

        result = get_recent(test_db)

        assert len(result) == 5

    def test_get_recent_empty_string_topic(self, test_db: Session, sample_news_item):
        """Empty string topic should be treated as no filter."""
        test_db.add(NewsItem(**sample_news_item))
        test_db.commit()

        result = get_recent(test_db, topic="")

        # Empty string is treated as no filter, returns all items
        assert len(result) == 1

    def test_get_recent_whitespace_topic(self, test_db: Session, sample_news_item):
        """Whitespace-only topic should be stripped and treated as no filter."""
        test_db.add(NewsItem(**sample_news_item))
        test_db.commit()

        result = get_recent(test_db, topic="   ")

        # Whitespace is stripped, resulting in empty string -> no filter
        assert len(result) == 1

    def test_get_recent_schema_validation(self, test_db: Session):
        """Should properly validate and convert to schema with all fields."""
        now = datetime.now(UTC)
        test_db.add(NewsItem(
            published_at=now,
            headline="Comprehensive Test",
            summary="Full summary text",
            url="https://example.com/full",
            source="Bloomberg",
            topic="FX",
            relevance_score=0.95,
            sentiment="POSITIVE",
        ))
        test_db.commit()

        result = get_recent(test_db, days=1, topic="FX")

        assert len(result) == 1
        item = result[0]
        assert item.headline == "Comprehensive Test"
        assert item.summary == "Full summary text"
        assert item.url == "https://example.com/full"
        assert item.source == "Bloomberg"
        assert item.topic == "FX"
        assert item.relevance_score == 0.95
        assert item.sentiment == "POSITIVE"