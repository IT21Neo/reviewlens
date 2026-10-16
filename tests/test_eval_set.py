"""Offline tests for eval-set selection and gold-label validation."""
import csv
from collections import Counter

from app.taxonomy import ASPECTS, SENTIMENTS
from scripts.build_gold import validate
from scripts.select_eval_set import select


def load_reviews():
    with open("data/reviews.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_taxonomy_is_fixed():
    assert SENTIMENTS == ("positive", "neutral", "negative")
    assert ASPECTS == ("taste", "price", "service", "comfort", "portion", "other")


def test_selection_is_deterministic_balanced_and_disjoint():
    rows = load_reviews()
    a, b = select(rows), select(rows)
    assert [r["review_id"] for r in a] == [r["review_id"] for r in b]
    by_split = Counter(r["split"] for r in a)
    assert by_split == {"dev": 10, "test": 30}
    assert len({r["review_id"] for r in a}) == 40
    for split, per in (("dev", 2), ("test", 6)):
        assert Counter(r["rating"] for r in a if r["split"] == split) == {s: per for s in "12345"}


def _row(rid, text, sentiment="positive", aspects="taste", evidence=""):
    return {"review_id": rid, "split": "dev", "review_text": text, "gold_sentiment": sentiment,
            "gold_aspects": aspects, "gold_evidence": evidence, "notes": ""}


def test_validate_accepts_good_row():
    reviews = {"w001": "อร่อยมาก แต่แพงไปหน่อย"}
    gold, errors = validate([_row("w001", reviews["w001"], "positive", "price; taste", "อร่อยมาก | แพงไปหน่อย")], reviews)
    assert errors == []
    assert gold[0]["gold_aspects"] == ["taste", "price"]
    assert gold[0]["gold_evidence"] == ["อร่อยมาก", "แพงไปหน่อย"]


def test_validate_reports_every_problem():
    reviews = {"w001": "อร่อยมาก", "w002": "ร้านสะอาด"}
    rows = [
        _row("w001", "อร่อยมาก", "mixed", "taste;delivery", "ไม่อร่อย"),
        _row("w002", "ร้านสะอาด (edited)"),
        _row("w999", "x"),
    ]
    _, errors = validate(rows, reviews)
    text = "\n".join(errors)
    assert "gold_sentiment 'mixed'" in text
    assert "unknown aspect(s) ['delivery']" in text
    assert "evidence not found verbatim" in text
    assert "review_text was edited" in text
    assert "w999" in text and "not found" in text


def test_empty_aspects_allowed():
    reviews = {"w001": "ไปร้านนี้มาเมื่อวาน"}
    gold, errors = validate([_row("w001", reviews["w001"], "neutral", "")], reviews)
    assert errors == [] and gold[0]["gold_aspects"] == []
