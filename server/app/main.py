from __future__ import annotations
import os,uuid
from io import BytesIO
from typing import Any
import fitz,httpx
from fastapi import Depends,FastAPI,File,HTTPException,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from .auth import create_token,current_user,db_session,optional_user,password_hash
from .db import ChatMessage,StudyNote,User
from .rag import chunk_document,lexical_retrieve
from .study import PlanInput,make_plan
from .vector_store import index_chunks,semantic_search
GEMINI_API_KEY=os.getenv('GEMINI_API_KEY','');GEMINI_MODEL=os.getenv('GEMINI_MODEL','gemini-2.0-flash');ALLOWED_ORIGINS=[x.strip() for x in os.getenv('ALLOWED_ORIGINS','http://localhost:5173').split(',') if x.strip()]
app=FastAPI(title='StudentAI API',version='1.5.0',description='AI-powered RAG study assistant API');app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
class ChatRequest(BaseModel):question:str;context:str='';document_id:str|None=None;task:str='answer';use_retrieval:bool=True;semantic:bool=True
class ChatResponse(BaseModel):answer:str;model:str;used_ai:bool;sources:list[dict[str,Any]]=[]
class AuthRequest(BaseModel):email:str;password:str
class NoteRequest(BaseModel):title:str;content:str

def offline_answer(q:str)->str:
 q=q.lower()
 if 'supervised' in q:return 'Supervised learning trains a model with labelled examples. Classification predicts categories, while regression predicts numerical values.'
 if 'big data' in q:return 'Big Data refers to datasets whose volume, velocity, variety, veracity or value create challenges for conventional systems.'
 if 'stack' in q:return 'A stack follows LIFO (Last In, First Out). Common operations are push, pop and peek.'
 return 'StudentAI is running in offline mode. Configure GEMINI_API_KEY on the backend to enable real AI responses.'
def build_prompt(req:ChatRequest,retrieved:str='')->str:
 task={'answer':'Answer the student clearly and exam-ready.','summary':'Create an exam-ready summary with key concepts, definitions, formulas or steps, and likely questions.','quiz':'Generate 5 MCQs with four options, the correct answer, and a one-line explanation.','notes':'Create concise revision notes with headings and bullet points.','flashcards':'Create 10 study flashcards. Format each as Q: question / A: answer.'}.get(req.task,'Answer the student clearly.')
 return f'You are StudentAI, a university study assistant. {task}\nUse retrieved material when present. Cite supporting pages as [Page N]. Never invent citations.\n\nRETRIEVED:\n{retrieved[:30000]}\n\nQUESTION:\n{req.question}'
async def gemini(prompt:str)->str:
 if not GEMINI_API_KEY:return ''
 url=f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
 async with httpx.AsyncClient(timeout=90) as c:r=await c.post(url,params={'key':GEMINI_API_KEY},json={'contents':[{'parts':[{'text':prompt}]}]})
 if r.status_code>=400:raise HTTPException(502,'Gemini request failed')
 parts=r.json().get('candidates',[{}])[0].get('content',{}).get('parts',[]);a=''.join(p.get('text','') for p in parts).strip()
 if not a:raise HTTPException(502,'Gemini returned an empty response')
 return a
@app.get('/api/health')
async def health():return {'status':'ok','service':'StudentAI API','ai_configured':bool(GEMINI_API_KEY),'vector_store':'chroma','database':bool(os.getenv('DATABASE_URL'))}
@app.post('/api/auth/register')
def register(data:AuthRequest,db:Session=Depends(db_session)):
 email=data.email.strip().lower()
 if len(data.password)<8:raise HTTPException(400,'Password must contain at least 8 characters')
 if db.scalar(select(User).where(User.email==email)):raise HTTPException(409,'Email already registered')
 u=User(email=email,password_hash=password_hash.hash(data.password));db.add(u);db.commit();db.refresh(u);return {'access_token':create_token(u.id),'token_type':'bearer','user':{'id':u.id,'email':u.email}}
@app.post('/api/auth/login')
def login(data:AuthRequest,db:Session=Depends(db_session)):
 u=db.scalar(select(User).where(User.email==data.email.strip().lower()))
 if not u or not password_hash.verify(data.password,u.password_hash):raise HTTPException(401,'Invalid email or password')
 return {'access_token':create_token(u.id),'token_type':'bearer','user':{'id':u.id,'email':u.email}}
