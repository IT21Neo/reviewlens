"""Evaluation metrics (pure Python, no extra libraries) — unit-tested in tests/test_metrics.py.

Sentiment (single label, 3 classes): accuracy, per-class precision/recall/F1, macro F1,
and a confusion matrix.
Aspects (multi-label): micro precision/recall/F1 over all (review, aspect) pairs, plus
per-aspect precision/recall/F1 and support.
Evidence validity: share of predicted evidence snippets found verbatim in the review.
"""
from __future__ import annotations

from app.taxonomy import ASPECTS, SENTIMENTS


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def sentiment_metrics(gold: list[str], pred: list[str]) -> dict:
    assert len(gold) == len(pred)
    n = len(gold)
    accuracy = sum(g == p for g, p in zip(gold, pred)) / n if n else 0.0
    per_class, f1s = {}, []
    for c in SENTIMENTS:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        p_, r_, f_ = _prf(tp, fp, fn)
        per_class[c] = {"precision": p_, "recall": r_, "f1": f_, "support": tp + fn}
        f1s.append(f_)
    confusion = {g: {p: sum(x == g and y == p for x, y in zip(gold, pred)) for p in SENTIMENTS}
                 for g in SENTIMENTS}
    return {"n": n, "accuracy": accuracy, "macro_f1": sum(f1s) / len(f1s),
            "per_class": per_class, "confusion": confusion}


def aspect_metrics(gold: list[set[str]], pred: list[set[str]]) -> dict:
    assert len(gold) == len(pred)
    per_aspect = {}
    TP = FP = FN = 0
    for a in ASPECTS:
        tp = sum(a in g and a in p for g, p in zip(gold, pred))
        fp = sum(a not in g and a in p for g, p in zip(gold, pred))
        fn = sum(a in g and a not in p for g, p in zip(gold, pred))
        p_, r_, f_ = _prf(tp, fp, fn)
        per_aspect[a] = {"precision": p_, "recall": r_, "f1": f_, "support": tp + fn}
        TP, FP, FN = TP + tp, FP + fp, FN + fn
    p, r, f = _prf(TP, FP, FN)
    exact = sum(g == p_ for g, p_ in zip(gold, pred)) / len(gold) if gold else 0.0
    return {"micro_precision": p, "micro_recall": r, "micro_f1": f, "exact_set_match": exact,
            "per_aspect": per_aspect}


def evidence_validity(texts: list[str], evidence: list[list[str]]) -> dict:
    snippets = [(t, e) for t, ev in zip(texts, evidence) for e in ev]
    found = sum(e in t for t, e in snippets)
    return {"snippets": len(snippets), "verbatim": found,
            "validity": found / len(snippets) if snippets else None}
