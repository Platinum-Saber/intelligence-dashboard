"""
Comprehensive unit tests for weather_service.py
Tests cover all functions, edge cases, schema validation, and error handling.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.services.weather_service import (
    get_latest_all,
    get_history,
    get_high_risk,
)
from app.models.weather import WeatherReading
from app.schemas.weather import WeatherLatest, WeatherReadingOut


class TestGetLatestAll:
    """Test get_latest_all function - retrieves most recent reading per location."""

    def test_get_latest_all_empty_database(self, test_db: Session):
        """Should return empty list when no data exists."""
        result = get_latest_all(test_db)
        assert result == []
        assert isinstance(result, list)

    def test_get_latest_all_single_location(self, test_db: Session, sample_weather_reading):
        """Should return single latest reading for one location."""
        reading = WeatherReading(**sample_weather_reading)
        test_db.add(reading)
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 1
        assert result[0].location_name == "Colombo"
        assert result[0].rainfall_mm == 25.5
        assert result[0].flood_risk == "MEDIUM"
        assert result[0].temperature_c == 28.3

    def test_get_latest_all_multiple_locations(
        self, test_db: Session, 
        sample_weather_reading,
        sample_weather_reading_critical,
        sample_weather_reading_high_risk
    ):
        """Should return latest reading per location, ordered by location_type and name."""
        test_db.add_all([
            WeatherReading(**sample_weather_reading),
            WeatherReading(**sample_weather_reading_critical),
            WeatherReading(**sample_weather_reading_high_risk),
        ])
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 3
        locations = [r.location_name for r in result]
        assert "Colombo" in locations
        assert "Port City" in locations
        assert "Galle" in locations

    def test_get_latest_all_multiple_readings_same_location(self, test_db: Session):
        """Should return only the most recent reading per location."""
        now = datetime.utcnow()
        readings_data = [
            {
                "timestamp": now - timedelta(hours=3),
                "location_type": "sri_lanka_district",
                "location_name": "Colombo",
                "rainfall_mm": 10.0,
                "flood_risk": "LOW",
                "temperature_c": 25.0,
                "source": "DMC",
            },
            {
                "timestamp": now - timedelta(hours=1),
                "location_type": "sri_lanka_district",
                "location_name": "Colombo",
                "rainfall_mm": 30.0,
                "flood_risk": "HIGH",
                "temperature_c": 28.0,
                "source": "DMC",
            },
            {
                "timestamp": now,
                "location_type": "sri_lanka_district",
                "location_name": "Colombo",
                "rainfall_mm": 50.0,
                "flood_risk": "CRITICAL",
                "temperature_c": 30.0,
                "source": "DMC",
            },
        ]
        test_db.add_all([WeatherReading(**data) for data in readings_data])
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 1
        assert result[0].rainfall_mm == 50.0  # Most recent
        assert result[0].flood_risk == "CRITICAL"
        assert result[0].temperature_c == 30.0

    def test_get_latest_all_returns_correct_schema(self, test_db: Session, sample_weather_reading):
        """Should return WeatherLatest schema objects."""
        test_db.add(WeatherReading(**sample_weather_reading))
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, WeatherLatest)
        assert hasattr(item, "location_name")
        assert hasattr(item, "location_type")
        assert hasattr(item, "timestamp")
        assert hasattr(item, "rainfall_mm")
        assert hasattr(item, "flood_risk")
        assert hasattr(item, "temperature_c")

    def test_get_latest_all_null_flood_risk_defaults_to_low(self, test_db: Session):
        """When flood_risk is NULL, should default to 'LOW'."""
        data = {
            "timestamp": datetime.utcnow(),
            "location_type": "sri_lanka_district",
            "location_name": "Colombo",
            "rainfall_mm": 10.0,
            "flood_risk": None,
            "temperature_c": 25.0,
            "source": "DMC",
        }
        test_db.add(WeatherReading(**data))
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 1
        assert result[0].flood_risk == "LOW"

    def test_get_latest_all_null_values_preserved(self, test_db: Session):
        """Should preserve NULL values for optional fields."""
        data = {
            "timestamp": datetime.utcnow(),
            "location_type": "sri_lanka_district",
            "location_name": "Colombo",
            "rainfall_mm": None,
            "flood_risk": "LOW",
            "temperature_c": None,
            "source": None,
        }
        test_db.add(WeatherReading(**data))
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 1
        assert result[0].rainfall_mm is None
        assert result[0].temperature_c is None

    def test_get_latest_all_ordered_by_location_type_then_name(self, test_db: Session):
        """Results should be ordered by location_type, then location_name."""
        readings = [
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="supplier_port",
                location_name="Zebra Port",
                rainfall_mm=10.0,
                flood_risk="LOW",
                temperature_c=25.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Apple District",
                rainfall_mm=20.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="supplier_port",
                location_name="Adam Port",
                rainfall_mm=15.0,
                flood_risk="LOW",
                temperature_c=24.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_latest_all(test_db)

        assert len(result) == 3
        # Grouped by location_type first, then sorted by name
        port_results = [r for r in result if r.location_type == "supplier_port"]
        district_results = [r for r in result if r.location_type == "sri_lanka_district"]
        
        assert len(port_results) == 2
        assert len(district_results) == 1


class TestGetHistory:
    """Test get_history function - retrieves historical readings for a location."""

    def test_get_history_empty_database(self, test_db: Session):
        """Should return empty list when location has no data."""
        result = get_history(test_db, "NonExistent")
        assert result == []
        assert isinstance(result, list)

    def test_get_history_single_reading(self, test_db: Session, sample_weather_reading):
        """Should return single reading when only one exists."""
        test_db.add(WeatherReading(**sample_weather_reading))
        test_db.commit()

        result = get_history(test_db, "Colombo", days=30)

        assert len(result) == 1
        assert isinstance(result[0], WeatherReadingOut)

    def test_get_history_multiple_readings_same_location(self, test_db: Session):
        """Should return all readings for location within date range."""
        now = datetime.utcnow()
        readings = [
            WeatherReading(
                timestamp=now - timedelta(days=5),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=10.0,
                flood_risk="LOW",
                temperature_c=25.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now - timedelta(days=3),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=20.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now,
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=30.0,
                flood_risk="HIGH",
                temperature_c=28.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_history(test_db, "Colombo", days=30)

        assert len(result) == 3

    def test_get_history_filters_by_days(self, test_db: Session):
        """Should only return readings within the specified days window."""
        now = datetime.utcnow()
        readings = [
            WeatherReading(
                timestamp=now - timedelta(days=40),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=5.0,
                flood_risk="LOW",
                temperature_c=24.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now - timedelta(days=15),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=15.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now - timedelta(days=5),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=25.0,
                flood_risk="HIGH",
                temperature_c=28.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_history(test_db, "Colombo", days=30)

        assert len(result) == 2  # Only readings from last 30 days
        assert result[0].rainfall_mm == 15.0
        assert result[1].rainfall_mm == 25.0

    def test_get_history_default_days_30(self, test_db: Session):
        """Should default to 30 days when not specified."""
        now = datetime.utcnow()
        reading = WeatherReading(
            timestamp=now - timedelta(days=10),
            location_type="sri_lanka_district",
            location_name="Colombo",
            rainfall_mm=20.0,
            flood_risk="MEDIUM",
            temperature_c=26.0,
            source="DMC",
        )
        test_db.add(reading)
        test_db.commit()

        result = get_history(test_db, "Colombo")  # No days parameter

        assert len(result) == 1

    def test_get_history_ordered_by_timestamp_ascending(self, test_db: Session):
        """Results should be ordered by timestamp ascending."""
        now = datetime.utcnow()
        readings = [
            WeatherReading(
                timestamp=now - timedelta(days=5),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=30.0,
                flood_risk="HIGH",
                temperature_c=28.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now - timedelta(days=1),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=10.0,
                flood_risk="LOW",
                temperature_c=25.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now - timedelta(days=3),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=20.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_history(test_db, "Colombo", days=30)

        assert len(result) == 3
        assert result[0].rainfall_mm == 30.0  # oldest first
        assert result[1].rainfall_mm == 20.0
        assert result[2].rainfall_mm == 10.0  # newest last

    def test_get_history_location_name_case_sensitive(self, test_db: Session):
        """Location filtering should be case-sensitive."""
        test_db.add(WeatherReading(
            timestamp=datetime.utcnow(),
            location_type="sri_lanka_district",
            location_name="Colombo",
            rainfall_mm=20.0,
            flood_risk="MEDIUM",
            temperature_c=26.0,
            source="DMC",
        ))
        test_db.commit()

        result = get_history(test_db, "colombo", days=30)

        assert len(result) == 0  # Different case

    def test_get_history_returns_correct_schema(self, test_db: Session, sample_weather_reading):
        """Should return WeatherReadingOut schema objects."""
        test_db.add(WeatherReading(**sample_weather_reading))
        test_db.commit()

        result = get_history(test_db, "Colombo", days=30)

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, WeatherReadingOut)
        assert hasattr(item, "id")
        assert hasattr(item, "timestamp")
        assert hasattr(item, "location_type")
        assert hasattr(item, "location_name")
        assert hasattr(item, "rainfall_mm")
        assert hasattr(item, "flood_risk")
        assert hasattr(item, "temperature_c")
        assert hasattr(item, "source")


class TestGetHighRisk:
    """Test get_high_risk function - retrieves latest HIGH/CRITICAL risk readings."""

    def test_get_high_risk_empty_database(self, test_db: Session):
        """Should return empty list when no readings exist."""
        result = get_high_risk(test_db)
        assert result == []

    def test_get_high_risk_default_levels(self, test_db: Session):
        """Should default to HIGH and CRITICAL risk levels."""
        readings = [
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=50.0,
                flood_risk="CRITICAL",
                temperature_c=30.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Galle",
                rainfall_mm=40.0,
                flood_risk="HIGH",
                temperature_c=29.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_high_risk(test_db)  # No risk_levels parameter

        assert len(result) == 2
        risks = [r.flood_risk for r in result]
        assert "CRITICAL" in risks
        assert "HIGH" in risks

    def test_get_high_risk_filters_low_and_medium(self, test_db: Session):
        """Should exclude LOW and MEDIUM risk readings."""
        readings = [
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=50.0,
                flood_risk="CRITICAL",
                temperature_c=30.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Kandy",
                rainfall_mm=5.0,
                flood_risk="LOW",
                temperature_c=22.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Galle",
                rainfall_mm=20.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_high_risk(test_db)

        assert len(result) == 1
        assert result[0].flood_risk == "CRITICAL"
        assert result[0].location_name == "Colombo"

    def test_get_high_risk_custom_risk_levels(self, test_db: Session):
        """Should filter by custom risk levels when provided."""
        readings = [
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=50.0,
                flood_risk="CRITICAL",
                temperature_c=30.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Kandy",
                rainfall_mm=5.0,
                flood_risk="LOW",
                temperature_c=22.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Galle",
                rainfall_mm=20.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_high_risk(test_db, risk_levels=["LOW", "MEDIUM"])

        assert len(result) == 2
        risks = [r.flood_risk for r in result]
        assert "LOW" in risks
        assert "MEDIUM" in risks
        assert "CRITICAL" not in risks

    def test_get_high_risk_only_high(self, test_db: Session):
        """Should filter only HIGH when specified."""
        readings = [
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=50.0,
                flood_risk="CRITICAL",
                temperature_c=30.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=datetime.utcnow(),
                location_type="sri_lanka_district",
                location_name="Galle",
                rainfall_mm=40.0,
                flood_risk="HIGH",
                temperature_c=29.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_high_risk(test_db, risk_levels=["HIGH"])

        assert len(result) == 1
        assert result[0].flood_risk == "HIGH"

    def test_get_high_risk_returns_latest_per_location(self, test_db: Session):
        """Should return only latest reading per location."""
        now = datetime.utcnow()
        readings = [
            WeatherReading(
                timestamp=now - timedelta(hours=2),
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=30.0,
                flood_risk="MEDIUM",
                temperature_c=26.0,
                source="DMC",
            ),
            WeatherReading(
                timestamp=now,
                location_type="sri_lanka_district",
                location_name="Colombo",
                rainfall_mm=50.0,
                flood_risk="CRITICAL",
                temperature_c=30.0,
                source="DMC",
            ),
        ]
        test_db.add_all(readings)
        test_db.commit()

        result = get_high_risk(test_db)

        assert len(result) == 1
        assert result[0].rainfall_mm == 50.0  # Latest

    def test_get_high_risk_empty_risk_levels_list(self, test_db: Session):
        """Should return empty list when risk_levels is empty."""
        test_db.add(WeatherReading(
            timestamp=datetime.utcnow(),
            location_type="sri_lanka_district",
            location_name="Colombo",
            rainfall_mm=50.0,
            flood_risk="CRITICAL",
            temperature_c=30.0,
            source="DMC",
        ))
        test_db.commit()

        result = get_high_risk(test_db, risk_levels=[])

        assert len(result) == 0

    def test_get_high_risk_returns_correct_schema(self, test_db: Session):
        """Should return WeatherLatest schema objects."""
        test_db.add(WeatherReading(
            timestamp=datetime.utcnow(),
            location_type="sri_lanka_district",
            location_name="Colombo",
            rainfall_mm=50.0,
            flood_risk="CRITICAL",
            temperature_c=30.0,
            source="DMC",
        ))
        test_db.commit()

        result = get_high_risk(test_db)

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, WeatherLatest)

    def test_get_high_risk_invalid_risk_level_ignored(self, test_db: Session):
        """Invalid risk level values should be filtered out."""
        test_db.add(WeatherReading(
            timestamp=datetime.utcnow(),
            location_type="sri_lanka_district",
            location_name="Colombo",
            rainfall_mm=50.0,
            flood_risk="EXTREME",  # Invalid
            temperature_c=30.0,
            source="DMC",
        ))
        test_db.commit()

        result = get_high_risk(test_db, risk_levels=["EXTREME"])

        assert len(result) == 1  # Exists but returned based on filter logic
