from __future__ import annotations
import os,uuid
from datetime import date,datetime,timezone,timedelta
from io import BytesIO
from typing import Any
import fitz,httpx
from fastapi import Depends,FastAPI,File,HTTPException,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from sqlalchemy import delete,func,select
from sqlalchemy.orm import Session
from .auth import create_token,current_user,db_session,optional_user,password_hash
from .db import ChatMessage,StudyNote,User,Base,engine
from .models import DocumentRecord,StudyEvent,StudyTask,Subject,UserPreference
from .flashcards import FlashcardRecord
from .analytics import daily_summary
from .rag import chunk_document,lexical_retrieve
from .study import PlanInput,make_plan
from .vector_store import index_chunks,semantic_search
from .agents import route_agent
from .tools import list_tools,run_tool
from .engine import generate_text,selected_engine,OLLAMA_MODEL
GEMINI_API_KEY=os.getenv('GEMINI_API_KEY','');GEMINI_MODEL=os.getenv('GEMINI_MODEL','gemini-2.0-flash');ALLOWED_ORIGINS=[x.strip() for x in os.getenv('ALLOWED_ORIGINS','http://localhost:5173').split(',') if x.strip()]
app=FastAPI(title='JARVIS API',version='2.0.0',description='AI-powered RAG study assistant API');app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=True,allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'])
class ChatRequest(BaseModel):question:str=Field(min_length=1,max_length=12000);context:str=Field(default='',max_length=50000);document_id:str|None=None;task:str='answer';use_retrieval:bool=True;semantic:bool=True
class ChatResponse(BaseModel):answer:str;model:str;used_ai:bool;sources:list[dict[str,Any]]=Field(default_factory=list)
class AuthRequest(BaseModel):email:str;password:str
class NoteRequest(BaseModel):title:str=Field(min_length=1,max_length=200);content:str=Field(min_length=1,max_length=50000)
class Flashcard(BaseModel):question:str;answer:str
class FlashcardRequest(BaseModel):topic:str=Field(min_length=1,max_length=4000);count:int=Field(default=10,ge=1,le=30);document_id:str|None=None;context:str=Field(default='',max_length=50000)
class FlashcardResponse(BaseModel):cards:list[Flashcard];model:str;used_ai:bool
class SubjectRequest(BaseModel):name:str=Field(min_length=1,max_length=100);code:str=Field(default='',max_length=30);daily_minutes:int=Field(default=60,ge=15,le=480);exam_date:str|None=None
class TaskComplete(BaseModel):completed:bool
class ToolRequest(BaseModel):name:str=Field(min_length=1,max_length=100);arguments:dict[str,Any]=Field(default_factory=dict)

def event(db,user_id,event_type,minutes=0):db.add(StudyEvent(user_id=user_id,event_type=event_type,minutes=minutes));db.commit()
def offline_answer(q:str)->str:
 q=q.lower()
 if 'supervised' in q:return 'Supervised learning trains a model with labelled examples. Classification predicts categories, while regression predicts numerical values.'
 if 'big data' in q:return 'Big Data refers to datasets whose volume, velocity, variety, veracity or value create challenges for conventional systems.'
 if 'stack' in q:return 'A stack follows LIFO (Last In, First Out). Common operations are push, pop and peek.'
 return 'JARVIS is running in offline mode. Configure GEMINI_API_KEY on the backend to enable real AI responses.'
def build_prompt(req:ChatRequest,retrieved:str='')->str:
 agent=route_agent(req.question,req.task,req.document_id)
 agent_name=agent.name
 agent_instruction=agent.instruction
 task={'answer':'Answer the student clearly and exam-ready.','summary':'Create an exam-ready summary with key concepts, definitions, formulas or steps, and likely questions.','quiz':'Generate 5 MCQs with four options, the correct answer, and a one-line explanation.','notes':'Create concise revision notes with headings and bullet points.','flashcards':'Create 10 study flashcards. Format each as Q: question / A: answer.'}.get(req.task,'Answer the student clearly.')
 return f'You are JARVIS, a university study assistant. You are operating as the {agent_name} agent. {agent_instruction}\n{task}\nUse retrieved material when present. Cite supporting pages as [Page N]. Never invent citations.\n\nRETRIEVED:\n{retrieved[:30000]}\n\nQUESTION:\n{req.question}'
