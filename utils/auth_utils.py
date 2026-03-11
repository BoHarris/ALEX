from datetime import datetime, timezone, timedelta
import uuid
from jose import JWTError, ExpiredSignatureError, jwt
from dotenv import load_dotenv
import os
from typing import Optional, Tuple, Any, Dict
import logging as logger
from fastapi import HTTPException

from utils.api_errors import error_payload
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in environment variables.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = (os.getenv("JWT_ISSUER") or "").strip()
JWT_AUDIENCE = (os.getenv("JWT_AUDIENCE") or "").strip()
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
    if "typ" not in to_encode:
        to_encode["typ"] = "access"
    if JWT_ISSUER and "iss" not in to_encode:
        to_encode["iss"] = JWT_ISSUER
    if JWT_AUDIENCE and "aud" not in to_encode:
        to_encode["aud"] = JWT_AUDIENCE
    expire = _utc_expiry(expires_delta)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, refresh_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "ver": str(refresh_version),
        "typ": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    if JWT_ISSUER:
        to_encode["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        to_encode["aud"] = JWT_AUDIENCE
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def issue_refresh_token(user_id: int, refresh_version: int) -> tuple[str, str]:
    refresh_jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "ver": str(refresh_version),
        "typ": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": refresh_jti,
    }
    if JWT_ISSUER:
        to_encode["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        to_encode["aud"] = JWT_AUDIENCE
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM), refresh_jti


def _decode_token(
    token: str,
    *,
    expected_type: str | None,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    decode_kwargs: dict[str, Any] = {"algorithms": [ALGORITHM]}
    if JWT_ISSUER:
        decode_kwargs["issuer"] = JWT_ISSUER
    if JWT_AUDIENCE:
        decode_kwargs["audience"] = JWT_AUDIENCE

    try:
        payload = jwt.decode(token, SECRET_KEY, **decode_kwargs)
    except ExpiredSignatureError:
        logger.info("[decode_token] token expired")
        return None, "expired_token"
    except JWTError as e:
        logger.info(f"[decode_token] JWT error: {e}")
        return None, "invalid_token"

    if expected_type and payload.get("typ") != expected_type:
        logger.info("[decode_token] unexpected token type")
        return None, "invalid_token"

    if not payload.get("sub"):
        logger.info("[decode_token] missing subject claim")
        return None, "invalid_token"

    return payload, None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    payload, _ = _decode_token(token, expected_type="access")
    return payload


def decode_token_with_error(token: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    return _decode_token(token, expected_type="access")


def decode_refresh_token_with_error(token: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    return _decode_token(token, expected_type="refresh")


def ensure_user_is_active(user: Any) -> None:
    if getattr(user, "is_active", True):
        return
    raise HTTPException(
        status_code=401,
        detail=error_payload(
            detail="User account is inactive",
            error_code="ACCOUNT_DISABLED",
        ),
    )
    
def get_user_info_from_token(token: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Reads common identity info from access token, returns (sub, email).
    """
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("sub"), payload.get("email")
