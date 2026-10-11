# JARVIS 4.0 — Friend Review Guide

Thanks for reviewing JARVIS 4.0. Please review it as a student project / technical MVP, and report usability issues, reproducible bugs, security concerns, and the highest-value improvements. Do not assume that every AI feature works without provider configuration.

## Project links

- **Repository:** https://github.com/tejeshdimmiti5-crypto/JARVIS4.0
- **Live frontend:** https://jarvis-ui-6eu8.onrender.com
- **Backend health/API:** https://jarvis-api-sum5.onrender.com/api/health
- **Interactive API documentation (when the backend is awake):** https://jarvis-api-sum5.onrender.com/docs
- **CI runs:** https://github.com/tejeshdimmiti5-crypto/JARVIS4.0/actions
- **Open PRs to review separately:** https://github.com/tejeshdimmiti5-crypto/JARVIS4.0/pulls

Render free services may sleep after inactivity, so the first page/API request can take a while. If the live service does not respond, review the source locally as well.

## What the project is

JARVIS 4.0 is a full-stack AI study and productivity assistant. The frontend is React + Vite, the API is FastAPI, persistent app data uses SQLAlchemy/PostgreSQL, document retrieval uses a RAG pipeline with ChromaDB and lexical fallback, and text generation can use Gemini or a local Ollama model. An offline fallback supports only limited deterministic help; it is not a substitute for an available LLM.

## Main modules

- Account registration/login and user-scoped personal data
- Chat and study explanations
- PDF extraction and document-grounded study with retrieval
- Personal notes and subject/task planning
- Flashcard generation, persistence, and review counts
- Activity/progress analytics
- Browser voice input/output where supported
- Registered tools (rather than arbitrary shell execution)
- Docker Compose and Render deployment configurations

## Suggested review flow

1. Open the live website on desktop and mobile. Check navigation, loading states, sign-in, and error messages.
2. Create a test account using a non-sensitive test password. Do not use a password you use elsewhere.
3. Try a basic chat prompt such as “Explain a stack and give a short example.” Check that the UI accurately indicates whether the reply came from an AI provider or offline fallback.
4. Upload a small, non-sensitive sample PDF. Ask a question about it and verify that any cited page numbers actually support the answer.
5. Try notes, subjects/study planning, flashcard generation/review, and progress analytics.
6. Verify privacy boundaries with two separate test accounts. One account must not access the other's documents, notes, or flashcards.
7. Check responsive layout, keyboard navigation, empty states, failed-provider behavior, and refresh/session behavior.
8. Read the tests and workflows before suggesting large rewrites. Report specific file paths, steps to reproduce, expected behavior, and actual behavior.

## Run locally (Windows PowerShell)

Prerequisites: Git, Python 3.12, Node.js 22+, and optionally Docker Desktop. Use your own provider key only if you wish to test live Gemini generation.

```powershell
git clone https://github.com/tejeshdimmiti5-crypto/JARVIS4.0.git
cd JARVIS4.0

# Backend
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit server/.env locally; never commit it.
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Open a second terminal:

```powershell
cd JARVIS4.0\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend normally runs at http://localhost:5173 and the API at http://localhost:8000. For local Gemini testing, set `GEMINI_API_KEY` and a currently supported `GEMINI_MODEL` in `server/.env`. For local-model testing, install/start Ollama separately and configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

### Run automated checks

From the repository root:

```powershell
cd server
python -m pip install pytest
python -m pip check
python -m compileall app tests
alembic upgrade head
python -m pytest -q
```

The frontend can be checked with:

```powershell
cd frontend
npm install
npm run build
```

## Current review notes / known limitations

- AI responses depend on the model/provider and environment configuration. Without a provider, the offline mode offers limited deterministic responses only.
- Provider/model identifiers can age; confirm the configured Gemini model is currently available to your key.
- The open pull requests are not part of `main` until merged. Review them separately rather than assuming their changes are in the current app.
- The CI history has shown a flashcard-generation test failure when the AI provider is unavailable. A fallback fix has been committed; check the latest GitHub Actions result before concluding this issue is resolved.
- Document parsing and generated answers can be wrong. Confirm page citations against the original PDF.
- Verify database backups, persistent disk/database setup, token expiry, request rate limits, and production secret rotation before using real user data.
- Voice features depend on browser/device speech APIs and permissions.
- The application is an evolving student project, not a security-certified or production-audited service.

## Feedback format

Please send feedback in this format:

- **Finding:** one-line summary
- **Severity:** blocker / high / medium / low
- **Environment:** browser/OS, local or live
- **Steps to reproduce:** numbered steps
- **Expected vs actual:** what should happen and what happened
- **Evidence:** screenshot, API response, or relevant log (remove tokens, email addresses, and private document content)
- **Suggested fix:** if you have one

Please prioritise reproducible defects and privacy/security boundaries over cosmetic preferences. Do not publish test credentials, real API keys, private PDFs, or user data in screenshots or issue reports.
