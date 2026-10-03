# Student Wellness & Personality Reports

Enter a student's details, the AI (Google Gemini) writes the report, download it as a one-page A4 PDF.

## Run it
```
python -m venv .venv
.venv\Scripts\activate          (Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          (Mac: cp .env.example .env)  then add your GEMINI_API_KEY
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000** in Chrome.

## Pages
- `/` – all reports, search by name, filter by school and class
- `/new.html` – enter a student's details and generate the report
- `/report.html?id=1` – the finished report, with Download PDF and Rewrite with AI

API docs for testing: http://127.0.0.1:8000/docs

## Files
```
app/            backend (FastAPI)
  ai_service.py   the Gemini prompt and call
  schemas.py      form fields, trait list, personality types
  main.py         API routes, serves the frontend
  storage.py      student photos, kept in a private Supabase Storage bucket
frontend/       the web pages (plain HTML, CSS, JS)
  report.css      the report design
  report.js       builds the report from the data
```

## Changing things
- Trait checklist or personality types: edit the lists at the top of `app/schemas.py`
- How the AI writes: edit `SYSTEM_PROMPT` in `app/ai_service.py`
- Report colours and layout: `frontend/report.css`
