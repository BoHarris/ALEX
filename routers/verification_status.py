from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models.user import User

router = APIRouter(prefix="/verification", tags=["Authentication"])

@router.get("/check_verification_status")
def check_verification_status(email: str, db:Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return{"is_verified": user.is_verified}