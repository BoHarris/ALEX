from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.employee import Employee
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
            Employee.__table__,
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
        state=SimpleNamespace(request_id="req-employee-registration"),
    )


def _seed_employee(session, *, with_user: bool = False):
    company = Company(company_name="Acme")
    session.add(company)
    session.flush()

    user = None
    if with_user:
        user = User(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            role="security_admin",
            tier="business",
            company_id=company.id,
            is_active=True,
        )
        session.add(user)
        session.flush()

    employee = Employee(
        employee_id="EMP-0002",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        role="security_admin",
        status="active",
        company_id=company.id,
        user_id=user.id if user else None,
        is_internal=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _patch_registration_dependencies(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    monkeypatch.setattr(webauthn_auth, "ensure_default_company_and_employee", lambda db: None)
    monkeypatch.setattr(webauthn_auth, "_enforce_auth_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        webauthn_auth,
        "generate_registration_options",
        lambda **kwargs: SimpleNamespace(challenge=kwargs["challenge"]),
    )


def test_employee_status_stays_active_before_user_record_exists(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    session = _session()
    _seed_employee(session, with_user=False)
    monkeypatch.setattr(webauthn_auth, "ensure_default_company_and_employee", lambda db: None)

    result = webauthn_auth.employee_webauthn_status(
        payload=webauthn_auth.EmployeeWebAuthnStatusRequest(email="ada@example.com"),
        db=session,
    )

    assert result["employee_found"] is True
    assert result["is_active"] is True
    assert result["passkey_enrolled"] is False


def test_employee_registration_options_stage_pending_record_without_creating_user(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()
    _seed_employee(session, with_user=False)

    result = webauthn_auth.employee_webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.EmployeeWebAuthnRegisterOptionsRequest(email="ada@example.com"),
        db=session,
    )

    assert result["user_id"] is not None
    assert session.query(User).count() == 0
    assert session.query(PendingRegistration).count() == 1


def test_employee_registration_verify_creates_user_only_after_success(monkeypatch):
    _patch_registration_dependencies(monkeypatch)
    session = _session()
    employee = _seed_employee(session, with_user=False)
    monkeypatch.setattr(
        webauthn_auth,
        "verify_registration_response",
        lambda **kwargs: SimpleNamespace(
            credential_id=b"cred-id",
            credential_public_key=b"pub-key",
            sign_count=1,
        ),
    )

    staged = webauthn_auth.employee_webauthn_register_options(
        request=_request(),
        payload=webauthn_auth.EmployeeWebAuthnRegisterOptionsRequest(email="ada@example.com"),
        db=session,
    )

    result = webauthn_auth.employee_webauthn_register_verify(
        request=_request(),
        payload=webauthn_auth.EmployeeWebAuthnRegisterVerifyRequest(
            email="ada@example.com",
            user_id=staged["user_id"],
            credential={"id": "credential"},
        ),
        db=session,
    )

    created_user = session.query(User).filter(User.email == "ada@example.com").first()
    refreshed_employee = session.get(Employee, employee.id)

    assert result["status"] == "ok"
    assert created_user is not None
    assert refreshed_employee.user_id == created_user.id
    assert session.query(PendingRegistration).count() == 0
