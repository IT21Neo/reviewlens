"""Pydantic models for everything the LLM returns (Family A — structured output).

The model's JSON must match ReviewAnalysis exactly:
  - sentiment must be one of app.taxonomy.SENTIMENTS,
  - every aspect must be in app.taxonomy.ASPECTS (no duplicates, no invented aspects),
  - evidence is a list of short strings.
Schema validity is NOT proof of correctness: a valid object can still be the wrong label.
Whether each evidence snippet really occurs in the review is checked separately
(verify_evidence) and measured as "evidence validity" rather than silently fixed.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.taxonomy import ASPECTS

Sentiment = Literal["positive", "neutral", "negative"]


class ReviewAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys are an error, not ignored

    sentiment: Sentiment
    aspects: list[str] = Field(default_factory=list, max_length=len(ASPECTS))
    evidence: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("sentiment", mode="before")
    @classmethod
    def _lower_sentiment(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("aspects")
    @classmethod
    def _aspects_in_taxonomy(cls, v: list[str]) -> list[str]:
        cleaned = [a.strip().lower() for a in v]
        unknown = [a for a in cleaned if a not in ASPECTS]
        if unknown:
            raise ValueError(f"unknown aspect(s) {unknown}; allowed: {list(ASPECTS)}")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate aspects")
        return [a for a in ASPECTS if a in cleaned]  # canonical order

    @field_validator("evidence")
    @classmethod
    def _short_snippets(cls, v: list[str]) -> list[str]:
        v = [s.strip() for s in v if s and s.strip()]
        if any(len(s) > 200 for s in v):
            raise ValueError("evidence snippets must be short quotes (<= 200 characters)")
        return v


def verify_evidence(review_text: str, evidence: list[str]) -> list[bool]:
    """True for each snippet that appears verbatim in the review."""
    return [s in review_text for s in evidence]
