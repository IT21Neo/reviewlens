"""Evaluate the agent on data/eval/agent_questions.jsonl (calls the proxy).

For each hand-written question the file lists the tool call(s) a correct agent should make.
Metrics:
  tool_choice   — the agent called the expected tool at least once
  args_exact    — some call of that tool had exactly the expected validated arguments
  answer_ok     — count questions: the number returned by the expected call appears in the
                  final answer; example questions: at least one returned review id is cited
                  (summary/list questions are not scored on answer text)
The "right" numbers are computed by running the expected call on the same stored labels,
so this measures tool selection and faithful reporting, not label accuracy.

    python -m scripts.eval_agent        -> results/agent_eval.json and .md
    python -m scripts.eval_agent v2     -> results/agent_eval_v2.json and .md (keeps the old run)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from app.agent import ask
from app.data import get_store
from app.tools import run_tool

QUESTIONS = Path("data/eval/agent_questions.jsonl")
RESULTS = Path("results")
TAG = sys.argv[1] if len(sys.argv) > 1 else ""   # optional: python -m scripts.eval_agent v2


def main() -> int:
    store = get_store()
    qs = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8") if l.strip()]
    rows = []
    for q in qs:
        exp = q["expected"][0]
        expected_out, expected_args = run_tool(store, exp["tool"], exp["args"])
        res = ask(q["question"], store)
        calls = [s for s in res.trace if s.get("tool")]
        tool_choice = any(c["tool"] == exp["tool"] for c in calls)
        args_exact = any(c["tool"] == exp["tool"] and c["validated_arguments"] == expected_args for c in calls)
        answer_ok = None
        if q["type"] == "count":
            answer_ok = re.search(rf"(?<!\d){expected_out['count']}(?!\d)", res.answer) is not None
        elif q["type"] == "examples":
            ids = [e["review_id"] for e in expected_out["examples"]]
            answer_ok = any(i in res.answer for i in ids)
        rows.append({"id": q["id"], "question": q["question"], "type": q["type"],
                     "tools_called": [(c["tool"], c["validated_arguments"]) for c in calls],
                     "tool_choice": tool_choice, "args_exact": args_exact, "answer_ok": answer_ok,
                     "stopped_by": res.stopped_by, "forced_retry": res.forced_retry, "rounds": res.rounds, "answer": res.answer})
        print(f"{q['id']} tool={tool_choice!s:5} args={args_exact!s:5} answer={answer_ok!s:5} {res.stopped_by:10} retry={res.forced_retry!s:5} {[c[0] for c in rows[-1]['tools_called']]}")

    def rate(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return sum(vals) / len(vals) if vals else None, len(vals)

    summary = {k: rate(k) for k in ("tool_choice", "args_exact", "answer_ok")}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"agent_eval{'_' + TAG if TAG else ''}.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    md = ["# Agent evaluation", "", f"Analyses: `{store.analyses_file}` · questions: {len(rows)}", "",
          "| Metric | Score | n |", "|---|---:|---:|"]
    md += [f"| {k} | {v[0]:.2f} | {v[1]} |" for k, v in summary.items() if v[0] is not None]
    md += ["", "| id | question | tools called | tool | args | answer |", "|---|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['question']} | {'; '.join(f'{t} {json.dumps(a, ensure_ascii=False)}' for t, a in r['tools_called']) or '—'} | "
           f"{r['tool_choice']} | {r['args_exact']} | {r['answer_ok']} |" for r in rows]
    (RESULTS / f"agent_eval{'_' + TAG if TAG else ''}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md[4:4 + len(summary) + 2]))
    print(f"saved results/agent_eval{'_' + TAG if TAG else ''}.json and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
