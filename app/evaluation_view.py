"""Builds the data for the Evaluation page from files that the eval scripts already wrote.

Nothing here is computed by hand or hard-coded: the metric table comes from
results/evaluation_test.json (scripts/run_eval.py), the per-review successes and failures
come from comparing data/eval/gold_labels.jsonl with the saved llm_v2 test predictions,
and the agent rows come from results/agent_eval_v2.json (or agent_eval.json).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

RESULTS = Path("results")
GOLD = Path("data/eval/gold_labels.jsonl")
REVIEWS = Path("data/reviews.csv")
METHODS = ["majority", "rating", "keyword", "llm_v1", "llm_v2"]


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def metric_table(split: str = "test") -> dict:
    path = RESULTS / f"evaluation_{split}.json"
    if not path.exists():
        return {"available": False, "file": str(path)}
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for name in METHODS:
        m = d["methods"].get(name)
        if not m:
            continue
        rows.append({"method": name,
                     "sentiment_accuracy": m["sentiment"]["accuracy"],
                     "sentiment_macro_f1": m["sentiment"]["macro_f1"],
                     "aspect_micro_f1": (m.get("aspects") or {}).get("micro_f1"),
                     "evidence_validity": (m.get("evidence") or {}).get("validity"),
                     "failed_or_missing": len(m.get("failed", [])) + len(m.get("missing", []))})
    return {"available": True, "file": str(path), "split": d["split"], "n": d["n"],
            "generated": d.get("generated"), "rows": rows}


def review_cases(prediction: str = "llm_v2", split: str = "test") -> list[dict]:
    """Per-review comparison of gold labels and one method's predictions."""
    gold = [g for g in _jsonl(GOLD) if g["split"] == split]
    preds = {p["review_id"]: p for p in _jsonl(RESULTS / "predictions" / f"{prediction}_{split}.jsonl")}
    with open(REVIEWS, encoding="utf-8", newline="") as f:
        texts = {r["review_id"]: r for r in csv.DictReader(f)}
    cases = []
    for g in gold:
        p = preds.get(g["review_id"], {})
        ok = p.get("status") in ("ok", "retried_ok")
        gold_a, pred_a = set(g["gold_aspects"]), set(p.get("aspects") or []) if ok else set()
        cases.append({
            "review_id": g["review_id"], "text": texts[g["review_id"]]["review_text"],
            "rating": int(texts[g["review_id"]]["rating"]),
            "gold_sentiment": g["gold_sentiment"], "pred_sentiment": p.get("sentiment") if ok else None,
            "gold_aspects": sorted(gold_a), "pred_aspects": sorted(pred_a),
            "missed_aspects": sorted(gold_a - pred_a), "extra_aspects": sorted(pred_a - gold_a),
            "evidence": p.get("evidence", []), "evidence_verified": p.get("evidence_verified", []),
            "status": p.get("status", "missing"),
            "sentiment_correct": ok and p.get("sentiment") == g["gold_sentiment"],
            "aspects_exact": ok and gold_a == pred_a,
        })
    for c in cases:
        c["all_correct"] = c["sentiment_correct"] and c["aspects_exact"] and all(c["evidence_verified"] or [True])
    return cases


def agent_rows() -> dict:
    for name in ("agent_eval_v2.json", "agent_eval.json"):
        path = RESULTS / name
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            return {"available": True, "file": str(path),
                    "summary": {k: {"score": v[0], "n": v[1]} for k, v in d["summary"].items()},
                    "rows": [{k: r.get(k) for k in ("id", "question", "type", "tools_called", "tool_choice",
                                                   "args_exact", "answer_ok", "stopped_by", "forced_retry", "answer")}
                             for r in d["rows"]]}
    return {"available": False}


def evaluation_payload() -> dict:
    cases = review_cases()
    return {"metrics": metric_table("test"),
            "cases": {"method": "llm_v2", "split": "test", "n": len(cases),
                      "all_correct": sum(c["all_correct"] for c in cases),
                      "failures": [c for c in cases if not c["all_correct"]],
                      "successes": [c for c in cases if c["all_correct"]]},
            "agent": agent_rows()}
