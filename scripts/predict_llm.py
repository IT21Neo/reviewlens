"""Milestone 6 — run the LLM analyzer over a split and save predictions (calls the proxy).

    python -m scripts.predict_llm --prompt v1 --split dev     # 10 reviews
    python -m scripts.predict_llm --prompt v1 --split test    # 30 reviews
    python -m scripts.predict_llm --prompt v1 --split all     # all 300 (for the app)

Output: results/predictions/llm_<prompt>_<split>.jsonl, one line per review, including
status (ok / retried_ok / failed), the number of attempts and the raw reply.
Resumable: reviews already saved with a successful status are skipped; failed or missing
ones are (re)run. Use --force to redo everything. Then score with run_eval:

    python -m scripts.run_eval --split test --pred llm_v1=results/predictions/llm_v1_test.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from app.analyzer import PROMPTS, analyze_review
from app.config import ConfigError

REVIEWS = Path("data/reviews.csv")
GOLD = Path("data/eval/gold_labels.jsonl")
PRED_DIR = Path("results/predictions")


def select_reviews(split: str) -> list[dict]:
    with open(REVIEWS, encoding="utf-8", newline="") as f:
        reviews = list(csv.DictReader(f))
    if split == "all":
        return reviews
    with open(GOLD, encoding="utf-8") as f:
        ids = {json.loads(l)["review_id"] for l in f if l.strip() and json.loads(l)["split"] == split}
    return [r for r in reviews if r["review_id"] in ids]


def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {d["review_id"]: d for d in (json.loads(l) for l in f if l.strip())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", choices=sorted(PROMPTS), default="v1")
    ap.add_argument("--split", choices=["dev", "test", "all"], required=True)
    ap.add_argument("--force", action="store_true", help="ignore saved predictions and redo all")
    args = ap.parse_args(argv)

    out = PRED_DIR / f"llm_{args.prompt}_{args.split}.jsonl"
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    saved = {} if args.force else load_existing(out)
    rows = select_reviews(args.split)
    print(f"{len(rows)} reviews, prompt {args.prompt} -> {out}")

    try:
        for i, r in enumerate(rows, 1):
            prev = saved.get(r["review_id"])
            if prev and prev["status"] in ("ok", "retried_ok"):
                continue
            res = analyze_review(r["review_id"], r["review_text"], version=args.prompt).to_dict()
            saved[r["review_id"]] = res
            print(f"[{i:3}/{len(rows)}] {r['review_id']} {res['status']:10} {res['sentiment'] or '-':9} "
                  f"{','.join(res['aspects'])}  ({res['latency_s']}s)" + (f"  ERROR: {res['error'][:80]}" if res['error'] else ""))
            # rewrite after every review so an interruption loses nothing
            with open(out, "w", encoding="utf-8", newline="\n") as f:
                for rr in rows:
                    if rr["review_id"] in saved:
                        f.write(json.dumps(saved[rr["review_id"]], ensure_ascii=False) + "\n")
    except ConfigError as e:
        print(f"Config problem: {e}")
        return 1

    status = Counter(d["status"] for d in saved.values())
    ev = [v for d in saved.values() for v in d.get("evidence_verified", [])]
    print(f"\nstatus: {dict(status)}")
    if ev:
        print(f"evidence snippets found verbatim: {sum(ev)}/{len(ev)}")
    print(f"saved {out}")
    return 0 if status.get("failed", 0) == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
