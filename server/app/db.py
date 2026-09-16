from __future__ import annotations
import os
from datetime import datetime,timezone
from sqlalchemy import DateTime,ForeignKey,String,Text,create_engine
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker

DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./data/studentai.db')
if DATABASE_URL.startswith('sqlite:///'):
    os.makedirs('./data',exist_ok=True)
connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {}
engine=create_engine(DATABASE_URL,connect_args=connect_args,pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(255))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class StudyNote(Base):
    __tablename__='notes'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    title:Mapped[str]=mapped_column(String(200))
    content:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))

class ChatMessage(Base):
    __tablename__='chat_messages'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    role:Mapped[str]=mapped_column(String(20))
    content:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

# Import feature models so metadata is complete for fresh SQLite/dev databases.
try:
    from . import models as _models
    from . import flashcards as _flashcards
except ImportError:
    _models=None
    _flashcards=None

Base.metadata.create_all(engine)
