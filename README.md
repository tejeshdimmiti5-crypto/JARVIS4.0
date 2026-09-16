# StudentAI — AI-Powered RAG Study Assistant

StudentAI is a full-stack AI study workspace for university students. It combines React, FastAPI, Gemini, semantic retrieval, ChromaDB and PostgreSQL to turn lecture material into an interactive study system.

## Features

- 🤖 Gemini-powered academic Q&A
- 📄 PDF upload, extraction and page-aware chunking
- 🧠 Semantic RAG with Gemini embeddings + ChromaDB
- 🔎 Source/page-aware retrieval results
- ✨ Exam-ready summaries and revision notes
- 📝 Persistent personal notes
- ❓ AI quiz generation
- 🃏 Interactive AI flashcards
- 🗓️ 7-day study planner
- 💬 Persistent authenticated chat history
- 🔐 JWT authentication + Argon2 password hashing
- 🐘 PostgreSQL persistence with SQLite development fallback
- 📊 Study activity dashboard
- 🐳 Docker Compose environment
- ✅ Automated backend tests + frontend build CI

## Architecture

```text
React + Vite
     │
     ▼
FastAPI REST API ─────────► Gemini Generate Content
     │                         │
     ├── JWT + Argon2          └── Gemini Embeddings
     ├── PostgreSQL                 │
     ├── PyMuPDF                    ▼
     └── RAG pipeline ─────────► ChromaDB
```

## Tech stack

**Frontend:** React, JavaScript, Vite, Lucide Icons  
**Backend:** Python, FastAPI, Pydantic, HTTPX, SQLAlchemy  
**AI:** Gemini generation + embeddings  
**RAG:** ChromaDB, semantic retrieval, page-aware sources  
**PDF:** PyMuPDF  
**Database:** PostgreSQL / SQLite fallback  
**Security:** JWT, Argon2 password hashing, server-side API keys  
**DevOps:** Docker Compose, GitHub Actions

## Run locally

### Backend

```bash
cd server
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Configure `server/.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
JWT_SECRET=replace-with-a-long-random-secret
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

### Docker

```bash
docker compose up --build
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health/status check |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login and receive JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/chat` | AI study chat + RAG |
| GET | `/api/chat/history` | Persistent chat history |
| DELETE | `/api/chat/history` | Clear chat history |
| POST | `/api/pdf/extract` | Extract and index PDF |
| POST | `/api/pdf/study` | AI study response from PDF |
| GET | `/api/documents/{id}/search` | Semantic document search |
| POST | `/api/notes` | Save revision note |
| GET | `/api/notes` | List notes |
| DELETE | `/api/notes/{id}` | Delete note |
| POST | `/api/study/plan` | Generate a study plan |

Interactive Swagger docs: `http://localhost:8000/docs`

## Resume description

**StudentAI — AI-Powered RAG Study Assistant**  
Built a full-stack AI study platform using React and FastAPI with Gemini-powered academic Q&A, PDF ingestion through PyMuPDF, semantic retrieval with ChromaDB and Gemini embeddings, page-aware source tracking, JWT/Argon2 authentication, PostgreSQL persistence, AI quizzes and flashcards, a study planner, Dockerized development and GitHub Actions CI.

## Security

Never commit `.env`, API keys, tokens or database credentials. Gemini credentials remain server-side. Use strong secrets and managed database credentials in production.
