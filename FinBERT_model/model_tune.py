"""
End-to-end pipeline: data collection → labeling → training → saved model.

Steps:
  1. Generate synthetic labeled data        (generate_synthetic.py)
  2. Fetch real articles from freenewsapi   (fetch_news.py)
  3. Auto-label real articles via Claude    (auto_label.py)
  4. Merge all sources into training CSV    (prepare_dataset.py)
  5. Fine-tune FinBERT — frozen encoder,   (this file)
     retrain classification head only
  6. Save tuned model → model/buyer_finbert/

Usage:
    uv run python model_tune.py                        # full pipeline
    uv run python model_tune.py --skip-fetch           # skip API calls, use existing raw data
    uv run python model_tune.py --skip-data            # train only (training_dataset.csv must exist)
    uv run python model_tune.py --epochs 10 --lr 3e-4  # custom hyperparameters

Output model path:  FinBERT_model/model/buyer_finbert/
To wire into dashboard: change model="ProsusAI/finbert" → model="<abs_path>/model/buyer_finbert"
in backend/app/services/sentiment_service.py
"""

import argparse
import csv
import logging
import random
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Label mapping must match ProsusAI/finbert's original config exactly
# so the saved model is a drop-in replacement with no changes to sentiment_service.py
LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
ID2LABEL  = {0: "negative", 1: "neutral", 2: "positive"}

