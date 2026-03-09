from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from utils.auth_utils import decode_token

router = APIRouter(prefix="/protected", tags=["Secure"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/tokenUrl")

@router.get("/me")
def secure_area(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail= "Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": "Secure area",
        "user_id": user.id,
        "email": user.email,
        "tier": getattr(user, "tier", "free")
    }
