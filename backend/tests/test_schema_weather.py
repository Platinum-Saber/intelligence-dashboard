"""
Unit tests for app/schemas/weather.py — WeatherReadingOut and WeatherLatest.
Covers valid construction, ORM mode, every optional field, required-field
validation errors, and type-coercion/rejection.
"""
import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.schemas.weather import WeatherReadingOut, WeatherLatest


# ═══════════════════════════════════════════════════════════════════════════════
# WeatherReadingOut
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeatherReadingOut:
    """Tests for the WeatherReadingOut response schema."""

    _TS = datetime(2026, 5, 14, 6, 0, 0, tzinfo=UTC)

    def _full_kwargs(self) -> dict:
        return {
            "id": 1,
            "timestamp": self._TS,
            "location_type": "sri_lanka_district",
            "location_name": "Colombo",
            "rainfall_mm": 25.5,
            "flood_risk": "MEDIUM",
            "drought_risk": "LOW",
            "temperature_c": 28.3,
            "source": "DMC",
        }

    # ── valid construction ────────────────────────────────────────────────────

    def test_valid_full(self):
        """All fields provided → model instantiates correctly."""
        obj = WeatherReadingOut(**self._full_kwargs())
        assert obj.id == 1
        assert obj.location_name == "Colombo"
        assert obj.rainfall_mm == 25.5
        assert obj.flood_risk == "MEDIUM"
        assert obj.drought_risk == "LOW"
        assert obj.temperature_c == 28.3
        assert obj.source == "DMC"

    def test_nullable_fields_accept_none(self):
        """All nullable fields accept explicit None."""
        obj = WeatherReadingOut(
            id=2, timestamp=self._TS,
            location_type="supplier_port", location_name="Singapore",
            rainfall_mm=None, flood_risk=None, drought_risk=None,
            temperature_c=None, source=None,
        )
        assert obj.rainfall_mm is None
        assert obj.flood_risk is None
        assert obj.drought_risk is None
        assert obj.temperature_c is None
        assert obj.source is None

    # ── each optional field individually ─────────────────────────────────────

    def test_rainfall_mm_none(self):
        obj = WeatherReadingOut(**{**self._full_kwargs(), "rainfall_mm": None})
        assert obj.rainfall_mm is None

    def test_flood_risk_none(self):
        obj = WeatherReadingOut(**{**self._full_kwargs(), "flood_risk": None})
        assert obj.flood_risk is None

    def test_drought_risk_none(self):
        obj = WeatherReadingOut(**{**self._full_kwargs(), "drought_risk": None})
        assert obj.drought_risk is None

    def test_temperature_c_none(self):
        obj = WeatherReadingOut(**{**self._full_kwargs(), "temperature_c": None})
        assert obj.temperature_c is None

    def test_source_none(self):
        obj = WeatherReadingOut(**{**self._full_kwargs(), "source": None})
        assert obj.source is None

    def test_rainfall_zero_accepted(self):
        """rainfall_mm=0.0 is valid (no rain)."""
        obj = WeatherReadingOut(**{**self._full_kwargs(), "rainfall_mm": 0.0})
        assert obj.rainfall_mm == 0.0

    def test_temperature_negative_accepted(self):
        """Negative temperature_c is a valid reading."""
        obj = WeatherReadingOut(**{**self._full_kwargs(), "temperature_c": -5.0})
        assert obj.temperature_c == -5.0

    def test_numeric_coercion_to_float(self):
        """Integer rainfall_mm and temperature_c are coerced to float."""
        obj = WeatherReadingOut(**{**self._full_kwargs(), "rainfall_mm": 10, "temperature_c": 25})
        assert isinstance(obj.rainfall_mm, float)
        assert isinstance(obj.temperature_c, float)

    # ── ORM mode ─────────────────────────────────────────────────────────────

    def test_from_orm_full(self):
        """model_validate on an ORM-like object works (from_attributes=True)."""
        orm_obj = MagicMock()
        orm_obj.id = 10
        orm_obj.timestamp = self._TS
        orm_obj.location_type = "supplier_port"
        orm_obj.location_name = "Rotterdam"
        orm_obj.rainfall_mm = 5.0
        orm_obj.flood_risk = "LOW"
        orm_obj.drought_risk = None
        orm_obj.temperature_c = 15.0
        orm_obj.source = "OpenWeather"

        result = WeatherReadingOut.model_validate(orm_obj)

        assert result.id == 10
        assert result.location_name == "Rotterdam"
        assert result.flood_risk == "LOW"

    def test_from_orm_all_optional_none(self):
        """ORM object with all optional fields None is accepted."""
        orm_obj = MagicMock()
        orm_obj.id = 11
        orm_obj.timestamp = self._TS
        orm_obj.location_type = "sri_lanka_district"
        orm_obj.location_name = "Kandy"
        orm_obj.rainfall_mm = None
        orm_obj.flood_risk = None
        orm_obj.drought_risk = None
        orm_obj.temperature_c = None
        orm_obj.source = None

        result = WeatherReadingOut.model_validate(orm_obj)

        assert result.rainfall_mm is None
        assert result.source is None

    # ── serialisation ─────────────────────────────────────────────────────────

    def test_model_dump_contains_all_fields(self):
        """model_dump() returns a dict with all nine expected keys."""
        obj = WeatherReadingOut(**self._full_kwargs())
        d = obj.model_dump()
        expected = {
            "id", "timestamp", "location_type", "location_name",
            "rainfall_mm", "flood_risk", "drought_risk", "temperature_c", "source",
        }
        assert set(d.keys()) == expected

    # ── missing required fields ───────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "id", "timestamp", "location_type", "location_name",
    ])
    def test_missing_required_field_raises(self, missing_field):
        """Each required field raises ValidationError when omitted."""
        kwargs = self._full_kwargs()
        del kwargs[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            WeatherReadingOut(**kwargs)
        assert missing_field in str(exc_info.value)

    # ── invalid types ─────────────────────────────────────────────────────────

    def test_invalid_id_type_raises(self):
        """Non-integer id → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherReadingOut(**{**self._full_kwargs(), "id": "abc"})

    def test_invalid_timestamp_type_raises(self):
        """Non-datetime timestamp → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherReadingOut(**{**self._full_kwargs(), "timestamp": "not-a-date"})

    def test_invalid_rainfall_mm_type_raises(self):
        """Non-numeric rainfall_mm → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherReadingOut(**{**self._full_kwargs(), "rainfall_mm": "heavy"})

    def test_invalid_temperature_c_type_raises(self):
        """Non-numeric temperature_c → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherReadingOut(**{**self._full_kwargs(), "temperature_c": "hot"})


# ═══════════════════════════════════════════════════════════════════════════════
# WeatherLatest
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeatherLatest:
    """Tests for the WeatherLatest summary schema."""

    _TS = datetime(2026, 5, 14, 7, 0, 0, tzinfo=UTC)

    def _full_kwargs(self) -> dict:
        return {
            "location_name": "Colombo",
            "location_type": "sri_lanka_district",
            "timestamp": self._TS,
            "rainfall_mm": 12.0,
            "flood_risk": "HIGH",
            "drought_risk": "NONE",
            "temperature_c": 31.0,
        }

    # ── valid construction ────────────────────────────────────────────────────

    def test_valid_full(self):
        """All fields provided → model instantiates correctly."""
        obj = WeatherLatest(**self._full_kwargs())
        assert obj.location_name == "Colombo"
        assert obj.flood_risk == "HIGH"
        assert obj.rainfall_mm == 12.0
        assert obj.temperature_c == 31.0
        assert obj.drought_risk == "NONE"

    def test_nullable_fields_accept_none(self):
        """All nullable fields accept explicit None."""
        obj = WeatherLatest(
            location_name="Galle",
            location_type="sri_lanka_district",
            timestamp=self._TS,
            flood_risk="LOW",
            rainfall_mm=None,
            drought_risk=None,
            temperature_c=None,
        )
        assert obj.rainfall_mm is None
        assert obj.drought_risk is None
        assert obj.temperature_c is None

    # ── each optional field individually ─────────────────────────────────────

    def test_rainfall_mm_none(self):
        obj = WeatherLatest(**{**self._full_kwargs(), "rainfall_mm": None})
        assert obj.rainfall_mm is None

    def test_drought_risk_none(self):
        obj = WeatherLatest(**{**self._full_kwargs(), "drought_risk": None})
        assert obj.drought_risk is None

    def test_temperature_c_none(self):
        obj = WeatherLatest(**{**self._full_kwargs(), "temperature_c": None})
        assert obj.temperature_c is None

    def test_rainfall_mm_zero(self):
        """rainfall_mm=0.0 is valid."""
        obj = WeatherLatest(**{**self._full_kwargs(), "rainfall_mm": 0.0})
        assert obj.rainfall_mm == 0.0

    def test_temperature_negative(self):
        """Negative temperature_c is valid."""
        obj = WeatherLatest(**{**self._full_kwargs(), "temperature_c": -2.5})
        assert obj.temperature_c == -2.5

    def test_numeric_coercion_to_float(self):
        """Integer rainfall_mm and temperature_c are coerced to float."""
        obj = WeatherLatest(**{**self._full_kwargs(), "rainfall_mm": 8, "temperature_c": 29})
        assert isinstance(obj.rainfall_mm, float)
        assert isinstance(obj.temperature_c, float)

    # ── flood_risk is required (str, not Optional) ────────────────────────────

    def test_flood_risk_critical(self):
        """flood_risk accepts any string value including CRITICAL."""
        obj = WeatherLatest(**{**self._full_kwargs(), "flood_risk": "CRITICAL"})
        assert obj.flood_risk == "CRITICAL"

    def test_flood_risk_cannot_be_none(self):
        """flood_risk is str (not Optional) → None raises ValidationError."""
        with pytest.raises(ValidationError):
            WeatherLatest(**{**self._full_kwargs(), "flood_risk": None})

    # ── serialisation ─────────────────────────────────────────────────────────

    def test_model_dump_contains_all_fields(self):
        """model_dump() returns a dict with all seven expected keys."""
        obj = WeatherLatest(**self._full_kwargs())
        d = obj.model_dump()
        expected = {
            "location_name", "location_type", "timestamp",
            "rainfall_mm", "flood_risk", "drought_risk", "temperature_c",
        }
        assert set(d.keys()) == expected

    # ── missing required fields ───────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "location_name", "location_type", "timestamp", "flood_risk",
    ])
    def test_missing_required_field_raises(self, missing_field):
        """Each required field raises ValidationError when omitted."""
        kwargs = self._full_kwargs()
        del kwargs[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            WeatherLatest(**kwargs)
        assert missing_field in str(exc_info.value)

    # ── invalid types ─────────────────────────────────────────────────────────

    def test_invalid_timestamp_type_raises(self):
        """Non-datetime timestamp → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherLatest(**{**self._full_kwargs(), "timestamp": "not-a-date"})

    def test_invalid_rainfall_mm_type_raises(self):
        """Non-numeric rainfall_mm → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherLatest(**{**self._full_kwargs(), "rainfall_mm": "heavy"})

    def test_invalid_temperature_c_type_raises(self):
        """Non-numeric temperature_c → ValidationError."""
        with pytest.raises(ValidationError):
            WeatherLatest(**{**self._full_kwargs(), "temperature_c": "warm"})
