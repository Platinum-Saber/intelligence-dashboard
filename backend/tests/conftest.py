"""
Shared pytest fixtures and configuration for all tests.
"""
import os
import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock, patch

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

from app.database import Base
from app.models.weather import WeatherReading
from app.models.news import NewsItem


@pytest.fixture(scope="function")
def test_db() -> Session:
    """Create a fresh in-memory database for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_weather_reading():
    """Return sample weather reading data."""
    return {
        "timestamp": datetime.now(UTC),
        "location_type": "sri_lanka_district",
        "location_name": "Colombo",
        "rainfall_mm": 25.5,
        "flood_risk": "MEDIUM",
        "temperature_c": 28.3,
        "source": "DMC",
    }


@pytest.fixture
def sample_weather_reading_critical():
    """Return critical flood risk weather data."""
    return {
        "timestamp": datetime.now(UTC) - timedelta(hours=2),
        "location_type": "supplier_port",
        "location_name": "Port City",
        "rainfall_mm": 150.0,
        "flood_risk": "CRITICAL",
        "temperature_c": 32.1,
        "source": "USGS",
    }


@pytest.fixture
def sample_weather_reading_high_risk():
    """Return high flood risk weather data."""
    return {
        "timestamp": datetime.now(UTC) - timedelta(hours=1),
        "location_type": "sri_lanka_district",
        "location_name": "Galle",
        "rainfall_mm": 80.0,
        "flood_risk": "HIGH",
        "temperature_c": 30.0,
        "source": "OpenWeather",
    }


@pytest.fixture
def sample_weather_reading_low_risk():
    """Return low risk weather data."""
    return {
        "timestamp": datetime.now(UTC),
        "location_type": "sri_lanka_district",
        "location_name": "Kandy",
        "rainfall_mm": 5.0,
        "flood_risk": "LOW",
        "temperature_c": 22.0,
        "source": "DMC",
    }


@pytest.fixture
def sample_news_item():
    """Return sample news item data."""
    return {
        "published_at": datetime.now(UTC),
        "headline": "FX Markets React to Trade Tensions",
        "summary": "Currency markets show volatility amid trade disputes.",
        "url": "https://example.com/news/fx-markets",
        "source": "Bloomberg",
        "topic": "FX",
        "relevance_score": 0.85,
        "sentiment": "NEGATIVE",
    }


@pytest.fixture
def sample_news_item_copper():
    """Return sample news item for copper topic."""
    return {
        "published_at": datetime.now(UTC) - timedelta(days=2),
        "headline": "Copper Prices Surge on Supply Concerns",
        "summary": "Global copper supply shortage drives prices higher.",
        "url": "https://example.com/news/copper",
        "source": "Reuters",
        "topic": "COPPER",
        "relevance_score": 0.92,
        "sentiment": "POSITIVE",
    }


@pytest.fixture
def sample_news_item_no_sentiment():
    """Return sample news item without sentiment."""
    return {
        "published_at": datetime.now(UTC) - timedelta(days=1),
        "headline": "Logistics Sector Faces New Challenges",
        "summary": "Industry grapples with operational complexities.",
        "url": "https://example.com/news/logistics",
        "source": "TradingView",
        "topic": "LOGISTICS",
        "relevance_score": 0.75,
        "sentiment": None,
    }


@pytest.fixture
def sample_news_item_invalid_topic():
    """Return news item with invalid topic (should be filtered)."""
    return {
        "published_at": datetime.now(UTC),
        "headline": "Random Market News",
        "summary": "Not relevant to tracked topics.",
        "url": "https://example.com/news/random",
        "source": "Unknown",
        "topic": "STOCKS",  # Not in VALID_TOPICS
        "relevance_score": 0.5,
        "sentiment": "NEUTRAL",
    }


@pytest.fixture
def mock_sentiment_pipeline():
    """Return a mock sentiment analysis pipeline."""
    mock_pipe = MagicMock()
    mock_pipe.return_value = [
        {"label": "positive", "score": 0.95}
    ]
    return mock_pipe


@pytest.fixture
def mock_settings_sentiment_enabled():
    """Mock settings with sentiment enabled."""
    with patch("app.services.sentiment_service.settings") as mock_settings:
        mock_settings.sentiment_enabled = True
        yield mock_settings


@pytest.fixture
def mock_settings_sentiment_disabled():
    """Mock settings with sentiment disabled."""
    with patch("app.services.sentiment_service.settings") as mock_settings:
        mock_settings.sentiment_enabled = False
        yield mock_settings
