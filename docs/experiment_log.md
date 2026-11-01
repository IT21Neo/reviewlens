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
