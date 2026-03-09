from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from jose import JWTError
from datetime import timedelta
import os

from database.database import get_db
from database.models.user import User
from utils.auth_utils import create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["Token"])

ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_TTL_MIN = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

@router.post("/refresh")
def refresh_access_token(
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    try:
        payload = decode_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        token_typ = payload.get("typ")
        if token_typ != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user_id = payload.get("sub")
        token_ver = payload.get("ver")
        if user_id is None or token_ver is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    #refresh token revocation check
    current_ver = int(getattr(user, "refresh_version", 0))
    if int(token_ver) != current_ver:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    
    #Issue new access token
    new_access = create_access_token(
        data={"sub": str(user.id), "email": user.email, "tier": getattr(user, "tier", "free")},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL),
    )
    
    #Keep refresh token same version 
    new_refresh = create_access_token(
            data={"sub": str(user.id), "ver": current_ver, "typ": "refresh"},
            expires_delta=timedelta(minutes=REFRESH_TOKEN_TTL_MIN)
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL_MIN * 60,
        secure=True,
    )
    
    return {"access_token": new_access, "token_type": "bearer"}
