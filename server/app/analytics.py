from __future__ import annotations
from datetime import date,timedelta
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from .models import StudyEvent

def daily_summary(db:Session,user_id:int,days:int=7):
    days=max(1,min(days,30));today=date.today();start=today-timedelta(days=days-1)
    rows=db.execute(select(func.date(StudyEvent.created_at).label('day'),func.coalesce(func.sum(StudyEvent.minutes),0).label('minutes'),func.count(StudyEvent.id).label('events')).where(StudyEvent.user_id==user_id,StudyEvent.created_at>=start).group_by(func.date(StudyEvent.created_at))).all()
    by_day={str(r.day):{'minutes':int(r.minutes or 0),'events':int(r.events or 0)} for r in rows}
    result=[{'date':str(start+timedelta(days=i)),'minutes':by_day.get(str(start+timedelta(days=i)),{}).get('minutes',0),'events':by_day.get(str(start+timedelta(days=i)),{}).get('events',0)} for i in range(days)]
    active={x['date'] for x in result if x['minutes']>0}
    streak=0
    cursor=today
    while str(cursor) in active:
        streak+=1;cursor-=timedelta(days=1)
    return {'days':result,'current_streak':streak,'active_days':len(active),'total_minutes':sum(x['minutes'] for x in result)}
