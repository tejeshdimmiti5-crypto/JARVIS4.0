from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base

class FlashcardRecord(Base):
    __tablename__='flashcards'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    question: Mapped[str]=mapped_column(Text)
    answer: Mapped[str]=mapped_column(Text)
    document_id: Mapped[str|None]=mapped_column(String(100),nullable=True)
    review_count: Mapped[int]=mapped_column(Integer,default=0)
    last_reviewed_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