def memory_context(db:Session,user:User)->str:
 rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id).order_by(ChatMessage.created_at.desc()).limit(8)).all()
 notes=db.scalars(select(StudyNote).where(StudyNote.user_id==user.id).order_by(StudyNote.updated_at.desc()).limit(5)).all()
 parts=[]
 if rows:parts.append('RECENT CONVERSATION:\\n'+'\\n'.join(f'{r.role}: {r.content[:1200]}' for r in reversed(rows)))
 if notes:parts.append('SAVED NOTES:\\n'+'\\n'.join(f'- {n.title}: {n.content[:1200]}' for n in notes))
 return '\\n\\n'.join(parts)

async def gemini(prompt:str)->str:
 answer,_=await generate_text(prompt)
 return answer
def parse_flashcards(text:str)->list[Flashcard]:
 cards=[];q=None
 for raw in text.splitlines():
  line=raw.strip()
  if line.lower().startswith('q:'):q=line[2:].strip()
  elif line.lower().startswith('a:') and q:cards.append(Flashcard(question=q,answer=line[2:].strip()));q=None
 return cards
def owned_document(db:Session,user:User,document_id:str)->DocumentRecord:
 record=db.scalar(select(DocumentRecord).where(DocumentRecord.document_id==document_id,DocumentRecord.user_id==user.id))
 if not record:raise HTTPException(404,'Document not found')
 return record
@app.get('/api/tools')
def tools_catalog(user:User|None=Depends(optional_user)):
 return list_tools()
@app.post('/api/tools/execute')
def execute_tool(req:ToolRequest,user:User=Depends(current_user)):
 try:
  return {'tool':req.name,'result':run_tool(req.name,req.arguments)}
 except KeyError as exc:raise HTTPException(404,str(exc)) from exc
 except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@app.get('/api/health')
async def health():
 database=False
 try:
  with engine.connect() as c:c.exec_driver_sql('SELECT 1');database=True
 except Exception:pass
 return {'status':'ok','service':'JARVIS API','ai_configured':selected_engine()!='offline','vector_store':'chroma','database':database}
@app.post('/api/auth/register')
def register(data:AuthRequest,db:Session=Depends(db_session)):
 email=data.email.strip().lower()
 if '@' not in email or '.' not in email.split('@')[-1]:raise HTTPException(400,'Enter a valid email address')
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
async def run_tool_command(question:str,user:User|None=None,db:Session|None=None)->str|None:
 from .tools import tool_for_text
 parsed=tool_for_text(question)
 if not parsed:return None
 name,args=parsed
 try:
  if name=="study_summary" and user and db:
   args={"subjects":[s.name for s in db.scalars(select(Subject).where(Subject.user_id==user.id)).all()]}
  if name=="notes_summary" and user and db:
   args={"notes":[n.title for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id)).all()]}
  if name=="progress_summary" and user and db:
   args={"tasks":[{"completed":t.completed} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id)).all()]}
  if name=="planner_summary" and user and db:
   args={"tasks":[{"title":t.title,"completed":t.completed} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id).order_by(StudyTask.task_date.asc()).limit(20)).all()]}
  if name=="study_dashboard" and user and db:
   args={"subjects":[s.name for s in db.scalars(select(Subject).where(Subject.user_id==user.id)).all()],"notes":[n.title for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id)).all()],"tasks":[{"title":t.title,"completed":t.completed} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id).order_by(StudyTask.task_date.asc()).limit(20)).all()]}
  if name=="daily_briefing" and user and db:
   args={"subjects":[s.name for s in db.scalars(select(Subject).where(Subject.user_id==user.id)).all()],"notes":[n.title for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id).order_by(StudyNote.updated_at.desc()).limit(5)).all()],"tasks":[{"title":t.title,"completed":t.completed,"minutes":t.minutes} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id).order_by(StudyTask.task_date.asc()).limit(20)).all()]}
  if name=="focus_recommendation" and user and db:
   subjects=db.scalars(select(Subject).where(Subject.user_id==user.id)).all(); subject_by_id={s.id:s.name for s in subjects}; args={"subjects":[s.name for s in subjects],"tasks":[{"title":t.title,"subject":subject_by_id.get(t.subject_id,""),"completed":t.completed,"minutes":t.minutes,"task_date":str(t.task_date)} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id).order_by(StudyTask.task_date.asc()).limit(20)).all()]}
   pref=db.scalar(select(UserPreference).where(UserPreference.user_id==user.id))
   if pref and pref.focus_subject:
    args["focus_subject"]=pref.focus_subject

  if name=="weekly_review" and user and db:
   cutoff=datetime.now(timezone.utc)-timedelta(days=7)
   args={"tasks":[{"completed":t.completed} for t in db.scalars(select(StudyTask).where(StudyTask.user_id==user.id,StudyTask.created_at>=cutoff).all())],"events":[{"minutes":e.minutes} for e in db.scalars(select(StudyEvent).where(StudyEvent.user_id==user.id,StudyEvent.created_at>=cutoff)).all()]}
  result=run_tool(name,args)
  return f"Tool {name} result: {result}"
 except (KeyError,ValueError):
  return None

