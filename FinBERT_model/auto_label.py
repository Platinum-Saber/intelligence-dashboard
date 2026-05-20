"""
Label raw fetched articles with buyer-perspective sentiment using the Claude API.

Reads the most recent (or a specified) articles_*.json from data/raw/,
sends each article to Claude with a procurement-buyer prompt,
and writes data/labeled/real_labeled.csv.

Usage:
    python auto_label.py
    python auto_label.py --input data/raw/articles_20260515_120000.json
    python auto_label.py --input data/raw/articles_20260515_120000.json --batch-size 20

Requires ANTHROPIC_API_KEY in .env.
"""

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR     = Path(__file__).parent / "data" / "raw"
LABELED_DIR = Path(__file__).parent / "data" / "labeled"
OUT_CSV     = LABELED_DIR / "real_labeled.csv"

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# Sonnet handles nuanced cases (miner stock news vs. commodity price news,
# near-duplicate framing differences) far more consistently than Haiku.
# Cost for 250 articles is ~$0.20 — negligible for an infrequent batch job.
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are a senior procurement buyer at ACL Cables PLC, a Sri Lankan cable manufacturer.
You import copper, aluminium, and XLPE as primary raw materials from UAE, China, Singapore, and Vietnam.
Your concern is cost, supply availability, and logistics reliability.

Classify each news article as POSITIVE, NEGATIVE, or NEUTRAL strictly from your perspective as a buyer:

POSITIVE — news that reduces your costs, improves supply availability, eases logistics,
           or reduces procurement risk. Examples: price falls, new supply sources,
           trade tariff reductions, logistics improvements, favourable FX for LKR.

NEGATIVE — news that increases your costs, threatens supply, disrupts logistics,
           or increases procurement risk. Examples: price rises, supply disruptions,
           mine strikes, port closures, tariff increases, LKR depreciation.

NEUTRAL  — informational news with no clear directional impact on cost or supply.
           Examples: policy meetings with no change, routine statistics releases,
           administrative announcements.

Rules:
- For COPPER and ALUMINIUM: rising prices are NEGATIVE (you pay more), falling prices are POSITIVE.
  Supply disruptions are NEGATIVE even if FinBERT would call them "negative" for traders.
  New supply sources are POSITIVE even if FinBERT would call them "positive" for traders.
- For FX: LKR weakening is NEGATIVE (imports cost more), LKR strengthening is POSITIVE.
- For TRADE and LOGISTICS: disruptions/tariffs are NEGATIVE, improvements/agreements are POSITIVE.

Respond with ONLY one word — exactly one of: positive  negative  neutral
No explanation, no punctuation, no extra words.\
"""


def label_article(headline: str, body: str, topic: str) -> str | None:
    """Return 'positive', 'negative', or 'neutral'. Returns None on API failure."""
    user_msg = (
        f"Topic: {topic}\n"
        f"Headline: {headline}\n"
        f"Body: {body[:400] if body else '(none)'}"
    )
    try:
        resp = CLIENT.messages.create(
            model=MODEL,
            max_tokens=5,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip().lower()
        if raw in ("positive", "negative", "neutral"):
            return raw
        # Handle cases where the model returns more than one word
        for word in ("positive", "negative", "neutral"):
            if word in raw:
                return word
        logger.warning(f"Unexpected label response: '{raw}' — skipping article")
        return None
    except Exception as e:
        logger.warning(f"Claude API call failed: {e}")
        return None


def latest_raw_file() -> Path | None:
    files = sorted(RAW_DIR.glob("articles_*.json"), reverse=True)
    return files[0] if files else None


def main(input_path: Path | None = None, batch_size: int = 50) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    if input_path is None:
        input_path = latest_raw_file()
    if input_path is None:
        raise FileNotFoundError("No articles_*.json found in data/raw/ — run fetch_news.py first")

    logger.info(f"Loading articles from {input_path}")
    with open(input_path, encoding="utf-8") as f:
        articles: list[dict] = json.load(f)

    LABELED_DIR.mkdir(parents=True, exist_ok=True)

    # Load already-labeled UUIDs to allow resuming interrupted runs.
    labeled_uuids: set[str] = set()
    existing_rows: list[dict] = []
    if OUT_CSV.exists():
        with open(OUT_CSV, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_rows.append(row)
                labeled_uuids.add(row.get("uuid", ""))
        logger.info(f"Resuming — {len(labeled_uuids)} articles already labeled")

    to_label = [a for a in articles if a.get("uuid") not in labeled_uuids]
    logger.info(f"Articles to label: {len(to_label)}")

    new_rows: list[dict] = []
    for i, article in enumerate(to_label):
        label = label_article(
            headline=article.get("headline", ""),
            body=article.get("body", ""),
            topic=article.get("topic", ""),
        )
        if label is None:
            continue

        row = {
            "uuid":     article.get("uuid", ""),
            "topic":    article.get("topic", ""),
            "headline": article.get("headline", ""),
            "text":     article.get("text", ""),
            "label":    label,
            "source":   "freenewsapi",
        }
        new_rows.append(row)

        if (i + 1) % 10 == 0:
            logger.info(f"  Labeled {i + 1}/{len(to_label)}")

        # Respect Claude API rate limits — haiku is fast but batch calls can pile up.
        time.sleep(0.3)

    all_rows = existing_rows + new_rows
    fieldnames = ["uuid", "topic", "headline", "text", "label", "source"]

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"Labeled {len(new_rows)} new articles → {OUT_CSV}")
    logger.info(f"Total in file: {len(all_rows)}")

    # Label distribution summary
    from collections import Counter
    dist = Counter(r["label"] for r in all_rows)
    logger.info(f"Label distribution: {dict(dist)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-label fetched articles with buyer-perspective sentiment")
    parser.add_argument("--input", type=Path, default=None, help="Path to articles JSON (default: latest in data/raw/)")
    parser.add_argument("--batch-size", type=int, default=50, help="Unused — kept for CLI compatibility")
    args = parser.parse_args()
    main(input_path=args.input, batch_size=args.batch_size)
