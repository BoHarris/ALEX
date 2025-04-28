from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.database import get_db
from database.models.user import User
from database.models.device_token import DeviceToken
from utils.auth_utils import create_access_token
from datetime import timedelta
from passlib.context import CryptContext
import logging

router = APIRouter(prefix="/auth", tags=["Login"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token
@router.post("/token", response_model=dict)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print("Incoming login request:")
    print("Username:", form_data.username)
    print("Password:", form_data.password)

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        print("User not found")
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # if not user.is_verified:
    #     print("User not verified")
    #     raise HTTPException(status_code=400, detail="User not verified")

    device_token = db.query(DeviceToken).filter(DeviceToken.user_id == user.id).order_by(DeviceToken.created_at.desc()).first()

    if not device_token:
        print("Device token not found")
        raise HTTPException(status_code=400, detail="Device token not found")

    # Now that everything is safe to use, print debug info
    print("Device token:", device_token.token)
    print("Combined password+token:", form_data.password + device_token.token)
    print("Expected hash:", user.hashed_password)
    match = pwd_context.verify(form_data.password + device_token.token, user.hashed_password)
    print("Password match:", match)

    if not match:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id), "device_token": device_token.token},
        expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id), "device_token": device_token.token},
        expires_delta=timedelta(days=7)
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