from __future__ import annotations
from datetime import date,datetime
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
 tasks=[]
 for d in range(days):
  s=subs[d%len(subs)];mins=max(15,min(s.daily_minutes,480));tasks.append(Task(day=d+1,date=str(date.today()),subject=s.name,minutes=mins,topic=f'{s.code + " — " if s.code else ""}Revision and practice'))
 return PlanResponse(tasks=tasks,created_at=datetime.utcnow().isoformat())