async def run_chat(req:ChatRequest,user:User|None=None,db:Session|None=None)->tuple[str,list[dict[str,Any]]]:
 sources=[];retrieved=req.context
 tool_result=await run_tool_command(req.question,user,db)
 if tool_result:return tool_result,sources
 if user and db:
  remembered=memory_context(db,user)
  if remembered:retrieved=(retrieved+'\n\n'+remembered).strip()
 if req.use_retrieval:
  hits=[]
  if req.document_id and req.semantic and GEMINI_API_KEY:
   try:hits=await semantic_search(req.question,req.document_id)
   except Exception:hits=[]
  if not hits and req.context:
   chunks=chunk_document(req.context)
   try:hits=await semantic_search(req.question,req.document_id) if req.semantic and GEMINI_API_KEY else lexical_retrieve(req.question,chunks)
   except Exception:hits=lexical_retrieve(req.question,chunks)
  if hits:
   sources=[{'page':h.page,'preview':h.text[:240]} for h in hits] if hasattr(hits[0],'text') else [{'page':h['page'],'preview':h['text'][:240],'distance':h.get('distance')} for h in hits]
   retrieved='\n\n'.join(f'[Page {h.page}]\n{h.text}' for h in hits) if hasattr(hits[0],'text') else '\n\n'.join(f"[Page {h['page']}]\n{h['text']}" for h in hits)
 a=await gemini(build_prompt(req,retrieved));return (a or offline_answer(req.question)),sources
@app.post('/api/chat',response_model=ChatResponse)
async def chat(req:ChatRequest,user:User|None=Depends(optional_user),db:Session=Depends(db_session)):
 if req.document_id:
  if not user:raise HTTPException(401,'Authentication required for document study')
  owned_document(db,user,req.document_id)
 a,sources=await run_chat(req,user,db)
 if user:db.add_all([ChatMessage(user_id=user.id,role='user',content=req.question),ChatMessage(user_id=user.id,role='assistant',content=a)]);db.commit();event(db,user.id,'question')
 return ChatResponse(answer=a,model=GEMINI_MODEL if selected_engine()=='gemini' else OLLAMA_MODEL if selected_engine()=='ollama' else 'offline',used_ai=selected_engine()!='offline',sources=sources)
