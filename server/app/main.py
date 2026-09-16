from __future__ import annotations

import os
import uuid
from io import BytesIO
from typing import Any

import fitz
import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import create_token, current_user, db_session, password_hash
from .db import ChatMessage, StudyNote, User
from .rag import chunk_document, lexical_retrieve
from .vector_store import index_chunks, semantic_search

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.0-flash")
ALLOWED_ORIGINS=[x.strip() for x in os.getenv("ALLOWED_ORIGINS","http://localhost:5173").split(",") if x.strip()]
app=FastAPI(title="StudentAI API",version="1.3.0",description="AI-powered RAG study assistant API")
app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

class ChatRequest(BaseModel):
    question:str
    context:str=""
    document_id:str|None=None
    task:str="answer"
    use_retrieval:bool=True
    semantic:bool=True
class ChatResponse(BaseModel):
    answer:str
    model:str
    used_ai:bool
    sources:list[dict[str,Any]]=[]
class AuthRequest(BaseModel):
    email:str
    password:str
class NoteRequest(BaseModel):
    title:str
    content:str


def offline_answer(question:str)->str:
    q=question.lower()
    if "supervised" in q:return "Supervised learning trains a model with labelled examples. Classification predicts categories, while regression predicts numerical values."
    if "big data" in q:return "Big Data refers to datasets whose volume, velocity, variety, veracity or value create challenges for conventional systems."
    if "stack" in q:return "A stack follows LIFO (Last In, First Out). Common operations are push, pop and peek."
    return "StudentAI is running in offline mode. Configure GEMINI_API_KEY on the backend to enable real AI responses."

def build_prompt(req:ChatRequest,retrieved:str="")->str:
    task={"answer":"Answer the student's question clearly and exam-ready.","summary":"Create a structured exam-ready summary with key concepts, definitions, formulas or steps, and likely questions.","quiz":"Generate 5 multiple-choice questions with four options, the correct answer, and a one-line explanation.","notes":"Turn the supplied material into concise revision notes with headings and bullet points."}.get(req.task,"Answer the student's question clearly.")
    return f"""You are StudentAI, a university study assistant. {task}
Use retrieved study material when present. Cite page numbers as [Page N] when supported. Never invent a citation. If the material does not contain the answer, say that clearly.

RETRIEVED SOURCES:\n{retrieved[:30000]}\n\nSTUDENT QUESTION:\n{req.question}"""

async def gemini(prompt:str)->str:
    if not GEMINI_API_KEY:return ""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=90) as client:r=await client.post(url,params={"key":GEMINI_API_KEY},json={"contents":[{"parts":[{"text":prompt}]}]})
    if r.status_code>=400:
        try:detail=r.json().get("error",{}).get("message","Gemini request failed")
        except Exception:detail="Gemini request failed"
        raise HTTPException(status_code=502,detail=detail)
    data:dict[str,Any]=r.json();parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[]);answer="".join(p.get("text","") for p in parts).strip()
    if not answer:raise HTTPException(status_code=502,detail="Gemini returned an empty response")
    return answer

@app.get("/api/health")
async def health():return {"status":"ok","service":"StudentAI API","ai_configured":bool(GEMINI_API_KEY),"vector_store":"chroma","database":os.getenv("DATABASE_URL","sqlite")[:30]}

@app.post("/api/auth/register")
def register(data:AuthRequest,db:Session=Depends(db_session)):
    email=data.email.strip().lower()
    if len(data.password)<8:raise HTTPException(400,"Password must contain at least 8 characters")
    if db.scalar(select(User).where(User.email==email)):raise HTTPException(409,"Email already registered")
    user=User(email=email,password_hash=password_hash.hash(data.password));db.add(user);db.commit();db.refresh(user)
    return {"access_token":create_token(user.id),"token_type":"bearer","user":{"id":user.id,"email":user.email}}

@app.post("/api/auth/login")
def login(data:AuthRequest,db:Session=Depends(db_session)):
    user=db.scalar(select(User).where(User.email==data.email.strip().lower()))
    if not user or not password_hash.verify(data.password,user.password_hash):raise HTTPException(401,"Invalid email or password")
    return {"access_token":create_token(user.id),"token_type":"bearer","user":{"id":user.id,"email":user.email}}