DATASET   = Path(__file__).parent / "data" / "training_dataset.csv"
MODEL_DIR = Path(__file__).parent / "model" / "buyer_finbert"


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class NewsDataset:
    def __init__(self, texts: list[str], label_ids: list[int], tokenizer):
        import torch
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt",
        )
        self.labels = torch.tensor(label_ids, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


def _collate(batch: list[dict]) -> dict:
    import torch
    keys = batch[0].keys()
    return {k: torch.stack([b[k] for b in batch]) for k in keys}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_csv(path: Path) -> tuple[list[str], list[int]]:
    texts, label_ids = [], []
    skipped = 0
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            text  = row.get("text", "").strip()
            label = row.get("label", "").strip().lower()
            lid   = LABEL2ID.get(label)
            if not text or lid is None:
                skipped += 1
                continue
            texts.append(text)
            label_ids.append(lid)
    if skipped:
        logger.warning(f"Skipped {skipped} rows with missing/invalid text or label")
    return texts, label_ids


def _train_val_split(
    texts: list[str],
    labels: list[int],
    val_frac: float = 0.2,
    seed: int = 42,
) -> tuple[list, list, list, list]:
    indices = list(range(len(texts)))
    random.seed(seed)
    random.shuffle(indices)
    split = int(len(indices) * (1 - val_frac))
    tr, va = indices[:split], indices[split:]
    return (
        [texts[i] for i in tr], [labels[i] for i in tr],
        [texts[i] for i in va], [labels[i] for i in va],
    )


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def run_training(epochs: int, batch_size: int, lr: float) -> None:
    import torch
    from torch.optim import AdamW
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    logger.info("=== Step 5: Fine-tuning FinBERT (frozen encoder) ===")

    if not DATASET.exists():
        raise FileNotFoundError(
            f"{DATASET} not found — run without --skip-data first"
        )

    texts, label_ids = _load_csv(DATASET)
    dist = Counter(ID2LABEL[lid] for lid in label_ids)
    logger.info(f"Dataset: {len(texts)} examples | distribution: {dict(dist)}")

    tr_texts, tr_labels, va_texts, va_labels = _train_val_split(texts, label_ids)
    logger.info(f"Train: {len(tr_texts)} | Val: {len(va_texts)}")

    logger.info("Loading ProsusAI/finbert…")
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    model = AutoModelForSequenceClassification.from_pretrained(
        "ProsusAI/finbert",
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=False,
    )

    # Freeze entire model, then unfreeze only the classification head.
    # For BertForSequenceClassification the head is model.classifier — a single
    # Linear(768, 3) layer — roughly 2,300 trainable parameters out of 110M.
    for param in model.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100 * trainable / total:.3f}%)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    model.to(device)

    from torch.utils.data import DataLoader as DL

    tr_ds = NewsDataset(tr_texts, tr_labels, tokenizer)
    va_ds = NewsDataset(va_texts, va_labels, tokenizer)
    tr_loader = DL(tr_ds, batch_size=batch_size, shuffle=True,  collate_fn=_collate)
    va_loader = DL(va_ds, batch_size=batch_size, shuffle=False, collate_fn=_collate)

    optimizer = AdamW(model.classifier.parameters(), lr=lr, weight_decay=0.01)

    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        # --- train ---
        model.train()
        epoch_loss = 0.0
        for batch in tr_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        avg_loss = epoch_loss / len(tr_loader)

        # --- validate ---
        model.eval()
        correct = 0
        per_class_correct = Counter()
        per_class_total   = Counter()
        with torch.no_grad():
            for batch in va_loader:
                batch  = {k: v.to(device) for k, v in batch.items()}
                preds  = model(**batch).logits.argmax(dim=-1)
                truths = batch["labels"]
                correct += (preds == truths).sum().item()
                for p, t in zip(preds.tolist(), truths.tolist()):
                    per_class_total[ID2LABEL[t]] += 1
                    if p == t:
                        per_class_correct[ID2LABEL[t]] += 1

        val_acc = correct / len(va_labels)
        per_class = {
            lbl: f"{per_class_correct[lbl]}/{per_class_total[lbl]}"
            for lbl in ("negative", "neutral", "positive")
        }
        flag = " ✓ best" if val_acc > best_val_acc else ""
        logger.info(
            f"Epoch {epoch}/{epochs} — loss: {avg_loss:.4f} | "
            f"val_acc: {val_acc:.3f}{flag} | per-class: {per_class}"
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    logger.info(f"=== Model saved → {MODEL_DIR} ===")
    logger.info(
        f"To use in dashboard, set model='ProsusAI/finbert' → "
        f"model=r'{MODEL_DIR.resolve()}' in sentiment_service.py"
    )


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def main(
    skip_fetch:    bool,
    skip_data:     bool,
    relabel:       bool,
    epochs:        int,
    batch_size:    int,
    lr:            float,
    max_per_topic: int,
) -> None:
    if not skip_data:
        from generate_synthetic import main as gen_synthetic
        from prepare_dataset import main as prep_dataset

        logger.info("=== Step 1: Generate synthetic labeled data ===")
        gen_synthetic()

        from auto_label import main as auto_label

        if not skip_fetch:
            from fetch_news import main as fetch_news
            logger.info("=== Step 2: Fetch real articles from freenewsapi.io ===")
            raw_path = fetch_news(max_per_topic=max_per_topic)
        else:
            raw_path = None  # auto_label will find the latest existing raw file
            logger.info("Skipping fetch — re-labeling existing raw data with Sonnet")

        if relabel:
            real_csv = Path(__file__).parent / "data" / "labeled" / "real_labeled.csv"
            if real_csv.exists():
                real_csv.unlink()
                logger.info("--relabel: deleted real_labeled.csv — all articles will be re-labeled")

        logger.info("=== Step 3: Auto-label real articles via Claude ===")
        auto_label(input_path=raw_path)  # input_path=None → picks latest articles_*.json

        logger.info("=== Step 4: Merge all sources → training_dataset.csv ===")
        prep_dataset(include_synthetic=True, include_real=True)

    run_training(epochs=epochs, batch_size=batch_size, lr=lr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Full FinBERT buyer-perspective fine-tuning pipeline"
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip freenewsapi fetch + Claude labeling; use existing labeled CSVs",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Skip all data steps; train directly from existing training_dataset.csv",
    )
    parser.add_argument("--relabel",       action="store_true", help="Delete real_labeled.csv before labeling — forces full re-label with current model")
    parser.add_argument("--epochs",        type=int,   default=5,    help="Training epochs (default: 5)")
    parser.add_argument("--batch-size",    type=int,   default=16,   help="Batch size (default: 16)")
    parser.add_argument("--lr",            type=float, default=2e-4, help="Learning rate (default: 2e-4)")
    parser.add_argument("--max-per-topic", type=int,   default=50,   help="Max articles per topic to fetch (default: 50)")
    args = parser.parse_args()

    main(
        skip_fetch=args.skip_fetch,
        skip_data=args.skip_data,
        relabel=args.relabel,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_per_topic=args.max_per_topic,
    )
