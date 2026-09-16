# StudentAI — AI-Powered RAG Study Assistant

StudentAI is a full-stack study workspace designed for university students. It combines a React frontend with a FastAPI AI backend to turn lecture material into interactive study sessions.

## What it does

- 🤖 AI study chat with Gemini
- 📄 PDF upload and server-side text extraction
- ✨ Exam-ready PDF summaries
- 🧠 AI-generated quiz prompts
- 📝 Personal revision notes
- 📊 Local study activity dashboard
- 🔐 API keys stay on the backend in `.env`
- 🐳 Docker Compose development environment
- ✅ GitHub Actions CI for backend tests and frontend builds

## Architecture

```text
React + Vite
     │
     ▼
FastAPI REST API ──────► Gemini API
     │
     └────────► PyMuPDF PDF extraction
```

## Tech stack

**Frontend:** React, JavaScript, Vite, Lucide Icons  
**Backend:** Python, FastAPI, Pydantic, HTTPX  
**AI:** Gemini API  
**PDF:** PyMuPDF  
**DevOps:** Docker Compose, GitHub Actions  

## Run locally

### 1. Backend

```bash
cd server
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Put your Gemini API key in `server/.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### 2. Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL shown in the terminal, normally `http://localhost:5173`.

### 3. Docker

```bash
copy server/.env.example server/.env
# add GEMINI_API_KEY to server/.env
docker compose up --build
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend health check |
| POST | `/api/chat` | AI study chat |
| POST | `/api/pdf/extract` | Extract PDF text |
| POST | `/api/pdf/study` | Generate an AI study response from PDF text |

Interactive API docs are available at `http://localhost:8000/docs`.

## Resume project description

**StudentAI — AI-Powered RAG Study Assistant**  
Built a full-stack AI study platform using React and FastAPI with Gemini-powered academic Q&A, PDF ingestion through PyMuPDF, exam-ready summarization, quiz generation, local progress tracking, Dockerized development, and GitHub Actions CI. The architecture is designed to evolve toward semantic chunking, embeddings, vector search, citations, authentication, and persistent PostgreSQL storage.

## Security

Never commit `.env`, API keys, tokens, or credentials. The production architecture keeps the Gemini credential server-side rather than exposing it in browser code.
