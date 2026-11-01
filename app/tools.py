"""Allow-listed deterministic tools (Family B). Python computes every number; the LLM only
chooses which tool to call and with which (validated) arguments.

Safety:
  - only names in TOOLS can run; anything else is refused;
  - arguments are parsed from the JSON string and validated with Pydantic
    (fixed enums for sentiment/aspect, 1 <= limit <= 10, unknown keys rejected);
  - no SQL, shell, file access or code execution;
  - errors are returned to the model as data, the loop never crashes.
"""
from __future__ import annotations

import json
from typing import Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.data import Store
from app.taxonomy import ASPECTS, SENTIMENTS

Sentiment = Literal["positive", "neutral", "negative"]
Aspect = Literal["taste", "price", "service", "comfort", "portion", "other"]
MAX_LIMIT = 10


class FilterArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentiment: Optional[Sentiment] = None
    aspect: Optional[Aspect] = None


class ExampleArgs(FilterArgs):
    limit: int = Field(default=3, ge=1, le=MAX_LIMIT)


class AspectArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: Aspect


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _match(store: Store, sentiment=None, aspect=None):
    rows = [r for r in store.analysed
            if (sentiment is None or r.sentiment == sentiment) and (aspect is None or aspect in r.aspects)]
    return sorted(rows, key=lambda r: r.review_id)


def _snippet(r) -> str:
    return r.evidence[0] if r.evidence else r.text[:120]


def count_reviews(store: Store, a: FilterArgs) -> dict:
    n_total = len(store.analysed)
    n = len(_match(store, a.sentiment, a.aspect))
    return {"count": n, "out_of_analysed_reviews": n_total,
            "percent": round(100 * n / n_total, 1) if n_total else 0.0,
            "filters": a.model_dump(), "note": "counts use LLM-predicted labels, which may be wrong"}


def get_review_examples(store: Store, a: ExampleArgs) -> dict:
    rows = _match(store, a.sentiment, a.aspect)
    return {"filters": a.model_dump(exclude={"limit"}), "matching": len(rows),
            "examples": [{"review_id": r.review_id, "sentiment": r.sentiment, "aspects": list(r.aspects),
                          "snippet": _snippet(r)} for r in rows[: a.limit]]}


def aspect_summary(store: Store, a: AspectArgs) -> dict:
    rows = _match(store, None, a.aspect)
    by = {s: [r for r in rows if r.sentiment == s] for s in SENTIMENTS}
    return {"aspect": a.aspect, "mentions": len(rows), "out_of_analysed_reviews": len(store.analysed),
            "by_sentiment": {s: len(v) for s, v in by.items()},
            "examples": {s: [{"review_id": r.review_id, "snippet": _snippet(r)} for r in v[:2]]
                         for s, v in by.items()}}


def list_available_aspects(store: Store, a: NoArgs) -> dict:
    return {"aspects": list(ASPECTS), "sentiments": list(SENTIMENTS)}


TOOLS: dict[str, tuple[type[BaseModel], Callable, str]] = {
    "count_reviews": (FilterArgs, count_reviews,
                      "Count reviews, optionally filtered by sentiment and/or aspect. Use for any 'how many' question."),
    "get_review_examples": (ExampleArgs, get_review_examples,
                            f"Return example reviews (id + evidence snippet) matching optional sentiment/aspect filters. limit 1-{MAX_LIMIT}."),
    "aspect_summary": (AspectArgs, aspect_summary,
                       "For one aspect: number of mentions, split by sentiment, with example review ids."),
    "list_available_aspects": (NoArgs, list_available_aspects,
                               "List the fixed aspect and sentiment labels that can be used as filters."),
}


# Hand-written JSON schemas (simple enums, like the smoke test that passed on gemma) instead
# of Pydantic's anyOf/null output. Pydantic still validates whatever the model sends.
_SENT = {"type": "string", "enum": list(SENTIMENTS), "description": "review-level sentiment filter"}
_ASP = {"type": "string", "enum": list(ASPECTS), "description": "aspect filter"}
PARAMETERS = {
    "count_reviews": {"type": "object", "properties": {"sentiment": _SENT, "aspect": _ASP}, "required": []},
    "get_review_examples": {"type": "object", "properties": {
        "sentiment": _SENT, "aspect": _ASP,
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "description": "number of examples"}},
        "required": []},
    "aspect_summary": {"type": "object", "properties": {"aspect": _ASP}, "required": ["aspect"]},
    "list_available_aspects": {"type": "object", "properties": {}, "required": []},
}


def openai_tool_specs() -> list[dict]:
    return [{"type": "function", "function": {"name": name, "description": desc, "parameters": PARAMETERS[name]}}
            for name, (_model, _fn, desc) in TOOLS.items()]


def run_tool(store: Store, name: str, raw_args: str | dict | None) -> tuple[dict, dict | None]:
    """Validate and run one tool call. Returns (result, validated_args_or_None). Never raises."""
    if name not in TOOLS:
        return {"error": f"unknown tool {name!r}; allowed: {sorted(TOOLS)}"}, None
    model, fn, _ = TOOLS[name]
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) and raw_args.strip() else (raw_args or {})
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
        parsed = model.model_validate(args)
    except (ValueError, ValidationError) as e:
        return {"error": f"invalid arguments for {name}: {str(e)[:400]}"}, None
    try:
        return fn(store, parsed), parsed.model_dump()
    except Exception as e:  # a tool bug must not crash the agent
        return {"error": f"{type(e).__name__}: {e}"}, parsed.model_dump()
