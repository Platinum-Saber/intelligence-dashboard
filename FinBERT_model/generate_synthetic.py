"""
Convert synthetic_data.json into a labeled training CSV.

Usage:
    python generate_synthetic.py

Output:
    data/labeled/synthetic_labeled.csv  — 200 rows, columns: text, label, topic, source
"""

import csv
import json
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SRC_JSON = Path(__file__).parent / "data" / "synthetic_data.json"
OUT_CSV  = Path(__file__).parent / "data" / "labeled" / "synthetic_labeled.csv"


def main() -> None:
    with open(SRC_JSON, encoding="utf-8") as f:
        examples: list[dict] = json.load(f)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for ex in examples:
        headline = ex["headline"].strip()
        body     = ex.get("body", "").strip()
        text     = f"{headline}. {body}".strip() if body else headline
        rows.append({
            "text":   text,
            "label":  ex["label"].lower(),
            "topic":  ex["topic"].upper(),
            "source": "synthetic",
        })

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "topic", "source"])
        writer.writeheader()
        writer.writerows(rows)

    dist = Counter(r["label"] for r in rows)
    by_topic = Counter(r["topic"] for r in rows)
    logger.info(f"Written {len(rows)} rows → {OUT_CSV}")
    logger.info(f"Label distribution : {dict(dist)}")
    logger.info(f"Topic distribution : {dict(by_topic)}")


if __name__ == "__main__":
    main()
