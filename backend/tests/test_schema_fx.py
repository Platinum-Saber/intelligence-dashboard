"""
Unit tests for app/schemas/fx.py — FXRateOut and FXSummary.
Covers valid construction, ORM mode, optional fields, required-field
validation errors, and type-coercion/rejection.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.schemas.fx import FXRateOut, FXSummary


# ═══════════════════════════════════════════════════════════════════════════════
# FXRateOut
# ═══════════════════════════════════════════════════════════════════════════════

class TestFXRateOut:
    """Tests for the FXRateOut response schema."""

    # ── valid construction ────────────────────────────────────────────────────

    def test_valid_full(self):
        """All fields provided → model instantiates without error."""
        obj = FXRateOut(
            id=1,
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            usd_lkr=318.75,
            source="exchangerate-api",
        )
        assert obj.id == 1
        assert obj.usd_lkr == 318.75
        assert obj.source == "exchangerate-api"

    def test_source_none_is_valid(self):
        """source is Optional[str] → None is accepted."""
        obj = FXRateOut(
            id=2,
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            usd_lkr=300.0,
            source=None,
        )
        assert obj.source is None

    def test_source_explicit_none_accepted(self):
        """source=None is explicitly accepted (field is str | None)."""
        obj = FXRateOut(
            id=3,
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            usd_lkr=305.0,
            source=None,
        )
        assert obj.source is None

    def test_timestamp_stored_correctly(self):
        """timestamp field stores the exact datetime provided."""
        ts = datetime(2026, 1, 15, 9, 30, 0, tzinfo=UTC)
        obj = FXRateOut(id=4, timestamp=ts, usd_lkr=320.0, source=None)
        assert obj.timestamp == ts

    def test_usd_lkr_float_coercion(self):
        """Integer value for usd_lkr is coerced to float."""
        obj = FXRateOut(id=5, timestamp=datetime.now(UTC), usd_lkr=300, source=None)
        assert isinstance(obj.usd_lkr, float)

    # ── ORM mode ─────────────────────────────────────────────────────────────

    def test_from_orm_object(self):
        """model_validate on an ORM-like object works (from_attributes=True)."""
        orm_obj = MagicMock()
        orm_obj.id = 10
        orm_obj.timestamp = datetime(2026, 5, 1, 0, 0, 0)
        orm_obj.usd_lkr = 315.5
        orm_obj.source = "test-source"

        result = FXRateOut.model_validate(orm_obj)

        assert result.id == 10
        assert result.usd_lkr == 315.5
        assert result.source == "test-source"

    def test_from_orm_source_none(self):
        """ORM object with source=None is handled correctly."""
        orm_obj = MagicMock()
        orm_obj.id = 11
        orm_obj.timestamp = datetime(2026, 5, 1, 0, 0, 0)
        orm_obj.usd_lkr = 310.0
        orm_obj.source = None

        result = FXRateOut.model_validate(orm_obj)

        assert result.source is None

    # ── serialisation ─────────────────────────────────────────────────────────

    def test_model_dump_contains_all_fields(self):
        """model_dump() returns a dict with all expected keys."""
        obj = FXRateOut(
            id=20,
            timestamp=datetime(2026, 5, 14, 12, 0, 0),
            usd_lkr=318.0,
            source="api",
        )
        d = obj.model_dump()
        assert set(d.keys()) == {"id", "timestamp", "usd_lkr", "source"}

    # ── missing required fields ───────────────────────────────────────────────

    def test_missing_id_raises(self):
        """id is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            FXRateOut(timestamp=datetime.now(UTC), usd_lkr=300.0, source=None)
        assert "id" in str(exc_info.value)

    def test_missing_timestamp_raises(self):
        """timestamp is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            FXRateOut(id=1, usd_lkr=300.0, source=None)
        assert "timestamp" in str(exc_info.value)

    def test_missing_usd_lkr_raises(self):
        """usd_lkr is required → ValidationError when omitted."""
        with pytest.raises(ValidationError) as exc_info:
            FXRateOut(id=1, timestamp=datetime.now(UTC), source=None)
        assert "usd_lkr" in str(exc_info.value)

    # ── invalid types ─────────────────────────────────────────────────────────

    def test_invalid_id_type_raises(self):
        """Non-integer id → ValidationError."""
        with pytest.raises(ValidationError):
            FXRateOut(id="not-an-int", timestamp=datetime.now(UTC), usd_lkr=300.0)

    def test_invalid_usd_lkr_type_raises(self):
        """Non-numeric usd_lkr → ValidationError."""
        with pytest.raises(ValidationError):
            FXRateOut(id=1, timestamp=datetime.now(UTC), usd_lkr="high")

    def test_invalid_timestamp_type_raises(self):
        """Non-datetime timestamp → ValidationError."""
        with pytest.raises(ValidationError):
            FXRateOut(id=1, timestamp="not-a-date", usd_lkr=300.0)


# ═══════════════════════════════════════════════════════════════════════════════
# FXSummary
# ═══════════════════════════════════════════════════════════════════════════════

class TestFXSummary:
    """Tests for the FXSummary aggregation schema."""

    def _valid_kwargs(self) -> dict:
        return {
            "current": 318.0,
            "change_24h": -2.5,
            "change_24h_pct": -0.78,
            "high_30d": 325.0,
            "low_30d": 310.0,
            "avg_30d": 316.5,
        }

    # ── valid construction ────────────────────────────────────────────────────

    def test_valid_full(self):
        """All six float fields provided → model is valid."""
        obj = FXSummary(**self._valid_kwargs())
        assert obj.current == 318.0
        assert obj.change_24h == -2.5
        assert obj.change_24h_pct == -0.78
        assert obj.high_30d == 325.0
        assert obj.low_30d == 310.0
        assert obj.avg_30d == 316.5

    def test_integer_inputs_coerced_to_float(self):
        """Integer values are coerced to float for all fields."""
        obj = FXSummary(
            current=318,
            change_24h=0,
            change_24h_pct=0,
            high_30d=320,
            low_30d=310,
            avg_30d=315,
        )
        for field in ("current", "change_24h", "change_24h_pct", "high_30d", "low_30d", "avg_30d"):
            assert isinstance(getattr(obj, field), float)

    def test_negative_change_accepted(self):
        """Negative change_24h and change_24h_pct are valid."""
        obj = FXSummary(**{**self._valid_kwargs(), "change_24h": -10.0, "change_24h_pct": -3.0})
        assert obj.change_24h == -10.0
        assert obj.change_24h_pct == -3.0

    def test_zero_values_accepted(self):
        """Zero is a valid value for all numeric fields."""
        obj = FXSummary(
            current=0.0, change_24h=0.0, change_24h_pct=0.0,
            high_30d=0.0, low_30d=0.0, avg_30d=0.0,
        )
        assert obj.current == 0.0

    # ── serialisation ─────────────────────────────────────────────────────────

    def test_model_dump_contains_all_fields(self):
        """model_dump() returns a dict with all six expected keys."""
        obj = FXSummary(**self._valid_kwargs())
        d = obj.model_dump()
        assert set(d.keys()) == {
            "current", "change_24h", "change_24h_pct",
            "high_30d", "low_30d", "avg_30d",
        }

    # ── missing required fields ───────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "current", "change_24h", "change_24h_pct", "high_30d", "low_30d", "avg_30d",
    ])
    def test_missing_field_raises(self, missing_field):
        """Each field is required — omitting any one raises ValidationError."""
        kwargs = self._valid_kwargs()
        del kwargs[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            FXSummary(**kwargs)
        assert missing_field in str(exc_info.value)

    # ── invalid types ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("bad_field", ["current", "high_30d", "low_30d"])
    def test_string_value_raises(self, bad_field):
        """Non-numeric string for any float field → ValidationError."""
        kwargs = self._valid_kwargs()
        kwargs[bad_field] = "not-a-number"
        with pytest.raises(ValidationError):
            FXSummary(**kwargs)
