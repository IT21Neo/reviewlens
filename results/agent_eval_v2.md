# Agent evaluation

Analyses: `results\predictions\llm_v2_all.jsonl` · questions: 10

| Metric | Score | n |
|---|---:|---:|
| tool_choice | 0.80 | 10 |
| args_exact | 0.80 | 10 |
| answer_ok | 1.00 | 7 |

| id | question | tools called | tool | args | answer |
|---|---|---|---|---|---|
| a01 | How many reviews mention price? | aspect_summary {"aspect": "price"} | False | False | True |
| a02 | มีรีวิวด้านลบทั้งหมดกี่รีวิว | count_reviews {"sentiment": "negative", "aspect": null} | True | True | True |
| a03 | How many negative reviews talk about service? | count_reviews {"sentiment": "negative", "aspect": "service"} | True | True | True |
| a04 | How many positive reviews are there? | count_reviews {"sentiment": "positive", "aspect": null} | True | True | True |
| a05 | รีวิวที่พูดถึงราคา มีกี่รีวิวที่เป็นกลาง (neutral) | count_reviews {"sentiment": "neutral", "aspect": "price"} | True | True | True |
| a06 | Show three negative reviews about taste. | get_review_examples {"sentiment": "negative", "aspect": "taste", "limit": 3} | True | True | True |
| a07 | ขอตัวอย่างรีวิวที่พูดถึงปริมาณอาหาร 2 รีวิว | get_review_examples {"sentiment": null, "aspect": "portion", "limit": 2} | True | True | True |
| a08 | Summarize what customers say about the service. | aspect_summary {"aspect": "service"} | True | True | None |
| a09 | What labels can I filter reviews by? | — | False | False | None |
| a10 | ลูกค้าพูดถึงบรรยากาศร้านว่ายังไงบ้าง | aspect_summary {"aspect": "comfort"} | True | True | None |
