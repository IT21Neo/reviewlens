"""API tests with FastAPI's TestClient. No proxy calls: the LLM functions are replaced."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.agent import AgentResult
from app.analyzer import AnalysisResult
from app.ratelimit import RateLimiter

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(main, "limiter", RateLimiter(per_minute=2, per_day=100, enabled=True))


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def analyze(review_id, text, *, version):
        calls.append(text)
        return AnalysisResult(review_id, "ok", "positive", ["taste"], ["อร่อย"], [True], 1, None, "{}", 0.1, version, "fake")

    def ask(question, store=None):
        calls.append(question)
        return AgentResult("According to the analysed labels, 5.", [{"round": 1, "tool": "count_reviews"}], 2, "answer")
    monkeypatch.setattr(main.analyzer, "analyze_review", analyze)
    monkeypatch.setattr(main.agent, "ask", ask)
    return calls


def test_index_and_health():
    assert "ReviewLens" in client.get("/").text
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["reviews"] == 300 and h["analysed"] + h["failed"] <= 300


def test_stats_add_up():
    s = client.get("/api/stats").json()
    assert sum(v["count"] for v in s["sentiment"].values()) == s["analysed"]
    for a in s["aspects"].values():
        assert sum(a["by_sentiment"].values()) == a["count"]
    assert "can be wrong" in s["disclaimer"]


def test_review_filters_and_validation():
    d = client.get("/api/reviews", params={"sentiment": "negative", "aspect": "service", "limit": 5}).json()
    assert len(d["items"]) <= 5
    assert all(r["sentiment"] == "negative" and "service" in r["aspects"] for r in d["items"])
    assert client.get("/api/reviews", params={"aspect": "delivery"}).status_code == 422
    assert client.get("/api/reviews", params={"limit": 1000}).status_code == 422
    assert client.get("/api/reviews/w001").json()["review_id"] == "w001"
    assert client.get("/api/reviews/nope").status_code == 404


def test_evaluation_comes_from_saved_files():
    e = client.get("/api/evaluation").json()
    assert e["metrics"]["available"] and e["cases"]["n"] == 30
    assert len(e["cases"]["failures"]) + len(e["cases"]["successes"]) == 30


def test_analyze_validates_body(fake_llm):
    assert client.post("/api/analyze", json={"text": "hi"}).status_code == 422          # too short
    assert client.post("/api/analyze", json={"text": "x" * 2001}).status_code == 422    # too long
    assert client.post("/api/analyze", json={"text": "อร่อยมาก", "sql": "x"}).status_code == 422
    assert fake_llm == []  # nothing reached the model
    r = client.post("/api/analyze", json={"text": "อร่อยมากครับ"}).json()
    assert r["sentiment"] == "positive" and "raw_reply" not in r


def test_live_calls_are_rate_limited(fake_llm):
    assert client.post("/api/ask", json={"question": "how many?"}).status_code == 200
    assert client.post("/api/ask", json={"question": "how many?"}).status_code == 200
    r = client.post("/api/ask", json={"question": "how many?"})
    assert r.status_code == 429 and "per minute" in r.json()["detail"]
    assert len(fake_llm) == 2


def test_limiter_day_cap_and_switch_off():
    t = [0.0]
    rl = RateLimiter(per_minute=10, per_day=3, enabled=True, clock=lambda: t[0])
    assert [rl.check(f"ip{i}") for i in range(3)] == [None] * 3
    assert "daily" in rl.check("ip9")
    t[0] += 86400  # next day resets
    assert rl.check("ip9") is None
    assert "switched off" in RateLimiter(enabled=False).check("x")


def test_ui_never_uses_innerhtml():
    js = Path("app/static/app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js
