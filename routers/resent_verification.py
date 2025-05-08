from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import secrets

from database.database import get_db
from database.models.user import User
from utils.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

class ResendRequest(BaseModel):
    email: EmailStr
    
@router.post("/resend-verification", status_code=200)
def resent_verification(
        request: ResendRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
    ):
    email =  request.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "No Account with that email")
    if user.is_verified:
        raise HTTPException(400, "Account already verified")
    
    user.email_verification_token = secrets.token_urlsafe(32)
    db.commit()
    
    send_verification_email(
        background_tasks,
        to_email=user.email,
        token=user.email_verification_token,
    )
    return {"message": "Verification email resent"}