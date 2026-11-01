"""Non-LLM baselines (Milestone 5). Written and frozen BEFORE the LLM pipeline exists.

1. majority  — always predicts the most frequent dev-set sentiment; no aspects.
2. rating    — dataset-provided signal: 4-5 stars -> positive, 3 -> neutral, 1-2 -> negative;
               no aspects. (Stars were hidden from annotators, so this is not circular.)
3. keyword   — a small, hand-written Thai lexicon:
               sentiment = (#positive phrases - #negative phrases) -> sign;
               aspects   = every aspect with at least one keyword in the text.

Keyword matching is longest-phrase-first and each character is used once, so "ไม่อร่อย"
counts as ONE negative phrase and is not also counted as the positive "อร่อย".
Known weaknesses (to discuss in the report): sarcasm, negation beyond "ไม่/ไม่ค่อย",
mixed reviews, keywords used without an opinion ("ราคา 60 บาท"), ambiguous words
("เยอะ" in "คนเยอะ").

The word lists use general restaurant vocabulary and the example words of
docs/annotation_guideline.md. They were fixed before any baseline score was computed and
were never adjusted to improve a test-set number. Disclosure: they were written by Claude,
which had read the dev and test reviews while drafting the gold-label suggestions, so some
exposure to the test vocabulary cannot be ruled out.
"""
from __future__ import annotations

from app.taxonomy import ASPECTS

POSITIVE = ["อร่อย", "ชอบ", "ประทับใจ", "แนะนำ", "ฟิน", "เด็ด", "สุดยอด", "เยี่ยม", "ถูกใจ",
            "กลมกล่อม", "คุ้ม", "ดีมาก", "สะอาด", "น่ารัก", "บรรยากาศดี", "บริการดี", "นุ่ม",
            "หอม", "ใจดี", "สบาย", "ติดใจ", "ราคาถูก", "สมราคา"]
NEGATIVE = ["แย่", "ผิดหวัง", "แพง", "ห่วย", "เค็มไป", "จืด", "สกปรก", "เหม็น", "คาว", "รอนาน",
            "ช้า", "เสียดาย", "ไม่มาอีก", "ไม่ไปซ้ำ", "ไม่กลับมา", "เหนียว", "แข็ง"]
NEGATORS = ["ไม่ค่อย", "ไม่"]

ASPECT_KEYWORDS = {
    "taste": ["อร่อย", "รสชาติ", "รสชาด", "รสชาต", "จืด", "เค็ม", "หวาน", "เผ็ด", "เปรี้ยว", "สด",
              "กลมกล่อม", "นุ่ม", "เหนียว", "กรอบ", "หอม", "คาว"],
    "price": ["ราคา", "แพง", "คุ้ม", "ลดราคา", "ส่วนลด", "โปร"],
    "service": ["พนักงาน", "บริการ", "รอนาน", "ช้า", "เสิร์ฟ", "เจ้าของร้าน", "คนขาย", "ต้อนรับ",
                "ออร์เดอร์", "คิว"],
    "comfort": ["บรรยากาศ", "ตกแต่ง", "สะอาด", "สกปรก", "แอร์", "ที่นั่ง", "ห้องน้ำ", "แคบ",
                "เสียงดัง", "วิว", "นั่งสบาย"],
    "portion": ["ปริมาณ", "เยอะ", "น้อย", "อิ่ม", "จานใหญ่", "จานเล็ก", "ชิ้นโต"],
    "other": ["ที่จอด", "จอดรถ", "หลากหลาย", "เมนูเยอะ", "เดลิเวอรี่", "delivery", "เปิดดึก",
              "ทำเล", "เดินทาง", "กลับบ้าน"],
}
assert set(ASPECT_KEYWORDS) == set(ASPECTS)


def _phrase_table() -> list[tuple[str, int]]:
    """(phrase, polarity) incl. negated forms; longest first so 'ไม่อร่อย' beats 'อร่อย'."""
    table = [(w, +1) for w in POSITIVE] + [(w, -1) for w in NEGATIVE]
    table += [(n + w, -1) for n in NEGATORS for w in POSITIVE]   # ไม่อร่อย -> negative
    table += [(n + w, +1) for n in NEGATORS for w in NEGATIVE]   # ไม่แพง  -> positive
    return sorted(set(table), key=lambda x: -len(x[0]))


PHRASES = _phrase_table()


def find_polar_phrases(text: str) -> list[tuple[str, int]]:
    text = text.lower()
    used = [False] * len(text)
    hits = []
    for phrase, pol in PHRASES:
        start = text.find(phrase)
        while start != -1:
            end = start + len(phrase)
            if not any(used[start:end]):
                hits.append((phrase, pol))
                for i in range(start, end):
                    used[i] = True
            start = text.find(phrase, end)
    return hits


def keyword_sentiment(text: str) -> str:
    score = sum(pol for _, pol in find_polar_phrases(text))
    return "positive" if score > 0 else "negative" if score < 0 else "neutral"


def keyword_aspects(text: str) -> list[str]:
    t = text.lower()
    return [a for a in ASPECTS if any(k.lower() in t for k in ASPECT_KEYWORDS[a])]


def rating_sentiment(rating: int) -> str:
    return "positive" if rating >= 4 else "neutral" if rating == 3 else "negative"
