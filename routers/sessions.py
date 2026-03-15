from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.refresh_session import RefreshSession
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from services.refresh_session_service import get_refresh_session, revoke_all_user_sessions, revoke_refresh_session_record
from utils.api_errors import error_payload
from utils.auth_utils import decode_refresh_token_with_error

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", httponly=True, samesite="strict")


def _current_session_id(refresh_token: str | None, db: Session) -> int | None:
    if not refresh_token:
        return None
    payload, _ = decode_refresh_token_with_error(refresh_token)
    refresh_jti = payload.get("jti") if payload else None
    if not refresh_jti:
        return None
    session = get_refresh_session(db, refresh_jti=refresh_jti)
    return session.id if session else None


def _serialize_session(session: RefreshSession, *, is_current: bool) -> dict:
    return {
        "id": session.id,
        "device_info": session.device_info,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_used": session.last_seen_at.isoformat() if session.last_seen_at else None,
        "ip_address": session.last_seen_ip_address or session.issued_ip_address,
        "revoked": session.revoked,
        "is_current": is_current,
    }


@router.get("")
def list_sessions(
    refresh_token: str | None = Cookie(default=None),
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    current_id = _current_session_id(refresh_token, db)
    sessions = (
        db.query(RefreshSession)
        .filter(RefreshSession.user_id == current_user["user_id"])
        .order_by(RefreshSession.created_at.desc())
        .all()
    )
    return {"sessions": [_serialize_session(session, is_current=session.id == current_id) for session in sessions]}


@router.delete("/revoke-all")
def revoke_all_sessions(
    response: Response,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    revoked_count = revoke_all_user_sessions(db, user_id=current_user["user_id"])
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user:
        user.refresh_version = int(getattr(user, "refresh_version", 0)) + 1
        db.add(user)
    db.commit()
    _clear_refresh_cookie(response)
    return {"revoked_sessions": revoked_count}


@router.delete("/{session_id}")
def revoke_session(
    session_id: int,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    session = (
        db.query(RefreshSession)
        .filter(RefreshSession.id == session_id, RefreshSession.user_id == current_user["user_id"])
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Session not found", error_code="not_found"),
        )
    current_id = _current_session_id(refresh_token, db)
    revoke_refresh_session_record(db, session=session)
    db.commit()
    if current_id == session.id:
        _clear_refresh_cookie(response)
    return {"revoked_session_id": session.id}
