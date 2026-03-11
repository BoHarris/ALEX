from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import os

from database.database import get_db
from database.models.user import User
from services.audit_service import record_audit_event
from services.refresh_session_service import (
    revoke_refresh_session,
    revoke_refresh_session_record,
    rotate_refresh_session,
    validate_refresh_session,
)
from services.security_service import extract_request_security_context, register_token_issue
from utils.auth_utils import create_access_token, decode_refresh_token_with_error, ensure_user_is_active, issue_refresh_token
from utils.api_errors import error_payload
from utils.rbac import normalize_role

router = APIRouter(prefix="/auth", tags=["Token"])

ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_TTL_MIN = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
IS_PROD = os.getenv("ENV", "development").lower() == "production"


def _parse_subject_as_int(subject: str | None) -> int:
    try:
        return int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid refresh token",
                error_code="invalid_token",
            ),
        )

@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        register_token_issue(
            db,
            organization_id=None,
            user_id=None,
            token_issue="missing_refresh_token",
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Missing refresh token",
                error_code="session_expired",
            ),
        )
    
    payload, decode_error = decode_refresh_token_with_error(refresh_token)
    if not payload:
        register_token_issue(
            db,
            organization_id=None,
            user_id=None,
            token_issue=decode_error or "invalid_refresh_token",
            context=extract_request_security_context(request),
        )
        db.commit()
        error_code = "expired_token" if decode_error == "expired_token" else "invalid_token"
        detail = "Refresh token expired" if decode_error == "expired_token" else "Invalid refresh token"
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail=detail, error_code=error_code),
        )
    user_id = _parse_subject_as_int(payload.get("sub"))
    token_ver = payload.get("ver")
    refresh_jti = payload.get("jti")
    if token_ver is None:
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid refresh token",
                error_code="invalid_token",
            ),
        )
    if not refresh_jti:
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid refresh token",
                error_code="invalid_token",
            ),
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        register_token_issue(
            db,
            organization_id=None,
            user_id=user_id,
            token_issue="refresh_subject_missing",
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid refresh token",
                error_code="invalid_token",
            ),
        )
    request_context = extract_request_security_context(request)
    if not user.is_active:
        register_token_issue(
            db,
            organization_id=user.company_id,
            user_id=user.id,
            token_issue="inactive_user",
            context=request_context,
        )
        revoke_refresh_session(db, refresh_jti=refresh_jti)
        user.refresh_version = int(getattr(user, "refresh_version", 0)) + 1
        db.add(user)
        db.commit()
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            samesite="strict",
            secure=IS_PROD,
        )
        ensure_user_is_active(user)
    
    #refresh token revocation check
    current_ver = int(getattr(user, "refresh_version", 0))
    if int(token_ver) != current_ver:
        register_token_issue(
            db,
            organization_id=user.company_id,
            user_id=user.id,
            token_issue="refresh_version_mismatch",
            context=request_context,
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Refresh token revoked",
                error_code="session_expired",
            ),
        )
    session_validation = validate_refresh_session(
        db,
        user_id=user.id,
        refresh_jti=refresh_jti,
        context=request_context,
    )
    if not session_validation.ok:
        register_token_issue(
            db,
            organization_id=user.company_id,
            user_id=user.id,
            token_issue=f"refresh_session_{session_validation.reason}",
            context=request_context,
        )
        if session_validation.reason == "binding_mismatch":
            revoke_refresh_session_record(db, session=session_validation.session)
            db.commit()
            response.delete_cookie(
                key="refresh_token",
                httponly=True,
                samesite="strict",
                secure=IS_PROD,
            )
            raise HTTPException(
                status_code=401,
                detail=error_payload(
                    detail="Reauthentication required",
                    error_code="reauthentication_required",
                ),
            )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid session",
                error_code="session_expired",
            ),
        )
    
    #Issue new access token
    new_access = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tier": getattr(user, "tier", "free"),
            "role": normalize_role(user.role),
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL),
    )
    
    user.refresh_version = current_ver + 1
    db.add(user)
    db.commit()
    db.refresh(user)

    new_refresh, new_refresh_jti = issue_refresh_token(user.id, int(user.refresh_version))
    rotate_refresh_session(
        db,
        session=session_validation.session,
        new_refresh_jti=new_refresh_jti,
        context=request_context,
    )
    db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL_MIN * 60,
        secure=IS_PROD,
    )
    record_audit_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type="token_refresh",
        event_category="authentication",
        description="Access and refresh tokens were rotated.",
        target_type="user",
        target_id=str(user.id),
        request_context=request_context,
        event_metadata={"refresh_version": user.refresh_version},
    )
    db.commit()
    
    return {"access_token": new_access, "token_type": "bearer"}
