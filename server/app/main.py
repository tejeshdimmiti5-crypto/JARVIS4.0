from __future__ import annotations

import os
from io import BytesIO
from typing import Any

import fitz
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rag import chunk_document, lexical_retrieve

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app = FastAPI(title="StudentAI API", version="1.1.0", description="AI-powered RAG study assistant API")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    question: str
    context: str = ""
    task: str = "answer"
    use_retrieval: bool = True

class ChatResponse(BaseModel):
    answer: str
    model: str
    used_ai: bool
    sources: list[dict[str, Any]] = []


def offline_answer(question: str) -> str:
    q = question.lower()
    if "supervised" in q: return "Supervised learning trains a model with labelled examples. Classification predicts categories, while regression predicts numerical values."
    if "big data" in q: return "Big Data refers to datasets whose volume, velocity, variety, veracity or value create challenges for conventional systems."
    if "stack" in q: return "A stack follows LIFO (Last In, First Out). Common operations are push, pop and peek."
    return "StudentAI is running in offline mode. Configure GEMINI_API_KEY on the backend to enable real AI responses."


def build_prompt(req: ChatRequest, retrieved: str = "") -> str:
    task = {"answer":"Answer the student's question clearly and exam-ready.","summary":"Create a structured exam-ready summary with key concepts, definitions, formulas or steps, and likely questions.","quiz":"Generate 5 multiple-choice questions with four options, the correct answer, and a one-line explanation.","notes":"Turn the supplied material into concise revision notes with headings and bullet points."}.get(req.task, "Answer the student's question clearly.")
    return f"""You are StudentAI, a university study assistant. {task}
Use the retrieved study material when present. Cite page numbers like [Page 3] when a source supports your answer. If the material does not contain the answer, clearly say so rather than inventing a source.

RETRIEVED SOURCES:
{retrieved[:30000]}

STUDENT QUESTION:
{req.question}
"""

async def gemini(prompt: str) -> str:
    if not GEMINI_API_KEY: return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, params={"key": GEMINI_API_KEY}, json={"contents":[{"parts":[{"text":prompt}]}]})
    if response.status_code >= 400:
        try: detail = response.json().get("error", {}).get("message", "Gemini request failed")
        except Exception: detail = "Gemini request failed"
        raise HTTPException(status_code=502, detail=detail)
    data: dict[str, Any] = response.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    answer = "".join(part.get("text", "") for part in parts).strip()
    if not answer: raise HTTPException(status_code=502, detail="Gemini returned an empty response")
    return answer

@app.get("/api/health")
async def health() -> dict[str, str | bool]: return {"status":"ok","service":"StudentAI API","ai_configured":bool(GEMINI_API_KEY)}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question: raise HTTPException(status_code=400, detail="Question is required")
    sources=[]; retrieved=request.context
    if request.context and request.use_retrieval:
        chunks=chunk_document(request.context); hits=lexical_retrieve(question,chunks)
        sources=[{"page":c.page,"preview":c.text[:240]} for c in hits]
        retrieved="\n\n".join(f"[Page {c.page}]\n{c.text}" for c in hits)
    answer=await gemini(build_prompt(request,retrieved))
    return ChatResponse(answer=answer or offline_answer(question),model=GEMINI_MODEL if answer else "offline",used_ai=bool(answer),sources=sources)

@app.post("/api/pdf/extract")
async def extract_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"): raise HTTPException(status_code=400, detail="Please upload a PDF file")
    raw=await file.read()
    if len(raw)>20*1024*1024: raise HTTPException(status_code=413, detail="PDF must be smaller than 20 MB")
    try:
        doc=fitz.open(stream=BytesIO(raw),filetype="pdf"); pages=[page.get_text("text") for page in doc]
        text="\n\n".join(f"PAGE {i+1}\n{value}" for i,value in enumerate(pages)).strip()
        return {"filename":file.filename,"pages":len(pages),"characters":len(text),"chunks":len(chunk_document(text)),"text":text[:150000]}
    except Exception as exc: raise HTTPException(status_code=422,detail=f"Could not read PDF: {exc}") from exc

@app.post("/api/pdf/study", response_model=ChatResponse)
async def study_pdf(request: ChatRequest) -> ChatResponse:
    request.task=request.task or "summary"
    return await chat(request)
