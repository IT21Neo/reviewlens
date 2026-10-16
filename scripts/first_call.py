"""Step 1 of the proxy milestone: one minimal chat request to the course proxy.

Run from the repo root:   python -m scripts.first_call
"""
import sys

from app.config import ConfigError
from app.llm_client import chat, get_model

try:
    resp = chat([{"role": "user", "content": "Reply with exactly: PROXY OK"}], max_tokens=20)
except ConfigError as e:
    sys.exit(f"Config problem: {e}")
except Exception as e:
    sys.exit(f"Request failed: {type(e).__name__}: {e}")

print("model requested :", get_model())
print("model reported  :", resp.model)
print("reply           :", repr(resp.choices[0].message.content))
print("usage           :", resp.usage)