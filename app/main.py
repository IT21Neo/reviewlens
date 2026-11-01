"""ReviewLens web API + UI (Milestone 10-11).

    uvicorn app.main:app --reload            # then open http://127.0.0.1:8000

Read-only endpoints use the cached analyses (results/predictions/llm_v2_all.jsonl), so the
dashboard, review list and Evaluation page work without calling the LLM. Only /api/analyze
and /api/ask call the proxy, and both go through the rate limiter in app/ratelimit.py.
Request and response bodies are validated with Pydantic; review text is treated as data and
the UI inserts it with textContent, never as HTML.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app import agent, analyzer, llm_client
from app.config import ConfigError
from app.data import DataError, get_store
from app.evaluation_view import evaluation_payload
from app.ratelimit import RateLimiter
from app.taxonomy import ASPECT_DESCRIPTIONS, ASPECTS, SENTIMENTS

STATIC = Path(__file__).parent / "static"
DISCLAIMER = ("Labels, counts and answers come from an LLM (gemma-4-E4B-it) and can be wrong. "
              "See the Evaluation page for how often it agreed with hand-checked labels.")
Sentiment = Literal["positive", "neutral", "negative"]
Aspect = Literal["taste", "price", "service", "comfort", "portion", "other"]

app = FastAPI(title="ReviewLens", version="1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
limiter = RateLimiter()


# ---------- request / response models ----------
class AnalyzeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=5, max_length=2000)


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=300)


class ReviewOut(BaseModel):
    review_id: str
    text: str
    rating: int
    sentiment: Optional[Sentiment]
    aspects: list[Aspect]
    evidence: list[str]


class ReviewPage(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[ReviewOut]


class AnalyzeOut(BaseModel):
    status: Literal["ok", "retried_ok", "failed"]
    sentiment: Optional[Sentiment]
    aspects: list[Aspect]
    evidence: list[str]
    evidence_verified: list[bool]
    attempts: int
    error: Optional[str]
    latency_s: float
    prompt_version: str
    model: str


class AskOut(BaseModel):
    answer: str
    stopped_by: str
    rounds: int
    forced_retry: bool
    trace: list[dict]


# ---------- helpers ----------
def _store():
    try:
        return get_store()
    except DataError as e:
        raise HTTPException(503, str(e))


def _client_ip(request: Request) -> str:
    # Hosting platforms put the real client first in X-Forwarded-For. It can be spoofed, which
    # is why the per-day global cap exists as well.
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _limit(request: Request) -> None:
    reason = limiter.check(_client_ip(request))
    if reason:
        raise HTTPException(429, reason)


def _review_out(r) -> ReviewOut:
    return ReviewOut(review_id=r.review_id, text=r.text, rating=r.rating, sentiment=r.sentiment,
                     aspects=list(r.aspects), evidence=list(r.evidence))


# ---------- pages ----------
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


# ---------- read-only API (cached analyses, no LLM call) ----------
@app.get("/health")
def health():
    store = _store()
    try:
        model, llm_configured = llm_client.get_model(), True
    except ConfigError:
        model, llm_configured = None, False
    return {"status": "ok", "reviews": len(store.reviews), "analysed": len(store.analysed),
            "failed": len(store.failed), "analyses_file": store.analyses_file,
            "model": model, "llm_configured": llm_configured, "live_limits": limiter.status()}


@app.get("/api/stats")
def stats():
    store = _store()
    rows = store.analysed
    n = len(rows)
    sent = Counter(r.sentiment for r in rows)
    by_aspect = {a: {s: sum(1 for r in rows if a in r.aspects and r.sentiment == s) for s in SENTIMENTS}
                 for a in ASPECTS}
    return {"analysed": n, "failed": len(store.failed), "disclaimer": DISCLAIMER,
            "sentiment": {s: {"count": sent[s], "percent": round(100 * sent[s] / n, 1) if n else 0}
                          for s in SENTIMENTS},
            "aspects": {a: {"count": sum(v.values()), "percent": round(100 * sum(v.values()) / n, 1) if n else 0,
                            "by_sentiment": v, "description": ASPECT_DESCRIPTIONS[a]}
                        for a, v in by_aspect.items()}}


@app.get("/api/reviews", response_model=ReviewPage)
def reviews(sentiment: Optional[Sentiment] = None, aspect: Optional[Aspect] = None,
            rating: Optional[int] = Query(None, ge=1, le=5), q: Optional[str] = Query(None, max_length=100),
            offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    rows = [r for r in sorted(_store().reviews.values(), key=lambda r: r.review_id)
            if (sentiment is None or r.sentiment == sentiment) and (aspect is None or aspect in r.aspects)
            and (rating is None or r.rating == rating) and (not q or q.lower() in r.text.lower())]
    return ReviewPage(total=len(rows), offset=offset, limit=limit,
                      items=[_review_out(r) for r in rows[offset:offset + limit]])


@app.get("/api/reviews/{review_id}", response_model=ReviewOut)
def review(review_id: str):
    r = _store().reviews.get(review_id)
    if r is None:
        raise HTTPException(404, f"no review {review_id!r}")
    return _review_out(r)


@app.get("/api/evaluation")
def evaluation():
    return evaluation_payload()


# ---------- live LLM endpoints (rate limited) ----------
@app.post("/api/analyze", response_model=AnalyzeOut)
def analyze(body: AnalyzeIn, request: Request):
    _limit(request)
    try:
        res = analyzer.analyze_review("live", body.text, version="v2")
    except ConfigError as e:
        raise HTTPException(503, f"LLM is not configured on this server: {e}")
    return AnalyzeOut(**{k: v for k, v in res.to_dict().items() if k in AnalyzeOut.model_fields})


@app.post("/api/ask", response_model=AskOut)
def ask(body: AskIn, request: Request):
    _limit(request)
    res = agent.ask(body.question, _store())
    return AskOut(answer=res.answer, stopped_by=res.stopped_by, rounds=res.rounds,
                  forced_retry=res.forced_retry, trace=res.trace)
