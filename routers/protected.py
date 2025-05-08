from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from utils.auth_utils import create_access_token, decode_token
from sqlalchemy.orm import Session
from database.database import get_db
from database.models.user import User

router = APIRouter(prefix="/protected", tags=["Secure"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

@router.get("/me")
def secure_area(
    token: str = Depends(oauth2_scheme),
     db: Session = Depends(get_db)           
     ):
    try: 
        payload = decode_token(token)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    device_token = payload.get("device_token")
    tier = payload.get("tier", "free")
    if not device_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    
    refreshed_token = create_access_token(
        data={"sub": user_id, "device_token": device_token, "tier": tier},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Secure area", 
        "user_id": user_id, 
        "name": user_obj.name,
        "device_token": device_token, 
        "tier": tier,
        "refreshed_access_token": refreshed_token}

