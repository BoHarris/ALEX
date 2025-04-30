import os
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session 
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

from database.database import get_db
from database.models.user import User
from database.models.device_token import DeviceToken
from utils.email import send_verification_email




#Toggle this in the backend .env:
# CREATE_DEVICE_ON_REGISTER=true  (or "false" to delay until after email verification)

CREATE_DEVICE_ON_REGISTER = os.getenv("CREATE_DEVICE_ON_REGISTER", "true").lower() =="true"

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto" )

TIER_LIMITS ={
        "free": 10,
        "pro": 50,
        "business": None
    }

# User Registration
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters long")
    tier: str = Field(default="free", description="User tier, default is 'free'")
    device_fingerprint: str = Field(..., description="Unique device fingerprint")
    


# ──────────────────────────────────────────────────────────────────────
# User Registration Endpoint
# This endpoint allows a new user to register by providing their email, password, and device information.
# The password is hashed before storing it in the database.

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    data: RegisterRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    ):
    
    email = data.email.strip().lower()
    logging.info(f"Registering user: {email}")
    
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = secrets.token_urlsafe(32)
    device_token = secrets.token_urlsafe(32)
    
    hashed_password = pwd_context.hash(data.password + device_token)
    
    new_user = User(
        first_name = data.first_name,
        last_name = data.last_name,
        email = email,
        hashed_password = hashed_password,
        tier = data.tier.lower(),
        is_verified = False,
        email_verification_token = verification_token,
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    max_devices = TIER_LIMITS.get(new_user.tier, 10)
    device_count = db.query(DeviceToken).filter(DeviceToken.user_id == new_user.id).count()
    if max_devices is not None and device_count >= max_devices:
        raise HTTPException(
            status_code=400,
            detail=f"{new_user.tier.capitalize()} tier allows {max_devices} device(s)"
        )
        
    send_verification_email(
        background_tasks,
        to_email=new_user.email,
        token=verification_token
    )
    
    device_row = DeviceToken(
        user_id = new_user.id,
        token = device_token,
        device_fingerprint = data.device_fingerprint,
        created_at = datetime.now(timezone.utc),
        last_used_at = datetime.now(timezone.utc),
    )
    db.add(device_row)
    db.commit()
    
    return{
        "message": "Registration successful! Please check your email to verify your account"
    }
    
    
    
    
    
  