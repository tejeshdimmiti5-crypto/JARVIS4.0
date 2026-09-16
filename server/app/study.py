from __future__ import annotations
from datetime import date,datetime,timedelta
from pydantic import BaseModel,Field
class SubjectInput(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 code:str=''
 exam_date:date|None=None
 daily_minutes:int=60
class PlanInput(BaseModel):
 subjects:list[SubjectInput]
 days:int=7
class Task(BaseModel):
 day:int
 date:str
 subject:str
 minutes:int
 topic:str
class PlanResponse(BaseModel):
 tasks:list[Task]
 created_at:str

def make_plan(data:PlanInput)->PlanResponse:
 days=max(1,min(data.days,30));subs=data.subjects
 if not subs:return PlanResponse(tasks=[],created_at=datetime.utcnow().isoformat())
 today=date.today();tasks=[]
 ranked=sorted(subs,key=lambda s:(s.exam_date or today+timedelta(days=3650),s.name.lower()))
 for d in range(days):
  s=ranked[d%len(ranked)];mins=max(15,min(s.daily_minutes,480))
  days_left=(s.exam_date-today).days if s.exam_date else None
  focus='Priority revision' if days_left is not None and days_left<=7 else 'Revision and practice'
  if s.code:focus=f'{s.code} — {focus}'
  if days_left is not None and days_left>=0:focus+=f' · {days_left} days to exam'
  tasks.append(Task(day=d+1,date=str(today+timedelta(days=d)),subject=s.name,minutes=mins,topic=focus))
 return PlanResponse(tasks=tasks,created_at=datetime.utcnow().isoformat())
