# ──────────────────────────────────────────────────────────────────────
# Importing necessary modules and classes
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database.database import get_db
from database.models.user import User
from database.models.device_token import DeviceToken
from utils.auth_utils import create_access_token, decode_token
from datetime import datetime, timedelta, timezone
import secrets



router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto" )
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# ──────────────────────────────────────────────────────────────────────

    
# ──────────────────────────────────────────────────────────────────────


@router.get("/secure-stuff")
def secure_area(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    device_token = payload.get("device_token")
    
    access_token=create_access_token(data={
        "sub": user_id,
        "device_token": device_token.token},
        expires_delta=timedelta(minutes=30)
    )
    return {"message": "Secure area", "user_id": user_id, "device_token": device_token}


    