from fastapi import APIRouter, Depends, HTTPException, Response,Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from database.database import get_db
from database.models.user import User
from database.models.device_token import DeviceToken
from passlib.context import CryptContext
from utils.auth_utils import create_access_token

import os

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#Token TTL
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_TTL = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "1440"))

@router.post("/token", response_model=dict)
def login(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    device_fingerprint: str = Form(...),
    db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        print("User not found")
        raise HTTPException(
            status_code=400, 
            detail="Invalid credentials")

    device_row = (
            db.query(DeviceToken)
            .filter(
                DeviceToken.user_id == user.id,
                DeviceToken.device_fingerprint == device_fingerprint
                )
                .first()
    )    

    if not device_row:
        raise HTTPException(status_code=400, detail="Unknown device")

    # Now that everything is safe to use, print debug info
    combined = form_data.password + device_row.token
    if not pwd_context.verify(combined,user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL)
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(REFRESH_TOKEN_TTL)
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=7*24*60*60,
        secure=True
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }