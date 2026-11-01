"""The deploy blueprint must never contain secret values."""
from pathlib import Path


def test_render_yaml_has_no_secret_values():
    text = Path("render.yaml").read_text(encoding="utf-8")
    lines = text.splitlines()
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
        i = next(n for n, l in enumerate(lines) if key in l)
        assert lines[i + 1].strip() == "sync: false"
    assert "sk-" not in text and "nat-d" not in text
    assert "uvicorn app.main:app" in text and "$PORT" in text
