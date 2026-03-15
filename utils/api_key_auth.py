from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from database.database import SessionLocal
from database.models.api_key import ApiKey
from database.models.user import User
from utils.api_errors import error_payload
from utils.rbac import normalize_role


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key_secret() -> str:
    return f"alex_{secrets.token_urlsafe(32)}"


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        authorization = request.headers.get("Authorization") or ""
        if not authorization.startswith("ApiKey "):
            return await call_next(request)

        raw_key = authorization.split(" ", 1)[1].strip()
        if not raw_key:
            return JSONResponse(
                status_code=401,
                content=error_payload(detail="Missing API key", error_code="invalid_token"),
            )

        session_factory = getattr(request.app.state, "session_factory", SessionLocal)
        db = session_factory()
        try:
            api_key = db.query(ApiKey).filter(ApiKey.hashed_key == hash_api_key(raw_key)).first()
            if not api_key:
                return JSONResponse(
                    status_code=401,
                    content=error_payload(detail="Invalid API key", error_code="invalid_token"),
                )

            user = db.query(User).filter(User.id == api_key.created_by_user_id).first()
            if not user or not user.is_active:
                return JSONResponse(
                    status_code=401,
                    content=error_payload(detail="API key owner is inactive", error_code="forbidden"),
                )

            api_key.last_used = datetime.now(timezone.utc)
            api_key.usage_count = int(api_key.usage_count or 0) + 1
            db.add(api_key)
            db.commit()

            request.state.api_key_context = {
                "api_key_id": api_key.id,
                "company_id": api_key.company_id,
                "user_id": user.id,
                "role": normalize_role(user.role),
                "auth_type": "api_key",
            }
            request.state.user_id = user.id
            return await call_next(request)
        finally:
            db.close()
