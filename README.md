# ReviewLens

**ลิงก์แอป (live):** https://reviewlens-aleh.onrender.com
(ใช้ Render แผนฟรี ถ้าไม่มีคนเข้าประมาณ 15 นาที แอปจะหลับ คนแรกที่เปิดต้องรอ 30–60 วินาทีให้แอปตื่น)

ReviewLens ใช้โมเดล `gemma-4-E4B-it` ของวิชา วิเคราะห์รีวิวร้านอาหารภาษาไทย 300 รีวิว
ให้ออกมาเป็นข้อมูลที่มีโครงสร้าง และทุกผลมีหลักฐานอ้างอิงจากข้อความรีวิวจริง
ผู้ใช้ยังถามคำถามเกี่ยวกับรีวิวเหล่านี้ได้ผ่าน agent ขนาดเล็กที่เรียกใช้ tool ได้
**ตัวเลขทุกตัวที่แสดงให้ผู้ใช้เห็นคำนวณด้วย Python** ส่วน LLM มีหน้าที่แค่อ่านรีวิวและเลือกว่าจะใช้ tool ไหน

โปรเจกต์จบ (capstone) ของรายวิชา *Building LLM-Powered Applications* คณะเทคโนโลยีสารสนเทศ สจล.

## ความสามารถหลัก (capability families)

| Family | อยู่ที่ไฟล์ | ทำอะไร |
|---|---|---|
| Structured output / extraction | `app/analyzer.py`, `app/schemas.py` | แปลงรีวิวเป็น JSON `{sentiment, aspects, evidence}` แล้วตรวจด้วย Pydantic ถ้าโมเดลตอบผิดรูปแบบจะให้ตอบใหม่ 1 ครั้ง และตรวจว่า evidence ตรงกับข้อความรีวิวแบบคำต่อคำ |
| Tool use / agent (agentic) | `app/tools.py`, `app/agent.py` | ใช้ native tool calling กับ tool 4 ตัวที่อนุญาตไว้ล่วงหน้า (allow-list) ตรวจ argument ทุกครั้ง จำกัดไม่เกิน 3 รอบและเรียก tool ไม่เกิน 6 ครั้ง และบันทึก trace ไว้ทั้งหมด |
| Evaluation | `app/metrics.py`, `scripts/run_eval.py`, `scripts/eval_agent.py` | gold label 40 รีวิวที่ตรวจด้วยคน, baseline 3 แบบ, เปรียบเทียบ prompt v1 กับ v2 และวัดว่า agent เลือก tool ถูกหรือไม่ |

## ผลการทดลอง (ชุด test: 30 รีวิวที่ตรวจด้วยคน รันครั้งเดียวต่อ prompt แต่ละเวอร์ชัน)

| วิธี | Sentiment acc | Sentiment macro F1 | Aspect micro F1 | Evidence validity |
|---|---:|---:|---:|---:|
| majority (ตอบคลาสที่พบบ่อยที่สุดเสมอ) | 0.567 | 0.241 | — | — |
| rating (4–5★ = บวก / 3★ = กลาง / 1–2★ = ลบ) | 0.800 | 0.727 | — | — |
| keyword lexicon (คำศัพท์บวก/ลบ) | 0.767 | 0.623 | 0.800 | — |
| LLM prompt v1 | 0.900 | 0.820 | 0.798 | 0.994 |
| **LLM prompt v2** | **0.900** | **0.820** | **0.870** | **1.000** |

**การปรับปรุงที่วัดผลได้:** prompt v2 เพิ่มคำนิยามของแต่ละ aspect และตัวอย่างที่แต่งขึ้นเอง 2 ตัวอย่าง
ออกแบบจากข้อผิดพลาดของ v1 บนชุด dev (10 รีวิว) เท่านั้น ผลคือ aspect micro F1 บนชุด test เพิ่มจาก 0.798 เป็น 0.870
ส่วน sentiment ไม่เปลี่ยน ข้อควรระวัง: 30 รีวิวถือเป็นตัวอย่างขนาดเล็ก รีวิวเพียง 1 อันทำให้ accuracy เปลี่ยนได้ 0.033
ตารางฉบับเต็มอยู่ที่ `results/evaluation_test.md` ส่วนการออกแบบและเหตุผลอยู่ที่ `docs/experiment_log.md`

**ผลของ agent** (คำถามที่เขียนขึ้นเอง 10 ข้อ, `results/agent_eval_v2.md`):
- เลือก tool ถูก 0.80
- argument ตรงทุกค่า 0.80
- คำตอบมีตัวเลขถูก หรืออ้าง review ID ที่ถูก 1.00 (n=7)

