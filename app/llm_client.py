"""The single place where the app talks to the course LLM proxy (OpenAI Python SDK)."""
from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    s = get_settings()
    return OpenAI(api_key=s.api_key, base_url=s.base_url)


def get_model() -> str:
    return get_settings().model


def chat(messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 512, **kwargs):
    """One non-streamed chat completion. temperature=0 by default for repeatable results.
    Returns the full response object so callers can inspect content, tool_calls and usage."""
    return get_client().chat.completions.create(
        model=get_model(), messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
    )