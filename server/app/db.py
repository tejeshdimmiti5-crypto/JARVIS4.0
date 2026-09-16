from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,String,Text,create_engine
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./data/studentai.db')
if DATABASE_URL.startswith('sqlite:///'):
 os.makedirs('./data',exist_ok=True)
connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {}
engine=create_engine(DATABASE_URL,connect_args=connect_args)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase):pass
class User(Base):
 __tablename__='users';id:Mapped[int]=mapped_column(primary_key=True);email:Mapped[str]=mapped_column(String(255),unique=True,index=True);password_hash:Mapped[str]=mapped_column(String(255));created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class StudyNote(Base):
 __tablename__='notes';id:Mapped[int]=mapped_column(primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True);title:Mapped[str]=mapped_column(String(200));content:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow);updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class ChatMessage(Base):
 __tablename__='chat_messages';id:Mapped[int]=mapped_column(primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True);role:Mapped[str]=mapped_column(String(20));content:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)
