from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    #Find user based on token
    user = db.query(User).filter(User.email_verification_token == token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    
    if user.is_verified:
        return{"message": "Account already verified."}
    
    #Mark user as verified
    user.is_verified = True
    user.email_verification_token = None #clear token after use
    db.commit()
    
    return {"message": "Email successfully verified! Welcome to ALEX.ai"}