@app.get('/api/auth/me')
def me(user:User=Depends(current_user)):return {'id':user.id,'email':user.email}
async def run_chat(req:ChatRequest)->tuple[str,list[dict[str,Any]]]:
 sources=[];retrieved=req.context
 if req.context and req.use_retrieval:
  chunks=chunk_document(req.context)
  try:hits=await semantic_search(req.question,req.document_id) if req.semantic and GEMINI_API_KEY else lexical_retrieve(req.question,chunks)
  except Exception:hits=lexical_retrieve(req.question,chunks)
  if hits and hasattr(hits[0],'text'):sources=[{'page':h.page,'preview':h.text[:240]} for h in hits];retrieved='\n\n'.join(f'[Page {h.page}]\n{h.text}' for h in hits)
  else:sources=[{'page':h['page'],'preview':h['text'][:240],'distance':h.get('distance')} for h in hits];retrieved='\n\n'.join(f"[Page {h['page']}]\n{h['text']}" for h in hits)
 a=await gemini(build_prompt(req,retrieved));return (a or offline_answer(req.question)),sources
@app.post('/api/chat',response_model=ChatResponse)
async def chat(req:ChatRequest,user:User|None=Depends(optional_user),db:Session=Depends(db_session)):
 if not req.question.strip():raise HTTPException(400,'Question is required')
 a,sources=await run_chat(req)
 if user:db.add_all([ChatMessage(user_id=user.id,role='user',content=req.question),ChatMessage(user_id=user.id,role='assistant',content=a)]);db.commit()
 return ChatResponse(answer=a,model=GEMINI_MODEL if GEMINI_API_KEY else 'offline',used_ai=bool(GEMINI_API_KEY),sources=sources)
@app.get('/api/chat/history')
def history(limit:int=50,user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id).order_by(ChatMessage.created_at.desc()).limit(max(1,min(limit,200)))).all();return [{'id':x.id,'role':x.role,'content':x.content,'created_at':x.created_at.isoformat()} for x in reversed(rows)]
@app.delete('/api/chat/history')
def clear_history(user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id)).all()
 for x in rows:db.delete(x)
 db.commit();return {'deleted':len(rows)}
@app.post('/api/study/plan')
def study_plan(data:PlanInput,user:User=Depends(current_user)):return make_plan(data)
@app.post('/api/notes')
def create_note(data:NoteRequest,user:User=Depends(current_user),db:Session=Depends(db_session)):
 n=StudyNote(user_id=user.id,title=data.title,content=data.content);db.add(n);db.commit();db.refresh(n);return {'id':n.id,'title':n.title,'content':n.content}
@app.get('/api/notes')
def list_notes(user:User=Depends(current_user),db:Session=Depends(db_session)):
 return [{'id':n.id,'title':n.title,'content':n.content,'created_at':n.created_at.isoformat()} for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id).order_by(StudyNote.updated_at.desc())).all()]
@app.delete('/api/notes/{note_id}')
def delete_note(note_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
 n=db.scalar(select(StudyNote).where(StudyNote.id==note_id,StudyNote.user_id==user.id))
 if not n:raise HTTPException(404,'Note not found')
 db.delete(n);db.commit();return {'deleted':True}
@app.post('/api/pdf/extract')
async def extract_pdf(file:UploadFile=File(...)):
 if file.content_type!='application/pdf' and not (file.filename or '').lower().endswith('.pdf'):raise HTTPException(400,'Please upload a PDF file')
 raw=await file.read()
 if len(raw)>20*1024*1024:raise HTTPException(413,'PDF must be smaller than 20 MB')
 try:
  doc=fitz.open(stream=BytesIO(raw),filetype='pdf');pages=[p.get_text('text') for p in doc];text='\n\n'.join(f'PAGE {i+1}\n{v}' for i,v in enumerate(pages)).strip();did=str(uuid.uuid4());chunks=chunk_document(text);indexed=0
  if GEMINI_API_KEY:
   try:indexed=await index_chunks(did,[{'page':c.page,'text':c.text} for c in chunks])
   except Exception:pass
  return {'document_id':did,'filename':file.filename,'pages':len(pages),'characters':len(text),'chunks':len(chunks),'indexed_chunks':indexed,'text':text[:150000]}
 except Exception as e:raise HTTPException(422,f'Could not read PDF: {e}') from e
@app.post('/api/pdf/study',response_model=ChatResponse)
async def study_pdf(req:ChatRequest):req.task=req.task or 'summary';a,s=await run_chat(req);return ChatResponse(answer=a,model=GEMINI_MODEL if GEMINI_API_KEY else 'offline',used_ai=bool(GEMINI_API_KEY),sources=s)
@app.get('/api/documents/{document_id}/search')
async def search_document(document_id:str,q:str,top_k:int=5):
 if not GEMINI_API_KEY:raise HTTPException(503,'Semantic search requires GEMINI_API_KEY')
 try:return {'results':await semantic_search(q,document_id,max(1,min(top_k,10)))}
 except Exception as e:raise HTTPException(502,str(e)) from e
