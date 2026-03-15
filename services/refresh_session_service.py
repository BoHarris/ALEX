from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.models.refresh_session import RefreshSession
from services.security_service import RequestSecurityContext
from utils.auth_utils import issue_refresh_token


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



def hash_refresh_jti(refresh_jti: str) -> str:
    return hashlib.sha256(refresh_jti.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RefreshSessionValidationResult:
    ok: bool
    reason: str | None = None
    session: RefreshSession | None = None



def create_refresh_session(
    db: Session,
    *,
    user_id: int,
    refresh_jti: str,
    context: RequestSecurityContext,
) -> RefreshSession:
    session = RefreshSession(
        user_id=user_id,
        refresh_jti_hash=hash_refresh_jti(refresh_jti),
        session_binding_hash=context.session_binding_hash,
        device_info=getattr(context, "user_agent", None),
        issued_ip_address=getattr(context, "ip_address", None),
        last_seen_ip_address=getattr(context, "ip_address", None),
        last_seen_at=_utcnow(),
    )
    db.add(session)
    return session



def issue_bound_refresh_token(
    db: Session,
    *,
    user_id: int,
    refresh_version: int,
    context: RequestSecurityContext,
) -> str:
    refresh_token, refresh_jti = issue_refresh_token(user_id, refresh_version)
    create_refresh_session(
        db,
        user_id=user_id,
        refresh_jti=refresh_jti,
        context=context,
    )
    return refresh_token



def get_refresh_session(db: Session, *, refresh_jti: str) -> RefreshSession | None:
    return (
        db.query(RefreshSession)
        .filter(RefreshSession.refresh_jti_hash == hash_refresh_jti(refresh_jti))
        .first()
    )



def validate_refresh_session(
    db: Session,
    *,
    user_id: int,
    refresh_jti: str,
    context: RequestSecurityContext,
) -> RefreshSessionValidationResult:
    session = get_refresh_session(db, refresh_jti=refresh_jti)
    if not session:
        return RefreshSessionValidationResult(ok=False, reason="missing_session")
    if session.revoked or session.revoked_at is not None:
        return RefreshSessionValidationResult(ok=False, reason="revoked_session", session=session)
    if session.user_id != user_id:
        return RefreshSessionValidationResult(ok=False, reason="user_mismatch", session=session)

    stored_binding = (session.session_binding_hash or "").strip()
    current_binding = (context.session_binding_hash or "").strip()
    if stored_binding and current_binding and stored_binding != current_binding:
        return RefreshSessionValidationResult(ok=False, reason="binding_mismatch", session=session)

    session.last_seen_at = _utcnow()
    session.last_seen_ip_address = getattr(context, "ip_address", None)
    session.device_info = getattr(context, "user_agent", None) or session.device_info
    db.add(session)
    return RefreshSessionValidationResult(ok=True, session=session)



def rotate_refresh_session(
    db: Session,
    *,
    session: RefreshSession,
    new_refresh_jti: str,
    context: RequestSecurityContext,
) -> RefreshSession:
    session.refresh_jti_hash = hash_refresh_jti(new_refresh_jti)
    session.session_binding_hash = context.session_binding_hash or session.session_binding_hash
    session.device_info = getattr(context, "user_agent", None) or session.device_info
    session.last_seen_at = _utcnow()
    session.last_seen_ip_address = getattr(context, "ip_address", None)
    db.add(session)
    return session



def revoke_refresh_session(
    db: Session,
    *,
    refresh_jti: str,
) -> RefreshSession | None:
    session = get_refresh_session(db, refresh_jti=refresh_jti)
    return revoke_refresh_session_record(db, session=session)



def revoke_refresh_session_record(
    db: Session,
    *,
    session: RefreshSession | None,
) -> RefreshSession | None:
    if not session:
        return None
    session.revoked = True
    session.revoked_at = _utcnow()
    db.add(session)
    return session



def revoke_all_user_sessions(db: Session, *, user_id: int) -> int:
    sessions = db.query(RefreshSession).filter(RefreshSession.user_id == user_id, RefreshSession.revoked.is_(False)).all()
    for session in sessions:
        revoke_refresh_session_record(db, session=session)
    return len(sessions)
