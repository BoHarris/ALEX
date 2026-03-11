from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.refresh_session import RefreshSession
from database.models.security_incident import SecurityIncident
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from routers.logout import logout
from routers.refresh import refresh_access_token
from services.refresh_session_service import create_refresh_session, issue_bound_refresh_token
from services.security_service import extract_request_security_context
from utils.auth_utils import create_access_token, issue_refresh_token


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            RefreshSession.__table__,
            SecurityIncident.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _request(token: str | None = None):
    headers = {"user-agent": "pytest"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return SimpleNamespace(
        headers=headers,
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="req-auth-revocation"),
    )


def _request_with_headers(headers: dict[str, str] | None = None, token: str | None = None):
    merged_headers = {"user-agent": "pytest"}
    if headers:
        merged_headers.update(headers)
    if token:
        merged_headers["Authorization"] = f"Bearer {token}"
    return SimpleNamespace(
        headers=merged_headers,
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="req-auth-revocation"),
    )


def _make_user(session, *, is_active: bool) -> User:
    company = Company(company_name="Acme")
    user = User(
        first_name="Ada",
        last_name="Lovelace",
        email=f"{'active' if is_active else 'inactive'}@example.com",
        role="member",
        tier="free",
        is_active=is_active,
        company=company,
        refresh_version=0,
    )
    session.add_all([company, user])
    session.commit()
    session.refresh(user)
    return user


def test_active_access_token_still_valid():
    session = _session()
    user = _make_user(session, is_active=True)
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "tier": user.tier})

    current_user = get_current_user_context(request=_request(token), db=session)

    assert current_user["user_id"] == user.id
    assert current_user["email"] == user.email


def test_inactive_access_token_is_rejected():
    session = _session()
    user = _make_user(session, is_active=False)
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "tier": user.tier})

    with pytest.raises(HTTPException) as exc:
        get_current_user_context(request=_request(token), db=session)

    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "ACCOUNT_DISABLED"
    assert exc.value.detail["detail"] == "User account is inactive"


def test_inactive_refresh_token_rotation_is_rejected_and_revoked():
    session = _session()
    user = _make_user(session, is_active=False)
    refresh_token, refresh_jti = issue_refresh_token(user.id, user.refresh_version)
    create_refresh_session(
        session,
        user_id=user.id,
        refresh_jti=refresh_jti,
        context=SimpleNamespace(ip_address="127.0.0.1", session_binding_hash=None),
    )
    session.commit()
    response = Response()

    with pytest.raises(HTTPException) as exc:
        refresh_access_token(
            request=_request(),
            response=response,
            refresh_token=refresh_token,
            db=session,
        )

    session.refresh(user)
    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "ACCOUNT_DISABLED"
    assert user.refresh_version == 1
    assert "refresh_token=\"\"" in response.headers.get("set-cookie", "")


def test_active_refresh_token_rotation_succeeds():
    session = _session()
    user = _make_user(session, is_active=True)
    refresh_token, refresh_jti = issue_refresh_token(user.id, user.refresh_version)
    create_refresh_session(
        session,
        user_id=user.id,
        refresh_jti=refresh_jti,
        context=SimpleNamespace(ip_address="127.0.0.1", session_binding_hash=None),
    )
    session.commit()
    response = Response()

    payload = refresh_access_token(
        request=_request(),
        response=response,
        refresh_token=refresh_token,
        db=session,
    )

    session.refresh(user)
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert user.refresh_version == 1
    assert "refresh_token=" in response.headers.get("set-cookie", "")
    assert session.query(RefreshSession).count() == 1


def test_refresh_fails_when_session_record_is_missing():
    session = _session()
    user = _make_user(session, is_active=True)
    refresh_token, _ = issue_refresh_token(user.id, user.refresh_version)

    with pytest.raises(HTTPException) as exc:
        refresh_access_token(
            request=_request(),
            response=Response(),
            refresh_token=refresh_token,
            db=session,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "session_expired"


def test_refresh_fails_when_session_record_is_revoked():
    session = _session()
    user = _make_user(session, is_active=True)
    refresh_token, refresh_jti = issue_refresh_token(user.id, user.refresh_version)
    refresh_session = create_refresh_session(
        session,
        user_id=user.id,
        refresh_jti=refresh_jti,
        context=SimpleNamespace(ip_address="127.0.0.1", session_binding_hash=None),
    )
    refresh_session.revoked = True
    session.add(refresh_session)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        refresh_access_token(
            request=_request(),
            response=Response(),
            refresh_token=refresh_token,
            db=session,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "session_expired"


def test_logout_revokes_active_refresh_session():
    session = _session()
    user = _make_user(session, is_active=True)
    refresh_token, refresh_jti = issue_refresh_token(user.id, user.refresh_version)
    create_refresh_session(
        session,
        user_id=user.id,
        refresh_jti=refresh_jti,
        context=SimpleNamespace(ip_address="127.0.0.1", session_binding_hash=None),
    )
    session.commit()
    response = Response()

    payload = logout(
        request=_request(),
        response=response,
        refresh_token=refresh_token,
        db=session,
    )

    refresh_session = session.query(RefreshSession).first()
    assert payload["message"] == "Logged out successfully"
    assert refresh_session.revoked is True
    assert "refresh_token=\"\"" in response.headers.get("set-cookie", "")


def test_login_refresh_cookie_creation_persists_server_side_session_record():
    session = _session()
    user = _make_user(session, is_active=True)
    response = Response()

    request = _request_with_headers({"x-device-fingerprint": "known-device"})
    refresh_token = issue_bound_refresh_token(
        session,
        user_id=user.id,
        refresh_version=user.refresh_version,
        context=extract_request_security_context(request),
    )
    session.commit()
    response.set_cookie("refresh_token", refresh_token)

    refresh_session = session.query(RefreshSession).first()
    assert refresh_session is not None
    assert refresh_session.user_id == user.id
    assert refresh_session.revoked is False
    assert refresh_session.session_binding_hash is not None
    assert "refresh_token=" in response.headers.get("set-cookie", "")


def test_refresh_requires_reauthentication_when_binding_changes():
    session = _session()
    user = _make_user(session, is_active=True)
    login_response = Response()
    login_request = _request_with_headers({"x-device-fingerprint": "known-device"})
    refresh_cookie = issue_bound_refresh_token(
        session,
        user_id=user.id,
        refresh_version=user.refresh_version,
        context=extract_request_security_context(login_request),
    )
    session.commit()
    login_response.set_cookie("refresh_token", refresh_cookie)

    with pytest.raises(HTTPException) as exc:
        refresh_access_token(
            request=_request_with_headers({"x-device-fingerprint": "spoofed-device"}),
            response=Response(),
            refresh_token=refresh_cookie,
            db=session,
        )

    refresh_session = session.query(RefreshSession).first()
    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "reauthentication_required"
    assert refresh_session.revoked is True
