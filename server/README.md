# JARVIS Backend

FastAPI service for the JARVIS study assistant.

## Run locally

```bash
cd server
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive API documentation.

## Environment

Set `GEMINI_API_KEY` in `.env`. Never commit the real key. `GEMINI_MODEL` can be changed without editing code.

## API

- `GET /api/health` — service status
- `POST /api/chat` — AI/offline study chat
- `POST /api/pdf/extract` — PDF text extraction
- `POST /api/pdf/study` — AI study response from extracted PDF text
