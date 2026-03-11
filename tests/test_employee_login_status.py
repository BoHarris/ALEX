from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.company import Company
from database.models.employee import Employee
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
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _seed_employee(session, *, has_passkey: bool):
    company = Company(company_name="Bo Harris LLC")
    user = User(
        first_name="Bo",
        last_name="Harris",
        email="bo.harris@boharrisllc.internal",
        role="security_admin",
        tier="business",
        is_active=True,
        company=company,
        webauthn_credential_id="credential-id" if has_passkey else None,
        webauthn_public_key="public-key" if has_passkey else None,
    )
    employee = Employee(
        employee_id="EMP-0001",
        first_name="Bo",
        last_name="Harris",
        email=user.email,
        role="security_admin",
        status="active",
        company=company,
        user=user,
        is_internal=True,
    )
    session.add_all([company, user, employee])
    session.commit()


def test_employee_status_reports_missing_passkey(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    session = _session()
    _seed_employee(session, has_passkey=False)
    monkeypatch.setattr(webauthn_auth, "ensure_default_company_and_employee", lambda db: None)

    payload = webauthn_auth.EmployeeWebAuthnStatusRequest(email="bo.harris@boharrisllc.internal")
    result = webauthn_auth.employee_webauthn_status(payload=payload, db=session)

    assert result["employee_found"] is True
    assert result["is_active"] is True
    assert result["passkey_enrolled"] is False


def test_employee_status_reports_enrolled_passkey(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    session = _session()
    _seed_employee(session, has_passkey=True)
    monkeypatch.setattr(webauthn_auth, "ensure_default_company_and_employee", lambda db: None)

    payload = webauthn_auth.EmployeeWebAuthnStatusRequest(email="bo.harris@boharrisllc.internal")
    result = webauthn_auth.employee_webauthn_status(payload=payload, db=session)

    assert result["employee_found"] is True
    assert result["is_active"] is True
    assert result["passkey_enrolled"] is True
