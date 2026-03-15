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

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))


def _secret_key() -> str:
    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is not configured. Run startup validation and set SECRET_KEY before issuing or decoding tokens."
        )
    return secret_key


def _jwt_issuer() -> str:
    return (os.getenv("JWT_ISSUER") or "").strip()


def _jwt_audience() -> str:
    return (os.getenv("JWT_AUDIENCE") or "").strip()

def _utc_expiry(expires_delta: Optional[timedelta]) -> datetime:
    return datetime.now(timezone.utc) + expires_delta if expires_delta else datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """ 
    Creates an access token for short lived api access
    """
    to_encode = data.copy()
    jwt_issuer = _jwt_issuer()
    jwt_audience = _jwt_audience()
    if "typ" not in to_encode:
        to_encode["typ"] = "access"
    if jwt_issuer and "iss" not in to_encode:
        to_encode["iss"] = jwt_issuer
    if jwt_audience and "aud" not in to_encode:
        to_encode["aud"] = jwt_audience
    expire = _utc_expiry(expires_delta)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, refresh_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    jwt_issuer = _jwt_issuer()
    jwt_audience = _jwt_audience()
    to_encode = {
        "sub": str(user_id),
        "ver": str(refresh_version),
        "typ": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    if jwt_issuer:
        to_encode["iss"] = jwt_issuer
    if jwt_audience:
        to_encode["aud"] = jwt_audience
    return jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM)


def issue_refresh_token(user_id: int, refresh_version: int) -> tuple[str, str]:
    refresh_jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    jwt_issuer = _jwt_issuer()
    jwt_audience = _jwt_audience()
    to_encode = {
        "sub": str(user_id),
        "ver": str(refresh_version),
        "typ": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": refresh_jti,
    }
    if jwt_issuer:
        to_encode["iss"] = jwt_issuer
    if jwt_audience:
        to_encode["aud"] = jwt_audience
    return jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM), refresh_jti


def _decode_token(
    token: str,
    *,
    expected_type: str | None,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    jwt_issuer = _jwt_issuer()
    jwt_audience = _jwt_audience()
    decode_kwargs: dict[str, Any] = {"algorithms": [ALGORITHM]}
    if jwt_issuer:
        decode_kwargs["issuer"] = jwt_issuer
    if jwt_audience:
        decode_kwargs["audience"] = jwt_audience

    try:
        payload = jwt.decode(token, _secret_key(), **decode_kwargs)
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
