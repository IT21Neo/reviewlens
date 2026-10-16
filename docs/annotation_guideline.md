# Annotation guideline — ReviewLens gold labels

Version 1.1 — v1.0 was fixed before annotation started. v1.1 was added during annotation,
because the aspect boundaries were hard to apply; it adds a Thai explanation sheet and two
clarifications (section 3a). Rows labelled before v1.1 were re-checked against it. Do not change these definitions during
annotation. If a rule turns out to be unclear, write the case in the `notes` column and
keep applying the rule as written; report it as a limitation.

Labels are defined in code in `app/taxonomy.py`.

## 1. What to label

For each review in `data/eval/labeling.xlsx` (sheet `labels`, yellow columns), created by
`python -m scripts.make_label_sheet` from `data/eval/to_label.csv`:

| Column | Fill in |
|---|---|
| `gold_sentiment` | exactly one of `positive`, `neutral`, `negative` |
| `gold_aspects` | zero or more aspects separated by `;` — e.g. `taste;price` |
| `gold_evidence` | short phrases **copied exactly** from the review, separated by ` \| ` — at least one per aspect is recommended |
| `notes` | optional: why a case was hard |

**Label from the review text only.** The star rating is hidden on purpose: the rating is
used as a baseline, so looking at it would leak the baseline's answer into the gold set.

## 2. Sentiment — the writer's overall stance

| Label | When |
|---|---|
| `positive` | Overall satisfied, or recommends the restaurant, even with small complaints. |
| `negative` | Overall dissatisfied, or would not recommend / not return, even with some praise. |
| `neutral` | No clear overall stance: praise and complaints weigh about the same, or the review only describes without an opinion. |

**Mixed reviews:** decide by the overall stance. Look first at a concluding statement
(e.g. "คงไม่ไปซ้ำ" → negative, "แนะนำเลย" → positive). If there is no conclusion and the
good and bad points weigh about the same, use `neutral`. There is no `mixed` label.

## 3. Aspects — what the writer gives an opinion about (multi-label)

| Aspect | Meaning | Count it when the review comments on… | Do **not** count (goes elsewhere) |
|---|---|---|---|
| `taste` | food/drink quality | flavour, freshness, doneness, food temperature, texture, smell (อร่อย, จืด, เค็มไป, ไม่สด, เหนียว) | "many menu items" → `other` |
| `price` | price and value | expensive, cheap, worth it, not worth it, service charge (แพงไป, คุ้ม) | a price stated with no opinion ("จานละ 60 บาท") → not counted |
| `service` | staff and service process | politeness, speed, waiting time, wrong/forgotten orders, billing (พนักงานยิ้มแย้ม, รอนาน) | cleanliness of the place → `comfort` |
| `comfort` | the place itself | cleanliness of the shop, decoration, atmosphere, air-con, noise, seating, space, toilets, view (ร้านสะอาด, แอร์ไม่เย็น, ร้านแคบ) | hair/dirt **in the food** → `taste` |
| `portion` | amount of food | big/small portions, (not) being full (ให้เยอะ, น้อยไป, กินไม่อิ่ม) | "small for the price" → count **both** `portion` and `price` |
| `other` | any other opinion | parking, location, getting there, menu variety, opening hours, take-away / delivery (หาที่จอดยาก, เมนูเยอะ) | only when no other aspect fits |

### 3a. Thai explanation and clarifications (v1.1)

A beginner-friendly Thai version of this table — a decision question per aspect, more
examples, and a list of commonly confused phrases — is the `guide` sheet of
`data/eval/labeling.xlsx` (source: `scripts/label_guide_th.py`). It does not change the
rules above except for two clarifications:

- the **look/presentation of the food** counts as `taste` (food quality);
- a **promotion or discount** ("มีโปรลดราคา") counts as `price`.

Rules:

1. A review can have several aspects.
2. Count an aspect only when the writer expresses an **opinion** about it (positive or
   negative). Pure description ("สั่งต้มยำกับข้าวผัด") does not count.
3. Do not infer: if the aspect is not mentioned, do not add it.
4. `other` is not a default. Leave `gold_aspects` empty if the review expresses no opinion
   on any aspect.

## 4. Evidence

- Copy phrases **exactly** as they appear in the review (same spelling, same spacing),
  so the program can find them. Short is better: 3–15 words.
- Separate several phrases with ` | ` (space, vertical bar, space).
- `scripts/build_gold.py` rejects any phrase that is not found verbatim in the review.

## 5. Process

1. Label the `dev` rows first (10 reviews). Re-read this guideline and note unclear cases.
2. Label the `test` rows (30 reviews) in one sitting if possible, without changing the rules.
3. The `dev` rows may be used to adjust prompts; the `test` rows are used **only** for the
   final measurement.
4. **AI-drafted labels (all 40 rows).** To save time, the annotator labelled while looking
   at suggestions written by Claude (an AI assistant — not the `gemma-4-E4B-it` model being
   evaluated). Claude worked from the review text only, without star ratings, and wrote
   `gold_sentiment`, `gold_aspects` (and, for dev, evidence) for every row:
   `data/eval/suggestions_dev_claude.csv` and `data/eval/suggestions_test_claude.csv`.
   The annotator reviewed the suggestions against this guideline and entered the final
   labels. `scripts/mark_label_source.py` then compared each final label with the
   suggestion and recorded `claude_checked` (identical) or `claude_edited` (different) in
   the `label_source` field of `gold_labels.jsonl`. Consequences, reported as limitations:
   the gold labels largely reflect one LLM's reading of the text, the annotator may have
   anchored on the suggestions, and agreement with these labels is not the same as
   agreement with independent human judgement.
5. Final labels were entered by one annotator (the project author). There is no second annotator,
   so inter-annotator agreement is not measured — this is a stated limitation.
