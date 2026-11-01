"""Milestone 5 — score methods against the gold labels and save the results.

Methods built in (no LLM, no network):
  majority  most frequent sentiment in the DEV gold labels; no aspects
  rating    star rating -> sentiment (4-5 pos, 3 neu, 1-2 neg); no aspects
  keyword   Thai keyword lexicon (app/baseline.py)

LLM methods (later milestones) are added with --pred NAME=path/to/predictions.jsonl, one
JSON object per line: {"review_id", "sentiment", "aspects": [...], "evidence": [...]}.

Run from the repo root:
    python -m scripts.run_eval                 # test split (the reported numbers)
    python -m scripts.run_eval --split dev     # dev split (allowed while developing)

Writes results/evaluation_<split>.json, results/evaluation_<split>.md and the baseline
predictions in results/predictions/. Every number in the report must come from these files.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from app import baseline
from app.metrics import aspect_metrics, evidence_validity, sentiment_metrics
from app.taxonomy import ASPECTS, SENTIMENTS

REVIEWS = Path("data/reviews.csv")
GOLD = Path("data/eval/gold_labels.jsonl")
RESULTS = Path("results")
PRED_DIR = RESULTS / "predictions"


def load_gold() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_reviews() -> dict[str, dict]:
    with open(REVIEWS, encoding="utf-8", newline="") as f:
        return {r["review_id"]: r for r in csv.DictReader(f)}


def baseline_predictions(name: str, items: list[dict], reviews: dict, dev_gold: list[dict]) -> dict[str, dict]:
    if name == "majority":
        label = Counter(g["gold_sentiment"] for g in dev_gold).most_common(1)[0][0]
        return {g["review_id"]: {"sentiment": label, "aspects": None, "evidence": None} for g in items}
    if name == "rating":
        return {g["review_id"]: {"sentiment": baseline.rating_sentiment(int(reviews[g["review_id"]]["rating"])),
                                 "aspects": None, "evidence": None} for g in items}
    if name == "keyword":
        out = {}
        for g in items:
            text = reviews[g["review_id"]]["review_text"]
            out[g["review_id"]] = {"sentiment": baseline.keyword_sentiment(text),
                                   "aspects": baseline.keyword_aspects(text), "evidence": None}
        return out
    raise ValueError(f"unknown method {name}")


def load_predictions(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {r["review_id"]: r for r in rows}


def score(items: list[dict], preds: dict[str, dict], reviews: dict) -> dict:
    missing = [g["review_id"] for g in items if g["review_id"] not in preds]
    # a missing or failed prediction counts as wrong (never silently dropped)
    pred_sent = [(preds.get(g["review_id"]) or {}).get("sentiment") or "missing" for g in items]
    result = {"n": len(items), "missing": missing,
              "sentiment": sentiment_metrics([g["gold_sentiment"] for g in items], pred_sent)}
    if all((preds.get(g["review_id"]) or {}).get("aspects") is not None for g in items if g["review_id"] in preds) \
            and any((preds.get(g["review_id"]) or {}).get("aspects") is not None for g in items):
        result["aspects"] = aspect_metrics([set(g["gold_aspects"]) for g in items],
                                           [set((preds.get(g["review_id"]) or {}).get("aspects") or []) for g in items])
    if any((preds.get(g["review_id"]) or {}).get("evidence") for g in items):
        result["evidence"] = evidence_validity(
            [reviews[g["review_id"]]["review_text"] for g in items],
            [(preds.get(g["review_id"]) or {}).get("evidence") or [] for g in items])
    result["errors"] = [{"review_id": g["review_id"], "gold": g["gold_sentiment"], "pred": p}
                        for g, p in zip(items, pred_sent) if g["gold_sentiment"] != p]
    return result


def fmt(x) -> str:
    return "—" if x is None else f"{x:.3f}"


def to_markdown(split: str, n: int, results: dict, stamp: str, commit: str) -> str:
    lines = [f"# Evaluation results — {split} split (n = {n})", "",
             f"Generated {stamp} from commit `{commit}` by `python -m scripts.run_eval --split {split}`.", "",
             "| Method | Sentiment accuracy | Sentiment macro F1 | Aspect micro F1 | Evidence validity |",
             "|---|---:|---:|---:|---:|"]
    for name, r in results.items():
        lines.append(f"| {name} | {fmt(r['sentiment']['accuracy'])} | {fmt(r['sentiment']['macro_f1'])} | "
                     f"{fmt(r.get('aspects', {}).get('micro_f1'))} | {fmt(r.get('evidence', {}).get('validity'))} |")
    lines += ["", "## Per-aspect F1 (support = gold count)", "",
              "| Method | " + " | ".join(ASPECTS) + " |", "|---|" + "---:|" * len(ASPECTS)]
    for name, r in results.items():
        if "aspects" in r:
            pa = r["aspects"]["per_aspect"]
            lines.append(f"| {name} | " + " | ".join(f"{pa[a]['f1']:.2f} ({pa[a]['support']})" for a in ASPECTS) + " |")
    lines += ["", "## Sentiment confusion (rows = gold, columns = predicted)", ""]
    for name, r in results.items():
        c = r["sentiment"]["confusion"]
        lines += [f"**{name}**", "", "| gold \\ pred | " + " | ".join(SENTIMENTS) + " |", "|---|" + "---:|" * 3]
        lines += [f"| {g} | " + " | ".join(str(c[g][p]) for p in SENTIMENTS) + " |" for g in SENTIMENTS]
        lines += [""]
    lines += ["## Sentiment errors (for failure analysis)", ""]
    for name, r in results.items():
        errs = ", ".join(f"{e['review_id']} ({e['gold']}→{e['pred']})" for e in r["errors"]) or "none"
        lines.append(f"- **{name}**: {errs}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="test")
    ap.add_argument("--methods", default="majority,rating,keyword")
    ap.add_argument("--pred", action="append", default=[], metavar="NAME=PATH",
                    help="add an LLM prediction file, e.g. llm_v1=results/predictions/llm_v1_test.jsonl")
    args = ap.parse_args(argv)

    gold, reviews = load_gold(), load_reviews()
    items = [g for g in gold if g["split"] == args.split]
    dev_gold = [g for g in gold if g["split"] == "dev"]
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name in [m for m in args.methods.split(",") if m]:
        preds = baseline_predictions(name, items, reviews, dev_gold)
        with open(PRED_DIR / f"{name}_{args.split}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for rid, p in preds.items():
                f.write(json.dumps({"review_id": rid, **p}, ensure_ascii=False) + "\n")
        results[name] = score(items, preds, reviews)
    for spec in args.pred:
        name, _, path = spec.partition("=")
        results[name] = score(items, load_predictions(Path(path)), reviews)

    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {"split": args.split, "n": len(items), "generated": stamp, "commit": commit, "methods": results}
    (RESULTS / f"evaluation_{args.split}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(args.split, len(items), results, stamp, commit)
    (RESULTS / f"evaluation_{args.split}.md").write_text(md, encoding="utf-8")
    print(md.split("## Per-aspect")[0])
    print(f"saved results/evaluation_{args.split}.json and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
