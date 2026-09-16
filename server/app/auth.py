from __future__ import annotations
import os
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer,HTTPBearer,HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .db import SessionLocal,User
SECRET_KEY=os.getenv("JWT_SECRET","change-this-secret-in-production");ALGORITHM="HS256";TOKEN_MINUTES=int(os.getenv("JWT_EXPIRE_MINUTES","1440"));password_hash=PasswordHash.recommended();oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/auth/login");optional_bearer=HTTPBearer(auto_error=False)
def db_session():
 db=SessionLocal()
 try:yield db
 finally:db.close()
def create_token(user_id:int)->str:return jwt.encode({"sub":str(user_id),"exp":datetime.now(timezone.utc)+timedelta(minutes=TOKEN_MINUTES)},SECRET_KEY,algorithm=ALGORITHM)
def user_from_token(token:str,db:Session)->User:
 try:payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM]);user=db.get(User,int(payload["sub"]))
 except (jwt.PyJWTError,KeyError,ValueError):user=None
 if not user:raise HTTPException(401,"Invalid or expired token",headers={"WWW-Authenticate":"Bearer"})
 return user
def current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(db_session))->User:return user_from_token(token,db)
def optional_user(credentials:HTTPAuthorizationCredentials|None=Depends(optional_bearer),db:Session=Depends(db_session))->User|None:
 if not credentials:return None
 try:return user_from_token(credentials.credentials,db)
 except HTTPException:return None
