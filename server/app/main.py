from __future__ import annotations

import os
from io import BytesIO
from typing import Any

import fitz
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if x.strip()]

app = FastAPI(title="StudentAI API", version="1.0.0", description="AI-powered study assistant API")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    question: str
    context: str = ""
    task: str = "answer"

class ChatResponse(BaseModel):
    answer: str
    model: str
    used_ai: bool


def offline_answer(question: str) -> str:
    q = question.lower()
    if "supervised" in q:
        return "Supervised learning trains a model with labelled examples. Classification predicts categories, while regression predicts numerical values."
    if "big data" in q:
        return "Big Data refers to datasets whose volume, velocity, variety, veracity or value create challenges for conventional systems."
    if "stack" in q:
        return "A stack follows LIFO (Last In, First Out). Common operations are push, pop and peek."
    return "StudentAI is running in offline mode. Configure GEMINI_API_KEY on the backend to enable real AI responses."


def build_prompt(req: ChatRequest) -> str:
    task = {
        "answer": "Answer the student's question clearly and exam-ready.",
        "summary": "Create a structured exam-ready summary with key concepts, definitions, formulas or steps, and likely questions.",
        "quiz": "Generate 5 multiple-choice questions with four options, the correct answer, and a one-line explanation.",
        "notes": "Turn the supplied material into concise revision notes with headings and bullet points.",
    }.get(req.task, "Answer the student's question clearly.")
    return f"""You are StudentAI, a university study assistant. {task}
Use the supplied study material when present. Do not invent facts that conflict with it.

STUDY MATERIAL:
{req.context[:120000]}

STUDENT QUESTION:
{req.question}
"""


async def gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, params={"key": GEMINI_API_KEY}, json=payload)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", "Gemini request failed")
        except Exception:
            detail = "Gemini request failed"
        raise HTTPException(status_code=502, detail=detail)
    data: dict[str, Any] = response.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    answer = "".join(part.get("text", "") for part in parts).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response")
    return answer


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    return {"status": "ok", "service": "StudentAI API", "ai_configured": bool(GEMINI_API_KEY)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    answer = await gemini(build_prompt(request))
    if answer:
        return ChatResponse(answer=answer, model=GEMINI_MODEL, used_ai=True)
    return ChatResponse(answer=offline_answer(question), model="offline", used_ai=False)


@app.post("/api/pdf/extract")
async def extract_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF must be smaller than 20 MB")
    try:
        doc = fitz.open(stream=BytesIO(raw), filetype="pdf")
        pages = [page.get_text("text") for page in doc]
        text = "\n\n".join(f"PAGE {i + 1}\n{value}" for i, value in enumerate(pages)).strip()
        return {"filename": file.filename, "pages": len(pages), "characters": len(text), "text": text[:150000]}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {exc}") from exc


@app.post("/api/pdf/study", response_model=ChatResponse)
async def study_pdf(request: ChatRequest) -> ChatResponse:
    request.task = request.task or "summary"
    answer = await gemini(build_prompt(request))
    if not answer:
        answer = "PDF text was received. Configure GEMINI_API_KEY to generate an AI summary."
    return ChatResponse(answer=answer, model=GEMINI_MODEL if GEMINI_API_KEY else "offline", used_ai=bool(GEMINI_API_KEY))
