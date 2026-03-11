from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.pending_registration import PendingRegistration
from database.models.user import User

try:
    from routers import webauthn_auth
except ModuleNotFoundError:
    webauthn_auth = None


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            PendingRegistration.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _request():
    return SimpleNamespace(
        headers={"user-agent": "pytest"},
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="req-registration"),
    )


def _patch_registration_dependencies(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    monkeypatch.setattr(webauthn_auth, "_enforce_auth_rate_limit", lambda **kwargs: None)

    def _fake_generate_registration_options(**kwargs):
        return SimpleNamespace(challenge=kwargs["challenge"])

    monkeypatch.setattr(webauthn_auth, "generate_registration_options", _fake_generate_registration_options)


def test_registration_options_do_not_create_persistent_records(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()

    result = webauthn_auth.webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.WebAuthnRegisterOptionsRequest(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            company_name="Acme",
            create_company=True,
        ),
        db=session,
    )

    assert result["user_id"] is not None
    assert session.query(User).count() == 0
    assert session.query(Company).count() == 0
    assert session.query(PendingRegistration).count() == 1


def test_successful_registration_verification_creates_persistent_records(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()

    monkeypatch.setattr(
        webauthn_auth,
        "verify_registration_response",
        lambda **kwargs: SimpleNamespace(
            credential_id=b"cred-id",
            credential_public_key=b"pub-key",
            sign_count=1,
        ),
    )

    staged = webauthn_auth.webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.WebAuthnRegisterOptionsRequest(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            company_name="Acme",
            create_company=True,
        ),
        db=session,
    )

    result = webauthn_auth.webauthn_register_verify(
        request=_request(),
        payload=webauthn_auth.WebAuthnRegisterVerifyRequest(
            user_id=staged["user_id"],
            credential={"id": "credential"},
        ),
        db=session,
    )

    user = session.query(User).first()
    company = session.query(Company).first()
    assert result["status"] == "ok"
    assert user is not None
    assert company is not None
    assert user.company_id == company.id
    assert session.query(PendingRegistration).count() == 0


def test_failed_registration_verification_discards_staged_record_without_creating_accounts(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()

    monkeypatch.setattr(
        webauthn_auth,
        "verify_registration_response",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("verification failed")),
    )

    staged = webauthn_auth.webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.WebAuthnRegisterOptionsRequest(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            company_name="Acme",
            create_company=True,
        ),
        db=session,
    )

    with pytest.raises(Exception):
        webauthn_auth.webauthn_register_verify(
            request=_request(),
            payload=webauthn_auth.WebAuthnRegisterVerifyRequest(
                user_id=staged["user_id"],
                credential={"id": "credential"},
            ),
            db=session,
        )

    assert session.query(User).count() == 0
    assert session.query(Company).count() == 0
    assert session.query(PendingRegistration).count() == 0


def test_expired_pending_registration_cannot_be_used(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()

    monkeypatch.setattr(
        webauthn_auth,
        "verify_registration_response",
        lambda **kwargs: SimpleNamespace(
            credential_id=b"cred-id",
            credential_public_key=b"pub-key",
            sign_count=1,
        ),
    )

    staged = webauthn_auth.webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.WebAuthnRegisterOptionsRequest(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            company_name="Acme",
            create_company=True,
        ),
        db=session,
    )
    registration = session.get(PendingRegistration, staged["user_id"])
    registration.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.add(registration)
    session.commit()

    with pytest.raises(Exception) as exc:
        webauthn_auth.webauthn_register_verify(
            request=_request(),
            payload=webauthn_auth.WebAuthnRegisterVerifyRequest(
                user_id=staged["user_id"],
                credential={"id": "credential"},
            ),
            db=session,
        )

    assert getattr(exc.value, "status_code", None) == 400
    assert exc.value.detail["error_code"] == "session_expired"
    assert session.query(User).count() == 0
    assert session.query(Company).count() == 0