@app.get("/api/auth/me")
def me(user:User=Depends(current_user)):return {"id":user.id,"email":user.email}

@app.post("/api/chat",response_model=ChatResponse)
async def chat(request:ChatRequest,user:User|None=Depends(lambda:None),db:Session=Depends(db_session)):
    if not request.question.strip():raise HTTPException(400,"Question is required")
    sources=[];retrieved=request.context
    if request.context and request.use_retrieval:
        chunks=chunk_document(request.context)
        if request.semantic and GEMINI_API_KEY:
            try:hits=await semantic_search(request.question,request.document_id);sources=[{"page":h["page"],"preview":h["text"][:240],"distance":h["distance"]} for h in hits];retrieved="\n\n".join(f"[Page {h['page']}]\n{h['text']}" for h in hits)
            except Exception: hits=lexical_retrieve(request.question,chunks);sources=[{"page":c.page,"preview":c.text[:240]} for c in hits];retrieved="\n\n".join(f"[Page {c.page}]\n{c.text}" for c in hits)
        else:hits=lexical_retrieve(request.question,chunks);sources=[{"page":c.page,"preview":c.text[:240]} for c in hits];retrieved="\n\n".join(f"[Page {c.page}]\n{c.text}" for c in hits)
    answer=await gemini(build_prompt(request,retrieved));return ChatResponse(answer=answer or offline_answer(request.question),model=GEMINI_MODEL if answer else "offline",used_ai=bool(answer),sources=sources)

@app.post("/api/notes")
def create_note(data:NoteRequest,user:User=Depends(current_user),db:Session=Depends(db_session)):
    note=StudyNote(user_id=user.id,title=data.title,content=data.content);db.add(note);db.commit();db.refresh(note);return {"id":note.id,"title":note.title,"content":note.content}

@app.get("/api/notes")
def list_notes(user:User=Depends(current_user),db:Session=Depends(db_session)):
    return [{"id":n.id,"title":n.title,"content":n.content,"created_at":n.created_at.isoformat()} for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id).order_by(StudyNote.updated_at.desc())).all()]

@app.delete("/api/notes/{note_id}")
def delete_note(note_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    note=db.scalar(select(StudyNote).where(StudyNote.id==note_id,StudyNote.user_id==user.id))
    if not note:raise HTTPException(404,"Note not found")
    db.delete(note);db.commit();return {"deleted":True}

@app.post("/api/pdf/extract")
async def extract_pdf(file:UploadFile=File(...)):
    if file.content_type!="application/pdf" and not (file.filename or "").lower().endswith(".pdf"):raise HTTPException(400,"Please upload a PDF file")
    raw=await file.read()
    if len(raw)>20*1024*1024:raise HTTPException(413,"PDF must be smaller than 20 MB")
    try:
        doc=fitz.open(stream=BytesIO(raw),filetype="pdf");pages=[p.get_text("text") for p in doc];text="\n\n".join(f"PAGE {i+1}\n{v}" for i,v in enumerate(pages)).strip();document_id=str(uuid.uuid4());chunks=chunk_document(text);indexed=0
        if GEMINI_API_KEY:
            try:indexed=await index_chunks(document_id,[{"page":c.page,"text":c.text} for c in chunks])
            except Exception:indexed=0
        return {"document_id":document_id,"filename":file.filename,"pages":len(pages),"characters":len(text),"chunks":len(chunks),"indexed_chunks":indexed,"text":text[:150000]}
    except Exception as exc:raise HTTPException(422,f"Could not read PDF: {exc}") from exc

@app.post("/api/pdf/study",response_model=ChatResponse)
async def study_pdf(request:ChatRequest)->ChatResponse:request.task=request.task or "summary";return await chat(request)

@app.get("/api/documents/{document_id}/search")
async def search_document(document_id:str,q:str,top_k:int=5):
    if not GEMINI_API_KEY:raise HTTPException(503,"Semantic search requires GEMINI_API_KEY")
    try:return {"results":await semantic_search(q,document_id,max(1,min(top_k,10)))}
    except Exception as exc:raise HTTPException(502,str(exc)) from exc
