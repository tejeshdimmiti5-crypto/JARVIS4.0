from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .db import SessionLocal, User

SECRET_KEY=os.getenv("JWT_SECRET","change-this-secret-in-production")
ALGORITHM="HS256"
TOKEN_MINUTES=int(os.getenv("JWT_EXPIRE_MINUTES","1440"))
password_hash=PasswordHash.recommended()
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def db_session():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def create_token(user_id:int)->str:
    exp=datetime.now(timezone.utc)+timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub":str(user_id),"exp":exp},SECRET_KEY,algorithm=ALGORITHM)

def current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(db_session))->User:
    credentials=HTTPException(status_code=401,detail="Invalid or expired token",headers={"WWW-Authenticate":"Bearer"})
    try: payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM]); user_id=int(payload["sub"])
    except (jwt.PyJWTError,KeyError,ValueError): raise credentials
    user=db.get(User,user_id)
    if not user: raise credentials
    return user
