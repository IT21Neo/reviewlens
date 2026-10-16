"""Milestone 3 — build data/reviews.csv from the Wongnai review corpus (reproducible).

What it does:
  1. Downloads review_dataset.zip from the wongnai-corpus GitHub repo, pinned to one
     commit, and checks its SHA-256 so everyone gets exactly the same file.
     The zip is cached in data/raw/ (git-ignored) and is NOT committed.
  2. Reads w_review_train.csv (40,000 restaurant reviews, rating 1-5).
  3. Cleans the text, masks phone numbers, keeps reviews of 30-1,500 characters.
  4. Draws a stratified sample: SAMPLE_PER_RATING reviews for each star rating, with a
     fixed random seed, so negative reviews are not drowned out (the corpus is ~47% 4-star).
  5. Writes data/reviews.csv with the columns from the project brief.

Run from the repo root:   python -m scripts.prepare_data
Re-running gives a byte-identical data/reviews.csv.
"""
from __future__ import annotations

import csv
import hashlib
import io
import random
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

CORPUS_COMMIT = "113ad2962374fa3274eeed7e4aa74540472e3bd5"
ZIP_URL = f"https://raw.githubusercontent.com/wongnai/wongnai-corpus/{CORPUS_COMMIT}/review/review_dataset.zip"
ZIP_SHA256 = "45c3439a5f0a68f438ccfbf4403dd65af797f5ee9df5348a0ed4588cd8bea220"
MEMBER = "w_review_train.csv"

RAW_DIR = Path("data/raw")
ZIP_PATH = RAW_DIR / "review_dataset.zip"
OUT_PATH = Path("data/reviews.csv")

SEED = 42
SAMPLE_PER_RATING = 60          # 5 ratings x 60 = 300 reviews
MIN_CHARS, MAX_CHARS = 30, 1500

PHONE_RE = re.compile(r"(?<!\d)0\d{1,2}[-\s]?\d{3}[-\s]?\d{3,4}(?!\d)")
FIELDS = ["review_id", "product_id", "review_text", "rating", "review_date", "source"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and sha256(ZIP_PATH) == ZIP_SHA256:
        print(f"using cached {ZIP_PATH}")
        return
    print(f"downloading {ZIP_URL}")
    urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)
    got = sha256(ZIP_PATH)
    if got != ZIP_SHA256:
        ZIP_PATH.unlink()
        sys.exit(f"SHA-256 mismatch: expected {ZIP_SHA256}, got {got}. Not using this file.")
    print("checksum OK")


def clean(text: str) -> tuple[str, int]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return PHONE_RE.subn("[PHONE]", text)


def load_rows() -> list[dict]:
    csv.field_size_limit(10**8)
    with zipfile.ZipFile(ZIP_PATH) as z:
        raw = z.read(MEMBER).decode("utf-8")
    rows = []
    for i, rec in enumerate(csv.reader(io.StringIO(raw), delimiter=";")):
        if len(rec) != 2 or rec[1] not in {"1", "2", "3", "4", "5"}:
            continue  # skip malformed lines instead of guessing
        rows.append({"row": i, "text": rec[0], "rating": int(rec[1])})
    return rows


def main() -> int:
    download()
    rows = load_rows()
    print(f"read {len(rows)} reviews from {MEMBER}")

    masked_total, kept = 0, []
    for r in rows:
        text, n_masked = clean(r["text"])
        if MIN_CHARS <= len(text) <= MAX_CHARS:
            masked_total += n_masked
            kept.append({**r, "text": text})
    print(f"kept {len(kept)} reviews with {MIN_CHARS}-{MAX_CHARS} characters")

    rng = random.Random(SEED)
    sample = []
    for rating in range(1, 6):
        pool = [r for r in kept if r["rating"] == rating]
        if len(pool) < SAMPLE_PER_RATING:
            sys.exit(f"only {len(pool)} reviews with rating {rating}; lower SAMPLE_PER_RATING")
        sample += rng.sample(pool, SAMPLE_PER_RATING)
    sample.sort(key=lambda r: r["row"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for n, r in enumerate(sample, 1):
            w.writerow({
                "review_id": f"w{n:03d}",
                "product_id": "restaurant",   # the corpus has no restaurant identifier
                "review_text": r["text"],
                "rating": r["rating"],
                "review_date": "",            # not available in the corpus
                "source": f"wongnai-corpus@{CORPUS_COMMIT[:7]}/{MEMBER}#row={r['row']}",
            })

    masked_in_sample = sum(r["text"].count("[PHONE]") for r in sample)
    print(f"wrote {len(sample)} reviews to {OUT_PATH}")
    print("rating counts:", dict(sorted(Counter(r["rating"] for r in sample).items())))
    print(f"phone numbers masked: {masked_total} in kept reviews, {masked_in_sample} in the sample")
    print(f"sha256 of {OUT_PATH}: {sha256(OUT_PATH)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