รอบแรกได้ 0.86 เพราะโมเดลเคยตอบกลับมาเป็นข้อความว่าง ตอนนี้ loop จะถามซ้ำ 1 ครั้งโดยไม่ให้ใช้ tool
(ผลรอบแรกยังเก็บไว้ที่ `results/agent_eval.md`)

## กรณีที่ระบบผิดพลาด (failure cases)

- **ถูกครบทุกอย่างเพียง 12 จาก 30 รีวิว** (ต้องถูกทั้ง sentiment, ชุด aspect ตรงทั้งชุด และ evidence ตรงคำต่อคำ)
  ส่วนใหญ่ที่พลาดคือใส่ aspect `other` หรือ `portion` เกินมา (F1 ของ `other` ได้แค่ 0.44)
- **รีวิวที่มีทั้งชมและติ (mixed) วิเคราะห์ยาก:** w111 และ w262 ใน gold label เป็นบวก แต่โมเดลตอบกลาง
  ส่วน w098 เป็นกลาง แต่โมเดลตอบลบ
- **prompt v1 แก้คำผิดของผู้รีวิวเองโดยไม่บอก:** w197 โมเดลเขียนว่า "ข้าวมา" แต่รีวิวจริงเขียนว่า "ข้าาวมา"
  ข้อความที่ยกมาจึงไม่ตรงคำต่อคำ แอปจะทำเครื่องหมาย evidence ที่ตรวจไม่ผ่าน และไม่แสดงเป็นข้อเท็จจริง
- **agent บางครั้งเลือก tool อื่นที่ก็ใช้ได้** (a01) หรือตอบจาก schema ของ tool โดยไม่เรียก tool เลย (a09)
- **sentiment เป็นระดับทั้งรีวิว ไม่ใช่ระดับ aspect:** "รีวิวบวกเรื่องรสชาติ" หมายถึง "รีวิวที่โดยรวมเป็นบวกและพูดถึงรสชาติ"
  ไม่ได้แปลว่าชมรสชาติจริง
- **evidence ไม่ได้ผูกกับ aspect:** ตัวอย่างของ "รสชาติ" จึงอาจแสดงประโยคที่พูดถึงราคา
- **gold label อาจผิดได้เช่นกัน:** Claude เป็นผู้เสนอ แล้วผู้จัดทำตรวจหรือแก้ไข (ดู `docs/annotation_guideline.md` หัวข้อ 5.4)

แท็บ Evaluation ในแอปแสดงรีวิวชุด test ทุกอัน แยกว่าระบบทำถูก (success) หรือผิด (failure)

## ข้อมูล

ใช้รีวิว 300 รีวิวจากคลังข้อมูล Wongnai (สัญญาอนุญาต LGPL-3.0, ตรึง commit ไว้)
คัดมาดาวละ 60 รีวิว และปิดบังเบอร์โทรศัพท์แล้ว เพราะคัดมาแบบสมดุล
**เปอร์เซ็นต์ในแอปจึงบรรยายเฉพาะชุดตัวอย่างนี้ ไม่ได้แทนรีวิว Wongnai ทั้งหมด**
รายละเอียด checksum และสัญญาอนุญาตอยู่ที่ `data/README.md`

