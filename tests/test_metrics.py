"""Metric and baseline tests with answers worked out by hand."""
import pytest

from app import baseline
from app.metrics import aspect_metrics, evidence_validity, sentiment_metrics


def test_sentiment_metrics_by_hand():
    gold = ["positive", "positive", "negative", "neutral"]
    pred = ["positive", "negative", "negative", "positive"]
    m = sentiment_metrics(gold, pred)
    assert m["accuracy"] == 0.5
    # positive: P=1/2 R=1/2 F=0.5 · negative: P=1/2 R=1 F=2/3 · neutral: F=0
    assert m["per_class"]["negative"]["f1"] == pytest.approx(2 / 3)
    assert m["macro_f1"] == pytest.approx((0.5 + 2 / 3 + 0) / 3)
    assert m["confusion"]["positive"]["negative"] == 1


def test_aspect_micro_f1_by_hand():
    gold = [{"taste", "price"}, {"service"}]
    pred = [{"taste"}, {"service", "comfort"}]
    m = aspect_metrics(gold, pred)
    # TP=2 (taste, service), FP=1 (comfort), FN=1 (price) -> P=R=F=2/3
    assert m["micro_precision"] == pytest.approx(2 / 3)
    assert m["micro_recall"] == pytest.approx(2 / 3)
    assert m["micro_f1"] == pytest.approx(2 / 3)
    assert m["per_aspect"]["price"]["recall"] == 0 and m["per_aspect"]["price"]["support"] == 1
    assert m["exact_set_match"] == 0


def test_evidence_validity():
    m = evidence_validity(["อร่อยมาก แพงนิด"], [["อร่อยมาก", "ถูกมาก"]])
    assert (m["snippets"], m["verbatim"], m["validity"]) == (2, 1, 0.5)
    assert evidence_validity(["x"], [[]])["validity"] is None


@pytest.mark.parametrize("text, expected", [
    ("อร่อยมาก แนะนำเลย", "positive"),
    ("ไม่อร่อยเลย", "negative"),          # negation handled
    ("ราคาไม่แพง", "positive"),            # negated negative word
    ("แพงไป แต่อร่อย", "neutral"),         # one each -> tie
    ("สั่งข้าวผัดมาหนึ่งจาน", "neutral"),   # no polar words
])
def test_keyword_sentiment(text, expected):
    assert baseline.keyword_sentiment(text) == expected


def test_keyword_aspects_and_rating():
    assert baseline.keyword_aspects("ราคาแพง พนักงานสุภาพ ที่จอดรถเยอะ") == ["price", "service", "portion", "other"]
    assert [baseline.rating_sentiment(r) for r in (1, 2, 3, 4, 5)] == \
        ["negative", "negative", "neutral", "positive", "positive"]


def test_run_eval_end_to_end(tmp_path, monkeypatch):
    import json

    from scripts import run_eval

    monkeypatch.setattr(run_eval, "RESULTS", tmp_path)
    monkeypatch.setattr(run_eval, "PRED_DIR", tmp_path / "predictions")
    assert run_eval.main(["--split", "dev"]) == 0
    out = json.loads((tmp_path / "evaluation_dev.json").read_text(encoding="utf-8"))
    assert set(out["methods"]) == {"majority", "rating", "keyword"} and out["n"] == 10
    assert "aspects" in out["methods"]["keyword"] and "aspects" not in out["methods"]["rating"]
