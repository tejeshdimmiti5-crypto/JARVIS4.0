# JARVIS — Personal AI Study & Productivity Assistant

JARVIS is the upgraded identity of this full-stack AI assistant. It combines React + Vite, FastAPI, Gemini, PDF/RAG retrieval, PostgreSQL/SQLite, ChromaDB, authentication, notes, quizzes, flashcards, study planning and progress tracking.

## Features

- Gemini AI conversation with offline fallback
- PDF upload, extraction and page-aware retrieval
- Semantic RAG with ChromaDB + Gemini embeddings
- Exam-ready summaries, notes and quizzes
- AI flashcards with review tracking
- Persistent chat history and personal notes
- Subject management and 7-day study planner
- Study analytics and streak tracking
- JWT authentication + Argon2 password hashing
- Docker Compose development stack
- Production frontend/backend container support

## Windows setup

Clone:

```powershell
git clone https://github.com/tejeshdimmiti5-crypto/chartbot___1.git
cd chartbot___1
```

Backend:

```powershell
cd server
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Set `server/.env` with your Gemini key and a strong JWT secret. The `alembic upgrade head` command creates/updates the local JARVIS database before the API starts.

Frontend (second PowerShell):

```powershell
cd chartbot___1/frontend
npm install
npm run dev
```

Open the Vite URL, normally http://localhost:5173.

Docker option from repository root:

```powershell
docker compose up --build
```

Docker automatically applies database migrations before starting the backend.

Swagger: http://localhost:8000/docs

## Security

Never commit `.env`, API keys, passwords, tokens or database credentials.

## Repository name

The repository is intentionally still named `chartbot___1` until local verification is complete. It can then be renamed to JARVIS without losing the Git history.