## วิธีรันในเครื่อง (Windows PowerShell)

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # ใส่ key และ base URL ของวิชาลงใน .env ห้าม commit ไฟล์นี้เด็ดขาด
python -m pytest -q           # ไม่ต้องใช้อินเทอร์เน็ต
uvicorn app.main:app --reload # เปิด http://127.0.0.1:8000  (เอกสาร API อยู่ที่ /docs)
```

แอปอ่านผลวิเคราะห์ที่เก็บไว้แล้วจาก `results/predictions/llm_v2_all.jsonl`
แท็บ Dashboard, Reviews และ Evaluation จึงใช้ได้แม้ไม่มี key
มีเพียงแท็บ *Ask* และ *Analyze a review* ที่เรียก LLM

## รันซ้ำเพื่อให้ได้ผลเดิม

```powershell
python -m scripts.smoke_test_proxy                         # ทดสอบความสามารถของ proxy -> results/smoke_test.json
python -m scripts.prepare_data                             # ดาวน์โหลดและสุ่มตัวอย่าง -> data/reviews.csv
python -m scripts.build_gold                               # labeling.xlsx -> data/eval/gold_labels.jsonl
python -m scripts.predict_llm --prompt v1 --split test     # เปลี่ยนเป็น v2, dev หรือ all ได้
python -m scripts.run_eval --split test --pred llm_v1=results/predictions/llm_v1_test.jsonl --pred llm_v2=results/predictions/llm_v2_test.jsonl
python -m scripts.predict_llm --prompt v2 --split all      # สร้างข้อมูลให้แอป
python -m scripts.eval_agent v2
python -m scripts.ask "How many negative reviews talk about service?"
```

ผลของ LLM อาจต่างไปเล็กน้อยในแต่ละรอบ แม้ตั้ง temperature เป็น 0

## API

| Method | Path | เรียก LLM ไหม |
|---|---|---|
| GET | `/health` | ไม่ |
| GET | `/api/stats` | ไม่ |
| GET | `/api/reviews?sentiment=&aspect=&rating=&q=&offset=&limit=` | ไม่ |
| GET | `/api/reviews/{id}` | ไม่ |
| GET | `/api/evaluation` | ไม่ |
| POST | `/api/analyze` `{"text": "..."}` (ยาว 5–2000 ตัวอักษร) | ใช่ (มี rate limit) |
| POST | `/api/ask` `{"question": "..."}` (ยาว 3–300 ตัวอักษร) | ใช่ (มี rate limit) |

## ความปลอดภัยและข้อจำกัด

- **API key:** ในเครื่องเก็บไว้ใน `.env` เท่านั้น (git ไม่ track ไฟล์นี้) ส่วนบนโปรดักชันเก็บใน environment settings ของ Render
  ไฟล์ `render.yaml` ไม่มีค่า secret ใดๆ และมีเทสต์คอยตรวจ
  ช่วงแรกของโปรเจกต์เคย commit key ขึ้นไปโดยไม่ตั้งใจ จึงเขียนประวัติ git ใหม่และเปลี่ยน key แล้ว
- **ข้อความรีวิวถือเป็น input ที่ไม่น่าเชื่อถือ:** ครอบด้วยแท็ก `<review>` สั่ง agent ไม่ให้ทำตามคำสั่งที่อยู่ในผลลัพธ์ของ tool
  และหน้าเว็บใส่ข้อความด้วย `textContent` เท่านั้น
- **LLM รันโค้ด, SQL หรือคำสั่ง shell ไม่ได้:** เรียกได้แค่ tool 4 ตัวที่อนุญาตไว้
  และ argument ถูกตรวจทุกครั้ง (ค่าต้องอยู่ในรายการที่กำหนด, `limit` อยู่ระหว่าง 1–10, key ที่ไม่รู้จักถูกปฏิเสธ)
- **ไม่เดา label:** ถ้าโมเดลตอบผิดรูปแบบจะให้ตอบใหม่ 1 ครั้ง ถ้ายังผิดจะบันทึกเป็น `failed`
- **Rate limit:** การเรียก LLM สดจำกัดที่ 5 ครั้งต่อนาทีต่อผู้ใช้ และ 300 ครั้งต่อวันทั้งแอป
  (ตั้งค่าได้ด้วย `LIVE_PER_MINUTE`, `LIVE_PER_DAY` และปิดได้ด้วย `LIVE_LLM_ENABLED=0`)
  ตัวนับเก็บในหน่วยความจำ จึงรีเซ็ตทุกครั้งที่แอปบนแผนฟรีรีสตาร์ต

## การ deploy (Render)

ที่ Render ให้กด New → Blueprint แล้วเลือก repo นี้ Render จะอ่าน `render.yaml` แล้วให้กรอก `OPENAI_API_KEY` กับ `OPENAI_BASE_URL`
หลังจากนั้นทุกครั้งที่ push ขึ้น `main` จะ deploy ใหม่ให้อัตโนมัติ

## โครงสร้างโปรเจกต์

```
app/        ตัววิเคราะห์ (analyzer), schema, tools, agent, metrics, baseline, แอป FastAPI และหน้าเว็บ
scripts/    เตรียมข้อมูล, ติด label, ทำนายผล, ประเมินผล, agent แบบ command line
data/       reviews.csv, gold label, คำถามสำหรับ agent, สัญญาอนุญาต
docs/       คู่มือการติด label (annotation guideline), บันทึกการทดลอง (experiment log)
results/    ตารางผลประเมินและผลทำนายที่บันทึกไว้
tests/      ชุดเทสต์ pytest (ไม่ต้องใช้อินเทอร์เน็ต)
```

## การใช้ AI ช่วยในการพัฒนา

โค้ดเขียนโดยมี Claude (Anthropic) ช่วย ผู้จัดทำเป็นผู้ตรวจสอบ รัน และ commit เอง
Claude ยังช่วยเสนอ gold label ซึ่งผู้จัดทำตรวจทานแล้ว (ดู `docs/annotation_guideline.md`)
