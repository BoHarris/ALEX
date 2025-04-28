from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from database.database import get_db
from database.models.device_token import DeviceToken
from utils.auth_utils import decode_token
import logging


router = APIRouter(prefix="/auth", tags=["Logout"])

@router.post("/logout")
def logout(response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)):
    if refresh_token:
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        token = payload.get("device_token")
        
        device = db.query(DeviceToken).filter(DeviceToken.user_id == user_id, DeviceToken.token == token).first()
        if device:
            db.delete(device)
            db.commit()
            
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="strict",
        secure=True
        )
    return{"message": "Logged out successfully"}

