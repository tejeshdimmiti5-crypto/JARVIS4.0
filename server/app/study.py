from __future__ import annotations
from datetime import date,datetime,timedelta
from pydantic import BaseModel,Field

class SubjectInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    code:str=''
    exam_date:date|None=None
    daily_minutes:int=Field(default=60,ge=15,le=480)

class PlanInput(BaseModel):
    subjects:list[SubjectInput]
    days:int=Field(default=7,ge=1,le=30)

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
    days=max(1,min(data.days,30))
    if not data.subjects:
        return PlanResponse(tasks=[],created_at=datetime.utcnow().isoformat())

    today=date.today()
    # Give nearer exams more weight, while still rotating subjects so every
    # subject gets study time. A subject can appear more often when its exam
    # is closer or its requested daily workload is higher.
    ranked=[]
    for subject in data.subjects:
        if subject.exam_date:
            days_left=(subject.exam_date-today).days
            urgency=1 if days_left<=0 else max(1,30-min(days_left,29))
        else:
            urgency=1
        workload=max(1,subject.daily_minutes//30)
        ranked.append((urgency*workload,subject))
    ranked.sort(key=lambda x:(-x[0],x[1].name.lower()))

    weighted=[]
    for weight,subject in ranked:
        weighted.extend([subject]*min(weight,10))
    tasks=[]
    for d in range(days):
        subject=weighted[d%len(weighted)]
        mins=max(15,min(subject.daily_minutes,480))
        days_left=(subject.exam_date-today).days if subject.exam_date else None
        focus='Priority revision' if days_left is not None and days_left<=7 else 'Revision and practice'
        if days_left is not None and days_left<0:
            focus='Backlog recovery and practice'
        if subject.code:
            focus=f'{subject.code} — {focus}'
        if days_left is not None and days_left>=0:
            focus+=f' · {days_left} days to exam'
        tasks.append(Task(day=d+1,date=str(today+timedelta(days=d)),subject=subject.name,minutes=mins,topic=focus))
    return PlanResponse(tasks=tasks,created_at=datetime.utcnow().isoformat())
