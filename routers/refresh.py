from fastapi import APIRouter, Depends, HTTPException,Request, Response, status, Cookie
from sqlalchemy.orm import Session
from database.database import get_db
from utils.auth_utils import create_access_token, decode_token
from database.models.device_token import DeviceToken
from jose import JWTError
from datetime import timedelta
import logging
import secrets
router = APIRouter(prefix="/auth", tags=["Token"])

@router.post("/refresh")
def refresh_access_token(response: Response, refresh_token: str=Cookie(None), db: Session = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail = "Missing refresh token")
    
    try:
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        old_token = payload.get("device_token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    device_record = db.query(DeviceToken).filter(
        DeviceToken.user_id == user_id,
        DeviceToken.token == old_token
    ).first()
    
    if not device_record:
        raise HTTPException(status_code=403, detail="Token not recognized")
    
    #Rotate token
    new_token = secrets.token_hex(32)
    device_record.token = new_token
    db.commit()
    
    new_access = create_access_token({"sub": user_id, "device_token": new_token}, expires_delta=timedelta(minutes=30))
    new_refresh = create_access_token ({"sub":user_id, "device_token": new_token}, expires_delta=timedelta(days=7))
    
    #set secure cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="strict",
        max_age=7*24*60*60
    )   

    return {"access_token": new_access, "token_type": "bearer"}