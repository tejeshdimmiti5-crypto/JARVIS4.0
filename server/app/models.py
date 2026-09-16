from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Subject(Base):
    __tablename__='subjects'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    name: Mapped[str]=mapped_column(String(100))
    code: Mapped[str]=mapped_column(String(30),default='')
    daily_minutes: Mapped[int]=mapped_column(Integer,default=60)
    exam_date: Mapped[date|None]=mapped_column(Date,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class StudyTask(Base):
    __tablename__='study_tasks'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    subject_id: Mapped[int|None]=mapped_column(ForeignKey('subjects.id'),nullable=True)
    title: Mapped[str]=mapped_column(String(200))
    task_date: Mapped[date]=mapped_column(Date)
    minutes: Mapped[int]=mapped_column(Integer,default=30)
    completed: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class StudyEvent(Base):
    __tablename__='study_events'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    event_type: Mapped[str]=mapped_column(String(40),index=True)
    minutes: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
