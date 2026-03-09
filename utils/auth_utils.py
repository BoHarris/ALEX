from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv
import os
from typing import Optional, Tuple, Any, Dict
import logging as logger
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in environment variables.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

def _utc_expiry(expires_delta: Optional[timedelta]) -> datetime:
    return datetime.now(timezone.utc) + expires_delta if expires_delta else datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """ 
    Creates an access token for short lived api access
    """
    to_encode = data.copy()
    expire = _utc_expiry(expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, refresh_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "ver": str(refresh_version),
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.info(f"[decode_token] JWT error: {e}")
        return None
    
def get_user_info_from_token(token: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Reads common identity info from access token, returns (sub. email)
    """
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("sub"), payload.get("device_token")
