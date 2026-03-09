from fastapi import APIRouter, Depends, Response, Cookie
from sqlalchemy.orm import Session
from jose import JWTError

from database.database import get_db
from database.models.user import User
from utils.auth_utils import decode_token

router = APIRouter(prefix="/auth", tags=["Logout"])

@router.post("/logout")
def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    # Best effort revoke
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user:
                    current_ver = int(getattr(user, "refresh_version", 0))
                    setattr(user, "refresh_version", current_ver + 1)
                    db.add(user)
                    db.commit()
        
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="strict",
        secure=True,
    )
    return {"message": "Logged out successfully"}