@app.post('/api/flashcards/generate',response_model=FlashcardResponse)
async def generate_flashcards(req:FlashcardRequest,user:User|None=Depends(optional_user),db:Session=Depends(db_session)):
 if req.document_id:
  if not user:raise HTTPException(401,'Authentication required for document flashcards')
  owned_document(db,user,req.document_id)
 context=req.context
 if req.document_id and GEMINI_API_KEY:
  try:context='\n\n'.join(f'[Page {h["page"]}]\n{h["text"]}' for h in await semantic_search(req.topic,req.document_id,top_k=min(req.count,10)))
  except Exception:pass
 text=await gemini(f'Create exactly {req.count} study flashcards. Return ONLY Q:/A: lines. Topic: {req.topic}\nMaterial:\n{context[:30000]}') if GEMINI_API_KEY else ''
 cards=parse_flashcards(text)[:req.count] if text else []
 if not cards:cards=[Flashcard(question=f'What is the key idea of {req.topic}?',answer='Review the definition, core concepts, examples, and exam points.')]
 if user:
  for c in cards:db.add(FlashcardRecord(user_id=user.id,question=c.question,answer=c.answer,document_id=req.document_id))
  db.commit();event(db,user.id,'flashcard')
 return FlashcardResponse(cards=cards,model=GEMINI_MODEL if selected_engine()=='gemini' else OLLAMA_MODEL if selected_engine()=='ollama' else 'offline',used_ai=selected_engine()!='offline')
@app.get('/api/flashcards')
def list_flashcards(user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(FlashcardRecord).where(FlashcardRecord.user_id==user.id).order_by(FlashcardRecord.created_at.desc())).all()
 return [{'id':x.id,'question':x.question,'answer':x.answer,'document_id':x.document_id,'review_count':x.review_count,'last_reviewed_at':x.last_reviewed_at.isoformat() if x.last_reviewed_at else None} for x in rows]
