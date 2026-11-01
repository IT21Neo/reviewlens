# Experiment log — prompt v1 → v2

Rule: prompts are changed by looking at the **dev** split only. The **test** split is run
once per prompt version and never used to choose wording.

## Step 1 — prompt v1 (naive default)

Label names only, no definitions, no examples (`PROMPT_V1` in `app/analyzer.py`).
Run on dev and test with `scripts/predict_llm.py`; scores from `scripts/run_eval.py`.

### Dev error analysis (10 reviews) — the only input used to design v2

Compared `results/predictions/llm_v1_dev.jsonl` with `data/eval/gold_labels.jsonl`:

| review | gold | v1 prediction | error |
|---|---|---|---|
| w021 | negative · taste | negative · taste, other | extra `other` |
| w060 | negative · taste, service | negative · taste, service, portion, other | extra `portion`, `other` |
| w192 | positive · taste, price, comfort, other | positive · taste, price, other | missing `comfort` |
| w203 | negative · taste, price | negative · taste, price, portion | extra `portion` |
| w246 | **positive** · taste, comfort, portion, other | **neutral** · taste, portion, other | sentiment; missing `comfort` |
| w254 | positive · taste, service, comfort, other | positive · taste, service, portion, other | extra `portion`, missing `comfort` |
| w288 | positive · taste, price | positive · taste, price, other | extra `other` |

Pattern: `other` used as a default (3 extra), `portion` confused with crowds/menu size
(3 extra), `comfort` not recognised as "the place" (3 missing). Sentiment: 1 error, on a
mixed review.

## Step 2 — prompt v2 (one change: definitions + two invented examples)

`PROMPT_V2` adds: the overall-stance sentiment rule; a definition per aspect (taken from
`docs/annotation_guideline.md`); explicit notes that `other` is never a default and that
crowds or a big menu are not `portion`; two short examples written for the prompt (a test
checks they are not reviews from the dataset). Output format, temperature, retry logic and
validation are unchanged, so the comparison isolates the prompt.

## Step 3 — results (copied from the run_eval output of 2026-11-01, commit d559596)

| Split | Method | Sentiment acc | Sentiment macro F1 | Aspect micro F1 | Evidence validity |
|---|---|---:|---:|---:|---:|
| dev (n=10) | keyword | 0.700 | 0.500 | 0.820 | — |
| dev (n=10) | llm_v1 | 0.900 | 0.859 | 0.821 | 0.955 |
| dev (n=10) | llm_v2 | 0.900 | 0.859 | 0.909 | 0.969 |
| test (n=30) | rating | 0.800 | 0.727 | — | — |
| test (n=30) | keyword | 0.767 | 0.623 | 0.800 | — |
| test (n=30) | llm_v1 | 0.900 | 0.820 | 0.798 | 0.994 |
| test (n=30) | **llm_v2** | 0.900 | 0.820 | **0.870** | **1.000** |

v2 was run on test once, after it was fixed on dev. Measured change v1 → v2 on test:
aspect micro F1 +0.072 (0.798 → 0.870), evidence validity 0.994 → 1.000, sentiment unchanged.
Caveat: 30 test reviews is small; a few reviews decide these differences.
Source files: `results/evaluation_dev.md`, `results/evaluation_test.md`.

Failure example kept for the report: in v1 the only invalid evidence snippet was for w197,
where the model wrote "ข้าวมา" but the review says "ข้าาวมา" — the model silently corrected the
reviewer's typo, so the quote was no longer verbatim.

## Step 4 — agent (tools + loop) on 10 hand-written questions

All 300 reviews analysed with v2 (`llm_v2_all.jsonl`): 300/300 ok, 980/994 evidence snippets
verbatim (unverified ones are dropped when the app loads the data).

Run 1 (commit e9a18ce, `results/agent_eval.md`): tool_choice 0.80 (n=10), args_exact 0.80 (n=10),
answer_ok 0.86 (n=7; summary/list questions are not scored on answer text).

| id | question | what happened |
|---|---|---|
| a01 | How many reviews mention price? | called `aspect_summary(price)` instead of `count_reviews`; the answer (148) was still correct — the metric accepts only one tool |
| a05 | รีวิวที่พูดถึงราคา มีกี่รีวิวที่เป็นกลาง | right tool and arguments (tool returned 24), but the model's final reply was an **empty string** and the loop accepted it |
| a09 | What labels can I filter reviews by? | answered without any tool call (the labels are visible in the tool schemas); the answer was correct |

Change (a loop bug fix, not prompt tuning): an empty final reply is now retried once with no
tools offered; if it is still empty the agent returns a fixed "empty answer" message with
`stopped_by="empty"` instead of an empty string. The questions and the prompt are unchanged.

Run 2 (after the fix, `results/agent_eval_v2.md`): tool_choice 0.80 (n=10), args_exact 0.80 (n=10),
answer_ok **1.00** (n=7). a05 now shows `retry=True` and its answer contains the correct count;
a01 and a09 behave as in run 1 (tool selection is unchanged, as expected — only the loop changed).
Caveat: 10 questions written by us, and the same 10 were used before and after the fix, so this
shows the bug is fixed on the case that exposed it, not a general improvement in accuracy.

Other limitation seen: example snippets are the review's first verified evidence, which is not
linked to an aspect — e.g. a06 (negative + taste) showed w002 with a snippet about price.
