"""Offline tests: no network and no real key needed."""
import pytest

from app import config


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    # make sure a developer's real .env never leaks into these tests
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: None)


def test_missing_settings_give_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    with pytest.raises(config.ConfigError) as e:
        config.get_settings()
    assert "OPENAI_API_KEY" in str(e.value) and "OPENAI_BASE_URL" in str(e.value)


def test_placeholder_values_are_rejected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "replace_me")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    with pytest.raises(config.ConfigError, match="OPENAI_API_KEY"):
        config.get_settings()


def test_settings_read_from_env_with_default_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1/")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    s = config.get_settings()
    assert s.model == "gemma-4-E4B-it"
    assert s.base_url == "https://example.invalid/v1"


def test_env_example_contains_no_secret():
    text = open(".env.example", encoding="utf-8").read()
    assert "sk-" not in text
    assert "OPENAI_API_KEY=replace_me" in text


def test_dotenv_is_gitignored():
    assert ".env" in open(".gitignore", encoding="utf-8").read().splitlines()