@app.post('/api/flashcards/{card_id}/review')
def review_flashcard(card_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
 card=db.scalar(select(FlashcardRecord).where(FlashcardRecord.id==card_id,FlashcardRecord.user_id==user.id))
 if not card:raise HTTPException(404,'Flashcard not found')
 card.review_count+=1;card.last_reviewed_at=datetime.now(timezone.utc);db.commit();event(db,user.id,'flashcard_review');return {'id':card.id,'review_count':card.review_count,'last_reviewed_at':card.last_reviewed_at.isoformat()}
@app.delete('/api/flashcards/{card_id}')
def delete_flashcard(card_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
 card=db.scalar(select(FlashcardRecord).where(FlashcardRecord.id==card_id,FlashcardRecord.user_id==user.id))
 if not card:raise HTTPException(404,'Flashcard not found')
 db.delete(card);db.commit();return {'deleted':True}
@app.get('/api/analytics/daily')
def analytics_daily(days:int=7,user:User=Depends(current_user),db:Session=Depends(db_session)):return daily_summary(db,user.id,days)
@app.get('/api/preferences')
def get_preferences(user:User=Depends(current_user),db:Session=Depends(db_session)):
 pref=db.scalar(select(UserPreference).where(UserPreference.user_id==user.id))
 if not pref:
  pref=UserPreference(user_id=user.id)
  db.add(pref);db.commit();db.refresh(pref)
 return {'daily_minutes':pref.daily_minutes,'focus_subject':pref.focus_subject}

@app.put('/api/preferences')
def update_preferences(payload:dict[str,Any],user:User=Depends(current_user),db:Session=Depends(db_session)):
 pref=db.scalar(select(UserPreference).where(UserPreference.user_id==user.id))
 if not pref: pref=UserPreference(user_id=user.id);db.add(pref)
 if 'daily_minutes' in payload: pref.daily_minutes=max(15,min(int(payload['daily_minutes']),720))
 if 'focus_subject' in payload: pref.focus_subject=str(payload['focus_subject'])[:100]
 db.commit();db.refresh(pref)
 return {'daily_minutes':pref.daily_minutes,'focus_subject':pref.focus_subject}
@app.get('/api/subjects')
def list_subjects(user:User=Depends(current_user),db:Session=Depends(db_session)):
 return [{'id':s.id,'name':s.name,'code':s.code,'daily_minutes':s.daily_minutes,'exam_date':s.exam_date.isoformat() if s.exam_date else None} for s in db.scalars(select(Subject).where(Subject.user_id==user.id).order_by(Subject.name)).all()]
@app.post('/api/subjects')
def create_subject(data:SubjectRequest,user:User=Depends(current_user),db:Session=Depends(db_session)):
 exam=None
 if data.exam_date:
  try:exam=date.fromisoformat(data.exam_date)
  except ValueError:raise HTTPException(400,'exam_date must use YYYY-MM-DD')
 s=Subject(user_id=user.id,name=data.name.strip(),code=data.code.strip(),daily_minutes=data.daily_minutes,exam_date=exam);db.add(s);db.commit();db.refresh(s);return {'id':s.id,'name':s.name,'code':s.code,'daily_minutes':s.daily_minutes,'exam_date':data.exam_date}
@app.delete('/api/subjects/{subject_id}')
def delete_subject(subject_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
 s=db.scalar(select(Subject).where(Subject.id==subject_id,Subject.user_id==user.id))
 if not s:raise HTTPException(404,'Subject not found')
 db.delete(s);db.commit();return {'deleted':True}
@app.post('/api/study/plan')
def study_plan(data:PlanInput,user:User=Depends(current_user),db:Session=Depends(db_session)):
 plan=make_plan(data);planned_dates={date.fromisoformat(t.date) for t in plan.tasks}
 if planned_dates:db.execute(delete(StudyTask).where(StudyTask.user_id==user.id,StudyTask.completed==0,StudyTask.task_date.in_(planned_dates)))
 for t in plan.tasks:
  subject=db.scalar(select(Subject).where(Subject.user_id==user.id,Subject.name==t.subject))
  db.add(StudyTask(user_id=user.id,subject_id=subject.id if subject else None,title=f'{t.subject}: {t.topic}',task_date=date.fromisoformat(t.date),minutes=t.minutes))
 db.commit();event(db,user.id,'plan');return plan
@app.get('/api/study/tasks')
def study_tasks(user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(StudyTask).where(StudyTask.user_id==user.id).order_by(StudyTask.task_date,StudyTask.id)).all();return [{'id':t.id,'title':t.title,'date':t.task_date.isoformat(),'minutes':t.minutes,'completed':bool(t.completed)} for t in rows]
@app.patch('/api/study/tasks/{task_id}')
def complete_task(task_id:int,data:TaskComplete,user:User=Depends(current_user),db:Session=Depends(db_session)):
 t=db.scalar(select(StudyTask).where(StudyTask.id==task_id,StudyTask.user_id==user.id))
 if not t:raise HTTPException(404,'Task not found')
 t.completed=1 if data.completed else 0;db.commit();event(db,user.id,'task_complete' if data.completed else 'task_uncomplete',t.minutes if data.completed else 0);return {'id':t.id,'completed':bool(t.completed)}
@app.get('/api/analytics/summary')
def analytics(user:User=Depends(current_user),db:Session=Depends(db_session)):
 total_questions=db.scalar(select(func.count()).select_from(StudyEvent).where(StudyEvent.user_id==user.id,StudyEvent.event_type=='question')) or 0
 total_minutes=db.scalar(select(func.coalesce(func.sum(StudyEvent.minutes),0)).where(StudyEvent.user_id==user.id)) or 0
 completed=db.scalar(select(func.count()).select_from(StudyTask).where(StudyTask.user_id==user.id,StudyTask.completed==1)) or 0
 tasks=db.scalar(select(func.count()).select_from(StudyTask).where(StudyTask.user_id==user.id)) or 0
 return {'questions':total_questions,'study_minutes':int(total_minutes),'completed_tasks':completed,'total_tasks':tasks,'notes':db.scalar(select(func.count()).select_from(StudyNote).where(StudyNote.user_id==user.id)) or 0,'subjects':db.scalar(select(func.count()).select_from(Subject).where(Subject.user_id==user.id)) or 0}
@app.get('/api/chat/history')
def history(limit:int=50,user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id).order_by(ChatMessage.created_at.desc()).limit(max(1,min(limit,200)))).all();return [{'id':x.id,'role':x.role,'content':x.content,'created_at':x.created_at.isoformat()} for x in reversed(rows)]
@app.delete('/api/chat/history')
def clear_history(user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id)).all()
 for x in rows:db.delete(x)
 db.commit();return {'deleted':len(rows)}
@app.post('/api/notes')
def create_note(data:NoteRequest,user:User=Depends(current_user),db:Session=Depends(db_session)):
 n=StudyNote(user_id=user.id,title=data.title.strip(),content=data.content.strip());db.add(n);db.commit();db.refresh(n);event(db,user.id,'note');return {'id':n.id,'title':n.title,'content':n.content}
@app.get('/api/notes')
def list_notes(user:User=Depends(current_user),db:Session=Depends(db_session)):
 return [{'id':n.id,'title':n.title,'content':n.content,'created_at':n.created_at.isoformat()} for n in db.scalars(select(StudyNote).where(StudyNote.user_id==user.id).order_by(StudyNote.updated_at.desc())).all()]
@app.delete('/api/notes/{note_id}')
def delete_note(note_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
 n=db.scalar(select(StudyNote).where(StudyNote.id==note_id,StudyNote.user_id==user.id))
 if not n:raise HTTPException(404,'Note not found')
 db.delete(n);db.commit();return {'deleted':True}
@app.post('/api/pdf/extract')
async def extract_pdf(file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(db_session)):
 if file.content_type!='application/pdf' and not (file.filename or '').lower().endswith('.pdf'):raise HTTPException(400,'Please upload a PDF file')
 raw=await file.read()
 if len(raw)>20*1024*1024:raise HTTPException(413,'PDF must be smaller than 20 MB')
 try:
  doc=fitz.open(stream=BytesIO(raw),filetype='pdf')
  if doc.page_count>500:raise HTTPException(413,'PDF must contain 500 pages or fewer')
  pages=[p.get_text('text') for p in doc];text='\n\n'.join(f'PAGE {i+1}\n{v}' for i,v in enumerate(pages)).strip();did=str(uuid.uuid4());chunks=chunk_document(text);indexed=0
  if GEMINI_API_KEY:
   try:indexed=await index_chunks(did,[{'page':c.page,'text':c.text} for c in chunks])
   except Exception:pass
  db.add(DocumentRecord(user_id=user.id,document_id=did,filename=file.filename or 'document.pdf',pages=len(pages)));db.commit();event(db,user.id,'pdf_upload')
  return {'document_id':did,'filename':file.filename,'pages':len(pages),'characters':len(text),'chunks':len(chunks),'indexed_chunks':indexed,'text':text[:150000]}
 except HTTPException:raise
 except Exception as e:raise HTTPException(422,f'Could not read PDF: {e}') from e
@app.post('/api/pdf/study',response_model=ChatResponse)
async def study_pdf(req:ChatRequest,user:User|None=Depends(optional_user),db:Session=Depends(db_session)):
 if req.document_id:
  if not user:raise HTTPException(401,'Authentication required for document study')
  owned_document(db,user,req.document_id)
 a,s=await run_chat(req,user,db);return ChatResponse(answer=a,model=GEMINI_MODEL if selected_engine()=='gemini' else OLLAMA_MODEL if selected_engine()=='ollama' else 'offline',used_ai=selected_engine()!='offline',sources=s)
@app.get('/api/documents')
def list_documents(user:User=Depends(current_user),db:Session=Depends(db_session)):
 rows=db.scalars(select(DocumentRecord).where(DocumentRecord.user_id==user.id).order_by(DocumentRecord.created_at.desc())).all()
 return [{'document_id':x.document_id,'filename':x.filename,'pages':x.pages,'created_at':x.created_at.isoformat()} for x in rows]
@app.get('/api/documents/{document_id}/search')
async def search_document(document_id:str,q:str,top_k:int=5,user:User=Depends(current_user),db:Session=Depends(db_session)):
 owned_document(db,user,document_id)
 if not GEMINI_API_KEY:raise HTTPException(503,'Semantic search requires GEMINI_API_KEY')
 try:return await semantic_search(q,document_id,max(1,min(top_k,20)))
 except Exception as e:raise HTTPException(502,f'Search failed: {e}') from e
