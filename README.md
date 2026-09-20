# JARVIS 4.0 🤖

> **Personal AI Study & Productivity Command Center**

JARVIS 4.0 is a full-stack AI study assistant designed to help students **learn, revise, organize, and track progress** from one workspace.

It combines a React/Vite interface, FastAPI backend, PostgreSQL persistence, document retrieval/RAG, Gemini or Ollama AI, authentication, study planning, flashcards, notes, quizzes, and analytics.

## ✨ What JARVIS can do

| Module | What it provides |
|---|---|
| 💬 JARVIS Chat | AI answers, exam explanations, revision help, command routing |
| 📄 PDF Study | Upload PDFs, extract text, index content, retrieve relevant pages |
| 🧠 RAG | Semantic retrieval with lexical fallback and page-aware sources |
| 📝 Notes | Personal revision notes stored per account |
| ❓ Quiz Me | Exam-style questions and AI-generated quizzes |
| 🃏 Flashcards | Generate, save, review, and track flashcards |
| 📅 Study Planner | Subjects, daily targets, exam dates, and 7-day plans |
| 📊 Progress | Questions, study time, tasks, notes, subjects, and daily activity |
| 🎙️ Voice | Browser speech input and spoken JARVIS replies when supported |
| 🔐 Accounts | JWT authentication with password hashing and user-scoped data |
| 🛠️ Safe Tools | Controlled tool registry instead of arbitrary shell execution |

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │     JARVIS UI        │
                         │   React + Vite       │
                         └──────────┬───────────┘
                                    │ REST / JSON
                         ┌──────────▼───────────┐
                         │     FastAPI API      │
                         │  Auth + Study APIs   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
      ┌───────▼───────┐    ┌────────▼────────┐   ┌──────▼───────┐
      │   AI Engine   │    │   RAG Pipeline  │   │  PostgreSQL  │
      │ Gemini/Ollama │    │ PDF → chunks →   │   │ users/data/  │
      │ + offline     │    │ retrieval → AI   │   │ analytics    │
      └───────────────┘    └─────────────────┘   └──────────────┘
                                    │
                              ┌─────▼─────┐
                              │ ChromaDB  │
                              └───────────┘
```

## 📁 Project structure

```text
JARVIS4.0/
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── server/
│   ├── app/
│   │   ├── main.py
│   │   ├── engine.py
│   │   ├── auth.py
│   │   ├── agents.py
│   │   ├── rag.py
│   │   ├── vector_store.py
│   │   ├── study.py
│   │   ├── flashcards.py
│   │   ├── analytics.py
│   │   ├── tools.py
│   │   ├── models.py
│   │   └── db.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
│
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── render.yaml
├── .env.example
└── README.md
```

## 🚀 Run locally on Windows

### 1. Clone

```powershell
git clone https://github.com/tejeshdimmiti5-crypto/JARVIS4.0.git
cd JARVIS4.0
```

### 2. Start the backend

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set your local values in `server/.env`. **Never commit this file.**

Then:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### 3. Start the frontend

Open a second PowerShell:

```powershell
cd JARVIS4.0\frontend
npm install
npm run dev
```

Frontend normally runs at:

```text
http://localhost:5173
```

Set `VITE_API_URL` when the API is not running on localhost.

## 🐳 Docker

Development:

```powershell
docker compose up --build
```

Production stack:

```powershell
docker compose -f docker-compose.prod.yml up --build -d
```

## 🔑 AI configuration

JARVIS supports a pluggable AI engine.

### Gemini

Configure:

```env
AI_ENGINE=auto
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=your_supported_gemini_model
```

### Ollama

For local AI:

```env
AI_ENGINE=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

For automatic selection, use:

```env
AI_ENGINE=auto
```

Keep API keys and secrets in environment variables only.

## 🔌 Important API routes

### Health & authentication
```text
GET  /api/health
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### AI & documents
```text
POST /api/chat
POST /api/pdf/extract
POST /api/pdf/study
GET  /api/documents
GET  /api/documents/{document_id}/search
```

### Study system
```text
GET  /api/notes
POST /api/notes
GET  /api/subjects
POST /api/subjects
POST /api/study/plan
GET  /api/study/tasks
```

### Flashcards & analytics
```text
POST /api/flashcards/generate
GET  /api/flashcards
POST /api/flashcards/{card_id}/review
GET  /api/analytics/summary
GET  /api/analytics/daily
GET  /api/preferences
PUT  /api/preferences
```

## 🔐 Security principles

- Authentication is required for private study data and document operations.
- Documents are checked against the authenticated user's ownership.
- Passwords are stored using a password-hashing scheme, not plaintext.
- Tool execution uses a registered tool catalog.
- Calculator execution is restricted rather than running arbitrary Python.
- CORS is configured through environment variables.
- Secrets belong in `.env` or deployment environment variables.
- **Never commit Gemini/API keys, JWT secrets, database passwords, or tokens.**

## 🧪 Testing

Backend tests live in:

```text
server/tests/
```

Run them with:

```powershell
cd server
pytest
```

The repository also includes GitHub Actions CI for automated checks.

## 🌐 Deployment

The project contains deployment configuration for Render:

```text
render.yaml
docker-compose.prod.yml
server/Dockerfile
frontend/Dockerfile
```

The current project is structured so the frontend and backend can be deployed independently.

## 🗺️ Roadmap

- [x] AI chat
- [x] Authentication
- [x] PostgreSQL persistence
- [x] Alembic migrations
- [x] PDF extraction
- [x] RAG retrieval
- [x] Notes
- [x] Quiz generation
- [x] Flashcards
- [x] Study planner
- [x] Progress analytics
- [x] Voice input/output
- [x] Safe tool registry
- [x] Docker + CI configuration
- [ ] Streaming AI responses
- [ ] Richer long-term memory controls
- [ ] More study-agent workflows
- [ ] Better PDF reading UI
- [ ] Scheduled study reminders
- [ ] Expanded local-model support

## 👨‍💻 Project

**JARVIS 4.0**  
Built as a student-focused AI engineering project combining **AI + RAG + FastAPI + React + PostgreSQL + Docker**.

Repository: https://github.com/tejeshdimmiti5-crypto/JARVIS4.0

---

### ⚠️ Note

JARVIS is an evolving project. Some AI/provider capabilities depend on the configured model and environment. Always keep production secrets outside Git.
