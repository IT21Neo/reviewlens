# Evaluation results — dev split (n = 10)

Generated 2026-11-01T16:16:35+07:00 from commit `d559596` by `python -m scripts.run_eval --split dev`.

| Method | Sentiment accuracy | Sentiment macro F1 | Aspect micro F1 | Evidence validity | Failed / missing |
|---|---:|---:|---:|---:|---:|
| majority | 0.600 | 0.250 | — | — | 0 / 0 |
| rating | 0.700 | 0.552 | — | — | 0 / 0 |
| keyword | 0.700 | 0.500 | 0.820 | — | 0 / 0 |
| llm_v1 | 0.900 | 0.859 | 0.821 | 0.955 | 0 / 0 |
| llm_v2 | 0.900 | 0.859 | 0.909 | 0.969 | 0 / 0 |

Failed = the model never returned valid JSON (counted as wrong); missing = no prediction for that review (also counted as wrong).

## Per-aspect F1 (support = gold count)

| Method | taste | price | service | comfort | portion | other |
|---|---:|---:|---:|---:|---:|---:|
| keyword | 1.00 (10) | 0.89 (4) | 0.75 (3) | 0.75 (4) | 0.25 (1) | 1.00 (4) |
| llm_v1 | 1.00 (10) | 0.89 (4) | 1.00 (3) | 0.40 (4) | 0.40 (1) | 0.73 (4) |
| llm_v2 | 1.00 (10) | 0.89 (4) | 1.00 (3) | 0.75 (4) | 0.67 (1) | 0.89 (4) |

## Sentiment confusion (rows = gold, columns = predicted)

**majority**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 6 | 0 | 0 |
| neutral | 1 | 0 | 0 |
| negative | 3 | 0 | 0 |

**rating**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 4 | 2 | 0 |
| neutral | 0 | 0 | 1 |
| negative | 0 | 0 | 3 |

**keyword**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 5 | 0 | 1 |
| neutral | 1 | 0 | 0 |
| negative | 0 | 1 | 2 |

**llm_v1**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 5 | 1 | 0 |
| neutral | 0 | 1 | 0 |
| negative | 0 | 0 | 3 |

**llm_v2**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 5 | 1 | 0 |
| neutral | 0 | 1 | 0 |
| negative | 0 | 0 | 3 |

## Sentiment errors (for failure analysis)

- **majority**: w203 (negative→positive), w060 (negative→positive), w021 (negative→positive), w176 (neutral→positive)
- **rating**: w176 (neutral→negative), w288 (positive→neutral), w246 (positive→neutral)
- **keyword**: w021 (negative→neutral), w176 (neutral→positive), w246 (positive→negative)
- **llm_v1**: w246 (positive→neutral)
- **llm_v2**: w246 (positive→neutral)
