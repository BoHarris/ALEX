from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.security_incident import SecurityIncident
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from routers.refresh import refresh_access_token
from utils.auth_utils import create_access_token


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
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
    refresh_token = create_access_token({"sub": str(user.id), "ver": user.refresh_version, "typ": "refresh"})
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
    refresh_token = create_access_token({"sub": str(user.id), "ver": user.refresh_version, "typ": "refresh"})
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
