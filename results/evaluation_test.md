# Evaluation results — test split (n = 30)

Generated 2026-11-01T16:21:47+07:00 from commit `d559596` by `python -m scripts.run_eval --split test`.

| Method | Sentiment accuracy | Sentiment macro F1 | Aspect micro F1 | Evidence validity | Failed / missing |
|---|---:|---:|---:|---:|---:|
| majority | 0.567 | 0.241 | — | — | 0 / 0 |
| rating | 0.800 | 0.727 | — | — | 0 / 0 |
| keyword | 0.767 | 0.623 | 0.800 | — | 0 / 0 |
| llm_v1 | 0.900 | 0.820 | 0.798 | 0.994 | 0 / 0 |
| llm_v2 | 0.900 | 0.820 | 0.870 | 1.000 | 0 / 0 |

Failed = the model never returned valid JSON (counted as wrong); missing = no prediction for that review (also counted as wrong).

## Per-aspect F1 (support = gold count)

| Method | taste | price | service | comfort | portion | other |
|---|---:|---:|---:|---:|---:|---:|
| keyword | 0.96 (27) | 0.88 (16) | 0.50 (9) | 0.91 (10) | 0.55 (6) | 0.67 (7) |
| llm_v1 | 0.98 (27) | 0.94 (16) | 0.89 (9) | 0.46 (10) | 0.67 (6) | 0.40 (7) |
| llm_v2 | 0.98 (27) | 0.97 (16) | 0.84 (9) | 0.90 (10) | 0.75 (6) | 0.44 (7) |

## Sentiment confusion (rows = gold, columns = predicted)

**majority**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 17 | 0 | 0 |
| neutral | 3 | 0 | 0 |
| negative | 10 | 0 | 0 |

**rating**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 12 | 4 | 1 |
| neutral | 0 | 2 | 1 |
| negative | 0 | 0 | 10 |

**keyword**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 16 | 1 | 0 |
| neutral | 1 | 1 | 1 |
| negative | 1 | 3 | 6 |

**llm_v1**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 15 | 2 | 0 |
| neutral | 0 | 2 | 1 |
| negative | 0 | 0 | 10 |

**llm_v2**

| gold \ pred | positive | neutral | negative |
|---|---:|---:|---:|
| positive | 15 | 2 | 0 |
| neutral | 0 | 2 | 1 |
| negative | 0 | 0 | 10 |

## Sentiment errors (for failure analysis)

- **majority**: w245 (neutral→positive), w183 (negative→positive), w141 (negative→positive), w289 (neutral→positive), w107 (negative→positive), w232 (negative→positive), w197 (negative→positive), w037 (negative→positive), w293 (negative→positive), w239 (negative→positive), w098 (neutral→positive), w017 (negative→positive), w211 (negative→positive)
- **rating**: w289 (neutral→negative), w173 (positive→neutral), w286 (positive→neutral), w262 (positive→negative), w201 (positive→neutral), w164 (positive→neutral)
- **keyword**: w289 (neutral→positive), w107 (negative→neutral), w197 (negative→positive), w037 (negative→neutral), w098 (neutral→negative), w108 (positive→neutral), w017 (negative→neutral)
- **llm_v1**: w111 (positive→neutral), w098 (neutral→negative), w262 (positive→neutral)
- **llm_v2**: w111 (positive→neutral), w098 (neutral→negative), w262 (positive→neutral)
