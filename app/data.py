"""Dataset loading + validation: reviews.csv joined with the stored LLM analyses.

The analyses come from `python -m scripts.predict_llm --prompt v2 --split all`
(results/predictions/llm_v2_all.jsonl). All statistics in the app are computed by Python
over THESE stored labels — they are LLM predictions, so they can be wrong.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.taxonomy import ASPECTS, SENTIMENTS

REVIEWS = Path("data/reviews.csv")
DEFAULT_ANALYSES = Path("results/predictions/llm_v2_all.jsonl")
REQUIRED_COLUMNS = ["review_id", "product_id", "review_text", "rating", "review_date", "source"]


@dataclass(frozen=True)
class Review:
    review_id: str
    text: str
    rating: int
    sentiment: str | None = None          # None = not analysed / analysis failed
    aspects: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()        # only snippets verified verbatim in the text


@dataclass
class Store:
    reviews: dict[str, Review]
    analyses_file: str
    failed: list[str] = field(default_factory=list)

    @property
    def analysed(self) -> list[Review]:
        return [r for r in self.reviews.values() if r.sentiment is not None]


class DataError(RuntimeError):
    pass


def load_store(reviews_path: Path = REVIEWS, analyses_path: Path | None = None) -> Store:
    analyses_path = Path(analyses_path or os.environ.get("ANALYSES_FILE", DEFAULT_ANALYSES))
    with open(reviews_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != REQUIRED_COLUMNS:
            raise DataError(f"{reviews_path} columns {reader.fieldnames} != {REQUIRED_COLUMNS}")
        raw = list(reader)
    if not analyses_path.exists():
        raise DataError(f"{analyses_path} not found — run: python -m scripts.predict_llm --prompt v2 --split all")
    with open(analyses_path, encoding="utf-8") as f:
        analyses = {d["review_id"]: d for d in (json.loads(l) for l in f if l.strip())}

    reviews, failed = {}, []
    for r in raw:
        a = analyses.get(r["review_id"])
        ok = a is not None and a.get("status") in ("ok", "retried_ok")
        if a is not None and not ok:
            failed.append(r["review_id"])
        sentiment = a["sentiment"] if ok else None
        aspects = tuple(x for x in (a.get("aspects") or []) if x in ASPECTS) if ok else ()
        if sentiment is not None and sentiment not in SENTIMENTS:
            raise DataError(f"{r['review_id']}: invalid sentiment {sentiment!r} in {analyses_path}")
        evidence = tuple(e for e, v in zip(a.get("evidence", []), a.get("evidence_verified", [])) if v) if ok else ()
        reviews[r["review_id"]] = Review(r["review_id"], r["review_text"], int(r["rating"]),
                                         sentiment, aspects, evidence)
    return Store(reviews=reviews, analyses_file=str(analyses_path), failed=failed)


@lru_cache(maxsize=1)
def get_store() -> Store:
    return load_store()
