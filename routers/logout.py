from fastapi import APIRouter, Depends, Response, Cookie, Request
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from services.audit_service import record_audit_event
from services.security_service import extract_request_security_context
from utils.auth_utils import decode_refresh_token_with_error
import os

router = APIRouter(prefix="/auth", tags=["Logout"])
IS_PROD = os.getenv("ENV", "development").lower() == "production"


def _parse_subject_as_int(subject: str | None) -> int | None:
    try:
        return int(subject) if subject is not None else None
    except (TypeError, ValueError):
        return None

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    # Best effort revoke
    if refresh_token:
        payload, _ = decode_refresh_token_with_error(refresh_token)
        if payload:
            user_id = _parse_subject_as_int(payload.get("sub"))
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    current_ver = int(getattr(user, "refresh_version", 0))
                    setattr(user, "refresh_version", current_ver + 1)
                    db.add(user)
                    record_audit_event(
                        db,
                        company_id=user.company_id,
                        user_id=user.id,
                        event_type="logout",
                        event_category="authentication",
                        description="User logged out.",
                        target_type="user",
                        target_id=str(user.id),
                        request_context=extract_request_security_context(request),
                    )
                    db.commit()
        
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="strict",
        secure=IS_PROD,
    )
    return {"message": "Logged out successfully"}

