"""Environment-based configuration.

Secrets (API key, base URL) are read from environment variables only. A local `.env`
file is loaded for convenience, but it is git-ignored and must never be committed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "gemma-4-E4B-it"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing, with a message a beginner can act on."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str


def _is_placeholder(value: str) -> bool:
    return value.strip() in {"", "replace_me"}


def get_settings() -> Settings:
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    missing = [name for name, value in (("OPENAI_API_KEY", api_key), ("OPENAI_BASE_URL", base_url))
               if _is_placeholder(value)]
    if missing:
        raise ConfigError(
            f"Missing setting(s): {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values from the course instructions."
        )
    return Settings(api_key=api_key, base_url=base_url.rstrip("/"),
                    model=os.environ.get("LLM_MODEL", DEFAULT_MODEL))