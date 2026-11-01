"""Ask the agent one question from the command line and print its tool trace.

    python -m scripts.ask "How many negative reviews mention service?"
"""
import json
import sys

from app.agent import ask


def main(argv: list[str]) -> int:
    if not argv:
        print('usage: python -m scripts.ask "your question"')
        return 1
    res = ask(" ".join(argv))
    for step in res.trace:
        if "tool" in step:
            print(f"[round {step['round']}] tool={step['tool']} args={json.dumps(step['validated_arguments'], ensure_ascii=False)} ok={step['ok']}")
        else:
            print("[error]", step.get("error"))
    print(f"\nstopped_by={res.stopped_by} rounds={res.rounds}\n")
    print(res.answer)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
