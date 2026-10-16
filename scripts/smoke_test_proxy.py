"""Verify what the course LLM proxy actually supports BEFORE building on it.

Checks (each one is recorded, nothing is assumed):
  1. settings      — OPENAI_API_KEY / OPENAI_BASE_URL are set (the key is never printed)
  2. basic_chat    — one chat completion with gemma-4-E4B-it at temperature=0
  3. repeatability — the same prompt twice at temperature=0: identical text?
  4. json_prompt   — asked for JSON in the prompt: does json.loads() succeed on the reply?
  5. tool_calling  — tools=[...] passed: does the model return a real `tool_calls` entry
                     with JSON arguments? (decides how the agent loop is built)

Run from the repo root:   python -m scripts.smoke_test_proxy
Output: a printed summary + results/smoke_test.json (evidence for the report).
"""
from __future__ import annotations

import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

import openai

from app.config import ConfigError, get_settings
from app.llm_client import chat

RESULTS = Path("results/smoke_test.json")

COUNT_TOOL = {
    "type": "function",
    "function": {
        "name": "count_reviews",
        "description": "Count reviews in the dataset, optionally filtered by sentiment and aspect.",
        "parameters": {
            "type": "object",
            "properties": {
                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                "aspect": {"type": "string", "enum": ["quality", "price", "delivery", "packaging",
                                                      "customer_service", "usability", "other"]},
            },
            "required": [],
        },
    },
}


def timed(fn):
    t0 = time.time()
    out = fn()
    return out, round(time.time() - t0, 2)


def check_basic_chat() -> dict:
    resp, secs = timed(lambda: chat([{"role": "user", "content": "Reply with exactly: PROXY OK"}], max_tokens=20))
    text = resp.choices[0].message.content or ""
    return {"pass": bool(text.strip()), "reply": text, "model_reported": resp.model,
            "usage": resp.usage.model_dump() if resp.usage else None, "latency_s": secs}


def check_repeatability() -> dict:
    msgs = [{"role": "user", "content": "In one short sentence, what is a product review?"}]
    a = chat(msgs, max_tokens=60).choices[0].message.content
    b = chat(msgs, max_tokens=60).choices[0].message.content
    return {"pass": a == b, "identical": a == b, "reply_1": a, "reply_2": b}


def check_json_prompt() -> dict:
    prompt = ('Classify the sentiment of this review: "The box arrived crushed and support never replied."\n'
              'Reply with ONLY a JSON object like {"sentiment": "positive|neutral|negative"} and nothing else.')
    text = chat([{"role": "user", "content": prompt}], max_tokens=60).choices[0].message.content or ""
    try:
        parsed = json.loads(text)
        ok, err = True, None
    except json.JSONDecodeError as e:
        parsed, ok, err = None, False, str(e)
    return {"pass": ok, "raw_reply": text, "parsed": parsed, "json_error": err,
            "note": "pass=False means we must extract/repair JSON ourselves (handled in a later milestone)"}


def check_tool_calling() -> dict:
    msgs = [{"role": "user", "content": "How many negative reviews mention delivery? Use the tool."}]
    resp = chat(msgs, tools=[COUNT_TOOL], max_tokens=200)
    msg = resp.choices[0].message
    calls = msg.tool_calls or []
    out = {"finish_reason": resp.choices[0].finish_reason, "content": msg.content, "tool_calls": []}
    for tc in calls:
        entry = {"name": tc.function.name, "arguments_raw": tc.function.arguments}
        try:
            entry["arguments_parsed"] = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError as e:
            entry["arguments_error"] = str(e)
        out["tool_calls"].append(entry)
    out["pass"] = bool(calls) and all("arguments_parsed" in c for c in out["tool_calls"])
    return out


def main() -> int:
    report = {"timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
              "python": platform.python_version(), "openai_sdk": openai.__version__, "checks": {}}

    try:
        s = get_settings()
    except ConfigError as e:
        print(f"[FAIL] settings: {e}")
        return 1
    report["base_url"] = s.base_url          # not a secret; the key is never stored
    report["model_requested"] = s.model
    report["checks"]["settings"] = {"pass": True, "api_key_set": True}
    print(f"[PASS] settings      base_url={s.base_url} model={s.model}")

    for name, fn in [("basic_chat", check_basic_chat), ("repeatability", check_repeatability),
                     ("json_prompt", check_json_prompt), ("tool_calling", check_tool_calling)]:
        try:
            result = fn()
        except openai.APIError as e:
            result = {"pass": False, "error": f"{type(e).__name__}: {e}"}
        except Exception as e:  # record, don't hide
            result = {"pass": False, "error": f"{type(e).__name__}: {e}"}
        report["checks"][name] = result
        detail = result.get("error") or ""
        if name == "basic_chat" and "reply" in result:
            detail = f"reply={result['reply']!r} latency={result['latency_s']}s"
        if name == "tool_calling" and "tool_calls" in result:
            detail = f"tool_calls={[ (c['name'], c.get('arguments_parsed')) for c in result['tool_calls'] ]}"
        if name == "json_prompt" and "raw_reply" in result:
            detail = f"raw_reply={result['raw_reply'][:80]!r}"
        print(f"[{'PASS' if result['pass'] else 'FAIL'}] {name:13} {detail}")
        if name == "basic_chat" and not result["pass"]:
            break  # nothing else can work if a plain chat call fails

    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {RESULTS}")
    return 0 if report["checks"].get("basic_chat", {}).get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())