# ReviewLens

LLM-powered analysis of 300 Thai restaurant reviews (Wongnai corpus, LGPL-3.0) with the course
model `gemma-4-E4B-it`: structured sentiment/aspect extraction with verbatim evidence, an
allow-listed tool-calling agent, and a FastAPI + HTML/JS app. A full README follows in a later milestone.

## Run locally (Windows PowerShell)

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then put your course key and base URL in .env (never commit it)
python -m pytest -q
uvicorn app.main:app --reload   # open http://127.0.0.1:8000
```
