"""
Fetch financial news articles from freenewsapi.io for FinBERT training data.

Free tier limits: 5,000 req/day, 2 req/sec.
Each topic runs multiple keyword queries; articles are deduplicated by UUID.
Body text is fetched via /v1/details (separate request per article).

Usage:
    pip install -r requirements.txt
    cp .env.example .env  # fill in FREENEWSAPI_KEY
    python fetch_news.py
    python fetch_news.py --max-per-topic 30  # smaller batch

Output:
    data/raw/articles_YYYYMMDD_HHMMSS.json
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_KEY  = os.getenv("FREENEWSAPI_KEY", "")
BASE_URL = "https://api.freenewsapi.io/v1"
RAW_DIR  = Path(__file__).parent / "data" / "raw"

# Per-topic keyword queries — multiple queries cover more article variety.
# Each query uses in_title (headline match) which is the most precise signal.
TOPIC_QUERIES: dict[str, list[str]] = {
    "COPPER": [
        "copper price",
        "LME copper",
        "copper supply",
        "copper mine",
        "copper market",
    ],
    "ALUMINIUM": [
        "aluminium price",
        "aluminum market",
        "LME aluminium",
        "aluminium supply",
    ],
    "FX": [
        "rupee exchange",
        "Sri Lanka rupee",
        "LKR dollar",
        "Sri Lanka currency",
    ],
    "TRADE": [
        "supply chain disruption",
        "trade tariff metals",
        "shipping freight",
        "import restrictions commodities",
    ],
    "LOGISTICS": [
        "port congestion",
        "shipping delay",
        "freight disruption",
        "logistics disruption",
    ],
}

HEADERS = {"x-api-key": API_KEY}
REQUEST_DELAY = 0.6  # seconds between requests — stays well under 2 req/sec


def _get(url: str, params: dict) -> dict | None:
    try:
        resp = httpx.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} for {url} params={params}")
    except Exception as e:
        logger.warning(f"Request failed: {e}")
    return None


def fetch_uuids(query: str, max_results: int) -> list[str]:
    """Return up to max_results article UUIDs matching the in_title query."""
    uuids: list[str] = []
    offset = 0
    page_size = 10

    while len(uuids) < max_results:
        data = _get(
            f"{BASE_URL}/news",
            {"in_title": query, "language": "en", "page_size": page_size, "offset": offset},
        )
        time.sleep(REQUEST_DELAY)
        if not data:
            break

        articles = data.get("data", [])
        for a in articles:
            if a.get("uuid"):
                uuids.append(a["uuid"])

        meta = data.get("meta", {})
        if not meta.get("has_more", False) or not articles:
            break
        offset = meta.get("next_offset", offset + page_size)

    return uuids[:max_results]


def fetch_details(uuid: str) -> dict | None:
    """Fetch full article (title + body) by UUID via /v1/details."""
    data = _get(f"{BASE_URL}/details", {"uuid": uuid})
    time.sleep(REQUEST_DELAY)
    if not data:
        return None
    return data.get("data")  # response wraps payload under "data"


def build_article(uuid: str, topic: str, details: dict) -> dict | None:
    """Convert a raw /v1/details response into a clean training record."""
    title = (details.get("title") or "").strip()
    if not title:
        return None

    # "body" has full text; "incipit" is a short excerpt used as fallback
    body = (details.get("body") or details.get("incipit") or "").strip()
    text = f"{title}. {body[:400]}".strip()

    publisher = details.get("publisher", "")
    source = publisher if isinstance(publisher, str) else publisher.get("name", "")

    return {
        "uuid":         uuid,
        "topic":        topic,
        "headline":     title,
        "body":         body[:1000],
        "text":         text,     # field used directly by the training pipeline
        "published_at": details.get("published_at", ""),
        "source":       source,
        "url":          details.get("original_url", ""),
        "label":        None,     # populated by auto_label.py
    }


def main(max_per_topic: int = 50) -> Path:
    if not API_KEY:
        raise RuntimeError("FREENEWSAPI_KEY not set — copy .env.example to .env and fill in the key")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_articles: list[dict] = []
    seen_uuids: set[str] = set()

    for topic, queries in TOPIC_QUERIES.items():
        logger.info(f"=== Topic: {topic} (target: {max_per_topic} articles) ===")
        topic_articles: list[dict] = []

        for query in queries:
            remaining = max_per_topic - len(topic_articles)
            if remaining <= 0:
                break

            logger.info(f"  Query: '{query}'")
            uuids = fetch_uuids(query, max_results=remaining)
            logger.info(f"  Got {len(uuids)} UUIDs")

            for uuid in uuids:
                if uuid in seen_uuids:
                    continue
                seen_uuids.add(uuid)

                details = fetch_details(uuid)
                if not details:
                    continue

                article = build_article(uuid, topic, details)
                if article:
                    topic_articles.append(article)

        logger.info(f"  Collected {len(topic_articles)} articles for {topic}")
        all_articles.extend(topic_articles)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = RAW_DIR / f"articles_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(all_articles)} articles → {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch training articles from freenewsapi.io")
    parser.add_argument(
        "--max-per-topic",
        type=int,
        default=50,
        help="Maximum articles to collect per topic (default: 50, total: ~250)",
    )
    args = parser.parse_args()
    main(max_per_topic=args.max_per_topic)
