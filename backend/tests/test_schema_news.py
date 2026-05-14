"""
Unit tests for app/schemas/news.py — NewsItemOut.
Covers valid construction, ORM mode, every optional field, required-field
validation errors, and type-coercion/rejection.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.schemas.news import NewsItemOut


# ═══════════════════════════════════════════════════════════════════════════════
# NewsItemOut
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsItemOut:
    """Tests for the NewsItemOut response schema."""

    _TS = datetime(2026, 5, 14, 8, 0, 0, tzinfo=UTC)

    def _full_kwargs(self) -> dict:
        return {
            "id": 1,
            "published_at": self._TS,
            "headline": "Supply Chain Disruption in Asia",
            "summary": "Ports report significant delays due to weather events.",
            "url": "https://example.com/news/1",
            "source": "Reuters",
            "topic": "LOGISTICS",
            "relevance_score": 0.91,
            "sentiment": "NEGATIVE",
        }

    # ── valid construction ────────────────────────────────────────────────────

    def test_valid_full(self):
        """All fields provided → model instantiates correctly."""
        obj = NewsItemOut(**self._full_kwargs())
        assert obj.id == 1
        assert obj.headline == "Supply Chain Disruption in Asia"
        assert obj.topic == "LOGISTICS"
        assert obj.sentiment == "NEGATIVE"
        assert obj.relevance_score == pytest.approx(0.91)

    def test_nullable_fields_accept_none(self):
        """All nullable (str|None / float|None) fields accept explicit None."""
        obj = NewsItemOut(
            id=2, published_at=self._TS, headline="Minimal Item",
            summary=None, url=None, source=None,
            topic=None, relevance_score=None, sentiment=None,
        )
        assert obj.summary is None
        assert obj.url is None
        assert obj.source is None
        assert obj.topic is None
        assert obj.relevance_score is None
        assert obj.sentiment is None

    # ── each optional field individually ─────────────────────────────────────

    def test_summary_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "summary": None})
        assert obj.summary is None

    def test_url_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "url": None})
        assert obj.url is None

    def test_source_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "source": None})
        assert obj.source is None

    def test_topic_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "topic": None})
        assert obj.topic is None

    def test_relevance_score_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "relevance_score": None})
        assert obj.relevance_score is None

    def test_sentiment_none(self):
        obj = NewsItemOut(**{**self._full_kwargs(), "sentiment": None})
        assert obj.sentiment is None

    def test_relevance_score_zero(self):
        """relevance_score=0.0 is a valid float (not falsy-excluded)."""
        obj = NewsItemOut(**{**self._full_kwargs(), "relevance_score": 0.0})
        assert obj.relevance_score == 0.0

    def test_relevance_score_integer_coerced(self):
        """Integer relevance_score is coerced to float."""
        obj = NewsItemOut(**{**self._full_kwargs(), "relevance_score": 1})
        assert isinstance(obj.relevance_score, float)

    # ── ORM mode ─────────────────────────────────────────────────────────────

    def test_from_orm_full(self):
        """model_validate on an ORM-like object works (from_attributes=True)."""
        orm_obj = MagicMock()
        orm_obj.id = 5
        orm_obj.published_at = self._TS
        orm_obj.headline = "ORM News"
        orm_obj.summary = "A summary"
        orm_obj.url = "https://example.com/5"
        orm_obj.source = "AP"
        orm_obj.topic = "TRADE"
        orm_obj.relevance_score = 0.75
        orm_obj.sentiment = "POSITIVE"

        result = NewsItemOut.model_validate(orm_obj)

        assert result.id == 5
        assert result.headline == "ORM News"
        assert result.sentiment == "POSITIVE"

    def test_from_orm_optional_fields_none(self):
        """ORM object with all optional fields None is accepted."""
        orm_obj = MagicMock()
        orm_obj.id = 6
        orm_obj.published_at = self._TS
        orm_obj.headline = "Bare Item"
        orm_obj.summary = None
        orm_obj.url = None
        orm_obj.source = None
        orm_obj.topic = None
        orm_obj.relevance_score = None
        orm_obj.sentiment = None

        result = NewsItemOut.model_validate(orm_obj)

        assert result.summary is None
        assert result.topic is None

    # ── serialisation ─────────────────────────────────────────────────────────

    def test_model_dump_contains_all_fields(self):
        """model_dump() returns a dict with all nine expected keys."""
        obj = NewsItemOut(**self._full_kwargs())
        d = obj.model_dump()
        expected_keys = {
            "id", "published_at", "headline", "summary",
            "url", "source", "topic", "relevance_score", "sentiment",
        }
        assert set(d.keys()) == expected_keys

    def test_model_dump_values_match(self):
        """model_dump() values match the provided input."""
        kwargs = self._full_kwargs()
        obj = NewsItemOut(**kwargs)
        d = obj.model_dump()
        assert d["headline"] == kwargs["headline"]
        assert d["topic"] == kwargs["topic"]
        assert d["relevance_score"] == pytest.approx(kwargs["relevance_score"])

    # ── missing required fields ───────────────────────────────────────────────

    def test_missing_id_raises(self):
        """id is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            NewsItemOut(published_at=self._TS, headline="No ID")
        assert "id" in str(exc_info.value)

    def test_missing_published_at_raises(self):
        """published_at is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            NewsItemOut(id=1, headline="No Date")
        assert "published_at" in str(exc_info.value)

    def test_missing_headline_raises(self):
        """headline is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            NewsItemOut(id=1, published_at=self._TS)
        assert "headline" in str(exc_info.value)

    # ── invalid types ─────────────────────────────────────────────────────────

    def test_invalid_id_type_raises(self):
        """Non-integer id → ValidationError."""
        with pytest.raises(ValidationError):
            NewsItemOut(**{**self._full_kwargs(), "id": "abc"})

    def test_invalid_published_at_raises(self):
        """Non-datetime published_at → ValidationError."""
        with pytest.raises(ValidationError):
            NewsItemOut(**{**self._full_kwargs(), "published_at": "not-a-date"})

    def test_invalid_relevance_score_raises(self):
        """Non-numeric relevance_score → ValidationError."""
        with pytest.raises(ValidationError):
            NewsItemOut(**{**self._full_kwargs(), "relevance_score": "high"})
