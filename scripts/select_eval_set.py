"""Milestone 4a — choose which reviews get hand labels (deterministic).

Picks, with a fixed seed and balanced by star rating:
  - dev  : 2 reviews per rating = 10   (may be used to adjust prompts)
  - test : 6 reviews per rating = 30   (held out for the final measurement)

Writes data/eval/to_label.csv for annotation. The star rating is deliberately NOT
written to that file (see docs/annotation_guideline.md). The file is UTF-8 with BOM so
Excel shows Thai correctly.

Run from the repo root:   python -m scripts.select_eval_set
Refuses to overwrite an existing to_label.csv (so labels are never lost); pass --force
to overwrite on purpose.
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

REVIEWS = Path("data/reviews.csv")
OUT = Path("data/eval/to_label.csv")
SEED = 2026
PER_RATING = {"dev": 2, "test": 6}
COLUMNS = ["review_id", "split", "review_text", "gold_sentiment", "gold_aspects", "gold_evidence", "notes"]


def select(rows: list[dict], seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    chosen = []
    for rating in "12345":
        pool = sorted((r for r in rows if r["rating"] == rating), key=lambda r: r["review_id"])
        picked = rng.sample(pool, sum(PER_RATING.values()))
        n_dev = PER_RATING["dev"]
        chosen += [{**r, "split": "dev"} for r in picked[:n_dev]]
        chosen += [{**r, "split": "test"} for r in picked[n_dev:]]
    # shuffle so rows are not grouped by rating (that would hint at the hidden stars)
    rng.shuffle(chosen)
    chosen.sort(key=lambda r: r["split"])  # stable: dev block first, order inside stays shuffled
    return chosen


def main(argv: list[str]) -> int:
    if OUT.exists() and "--force" not in argv:
        sys.exit(f"{OUT} already exists — not overwriting your labels. Use --force to replace it.")
    with open(REVIEWS, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    chosen = select(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in chosen:
            w.writerow({"review_id": r["review_id"], "split": r["split"], "review_text": r["review_text"],
                        "gold_sentiment": "", "gold_aspects": "", "gold_evidence": "", "notes": ""})
    counts = {s: sum(r["split"] == s for r in chosen) for s in PER_RATING}
    print(f"wrote {len(chosen)} rows to {OUT}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
