# JARVIS 4.0 — Personal AI Study & Productivity Assistant

JARVIS 4.0 is a full-stack personal AI assistant built for study, coding, documents and productivity. Its architecture is inspired by the composable ideas behind local-first systems such as OpenJarvis, while keeping JARVIS focused on a student's workflow.

## Architecture

```text
React + Vite UI
      ↓
FastAPI API
      ↓
JARVIS Agent Router
      ├── Study
      ├── PDF / RAG
      ├── Quiz
      ├── Planner
      ├── Coding
      └── General
      ↓
Tools + Memory
      ├── Safe calculator tool
      ├── Notes / chat history
      ├── Study analytics
      └── Chroma document retrieval
      ↓
AI Engine
      ├── Gemini
      ├── Ollama / local models
      └── Offline fallback
```

## Current features

- JARVIS agent routing for study, PDF, quiz, planner, coding and general requests
- Gemini cloud AI with a pluggable Ollama local-engine path
- Safe calculator tool registry; no arbitrary shell execution
- Authenticated PDF upload and page-aware RAG retrieval
- ChromaDB semantic retrieval with lexical fallback
- Exam-ready summaries, notes, quizzes and flashcards
- Persistent chat history and personal notes
- Subject management and study planning
- Progress analytics and study events
- JWT authentication with Argon2 password hashing
- User-scoped document isolation
- Docker Compose development and production stacks
- GitHub Actions CI for backend, frontend and Docker builds

## Windows setup

Clone the current repository:

```powershell
git clone https://github.com/tejeshdimmiti5-crypto/JARVIS4.0.git
cd JARVIS4.0
```

### Backend

```powershell
cd server
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Set `GEMINI_API_KEY` and a strong `JWT_SECRET` in `server/.env` for cloud AI.

### Optional local AI

Install Ollama and pull a model, then configure:

```env
AI_ENGINE=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

For automatic selection:

```env
AI_ENGINE=auto
```

JARVIS uses Gemini when `GEMINI_API_KEY` is available and otherwise can use the configured Ollama endpoint.

### Frontend

Open a second PowerShell:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

### Docker

From the repository root:

```powershell
docker compose up --build
```

The production stack is:

```powershell
docker compose -f docker-compose.prod.yml up --build -d
```

Swagger API docs: `http://localhost:8000/docs`

## API highlights

- `GET /api/health`
- `POST /api/chat`
- `GET /api/tools`
- `POST /api/tools/execute`
- `POST /api/pdf/extract`
- `POST /api/pdf/study`
- `GET /api/documents`
- `GET /api/documents/{document_id}/search`
- `POST /api/flashcards/generate`
- `GET /api/analytics/summary`
- `GET /api/study/tasks`

## Security

- PDF upload and document operations require authentication.
- Documents are scoped to their owning user.
- Tool execution is restricted to the registered tool catalog.
- The calculator uses an AST allowlist and does not execute Python code.
- Never commit `.env`, API keys, passwords, tokens or database credentials.

## Project direction

JARVIS is being built as a modular personal assistant rather than a single chatbot. The next expansion points are richer memory, additional safe tools, streaming responses, scheduled workflows and deeper local-model support.
