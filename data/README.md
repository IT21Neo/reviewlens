# Data

## Source

| Item | Value |
|---|---|
| Dataset | Wongnai review dataset (restaurant reviews with 1–5 star ratings) |
| Publisher | Wongnai — https://github.com/wongnai/wongnai-corpus |
| Pinned commit | `113ad2962374fa3274eeed7e4aa74540472e3bd5` |
| File used | `review/review_dataset.zip` → `w_review_train.csv` (40,000 reviews, `;`-separated: text, rating) |
| Zip SHA-256 | `45c3439a5f0a68f438ccfbf4403dd65af797f5ee9df5348a0ed4588cd8bea220` |
| Origin noted by the publisher | Used in a Kaggle review-rating competition created by Dr. Ekapol Chuangsuwanich |
| License | GNU LGPL v3 — the license file of the `wongnai-corpus` repository, copied verbatim to `data/LICENSE-wongnai-corpus.txt` |

**License note.** The LGPL is a software license; the publisher applies it to the whole
repository, including the data. It permits copying and redistributing verbatim copies,
provided the license text is included, which is why `LICENSE-wongnai-corpus.txt` is here.
This project only redistributes a 300-review sample and states the modifications below.
This is our reading of the license, not legal advice.

## Files

| File | Committed? | What |
|---|---|---|
| `reviews.csv` | yes | 300-review working sample (see below) |
| `LICENSE-wongnai-corpus.txt` | yes | the corpus license |
| `raw/review_dataset.zip` | **no** (git-ignored) | downloaded by `scripts/prepare_data.py`, checksum-verified |

## How `reviews.csv` was made

Run `python -m scripts.prepare_data`. It is deterministic (fixed seed 42, pinned commit, checksum).

1. Line endings normalised, repeated spaces and blank lines collapsed, leading/trailing whitespace stripped.
2. Thai phone-number patterns replaced with `[PHONE]`.
3. Only reviews of 30–1,500 characters kept (very short reviews carry little to analyse; very long ones cost many tokens).
4. **Stratified sample: 60 reviews per star rating (300 total).** The original corpus is
   skewed (about 47% are 4-star and about 1% are 1-star), so a random sample would contain
   almost no negative reviews. Consequence: counts and percentages in ReviewLens describe
   *this balanced sample*, not Wongnai reviews in general.

## Schema

| Field | Value in this dataset |
|---|---|
| `review_id` | `w001` … `w300` (stable, assigned after sorting by original row) |
| `product_id` | always `restaurant` — the corpus has no restaurant or product identifier |
| `review_text` | cleaned review text (Thai, informal) |
| `rating` | 1–5 stars as given by the reviewer |
| `review_date` | empty — not available in the corpus |
| `source` | `wongnai-corpus@<commit>/w_review_train.csv#row=<original row index>` for traceability |

## Privacy and limits

- The corpus contains review text and ratings only — no usernames or reviewer IDs.
- Phone numbers are masked. Review text may still mention restaurant names, staff
  nicknames or places; we did not attempt full PII removal.
- Reviews are restaurant reviews, not product reviews, so the aspect taxonomy is adapted
  to restaurants (see the annotation guideline in Milestone 4).
- The data files inside the zip are dated 2018; prices and restaurants
  may no longer be current.
