from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.company import Company
from database.models.employee import Employee
from database.models.security_state import SecurityState
from database.models.user import User
from dependencies.employee_guard import require_employee_context
from utils.auth_utils import create_access_token


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            Employee.__table__,
            SecurityState.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _request(token: str):
    return SimpleNamespace(
        headers={"Authorization": f"Bearer {token}", "user-agent": "pytest"},
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(),
    )


def test_inactive_employee_user_cannot_access_compliance_workspace():
    session = _session()
    company = Company(company_name="Acme")
    user = User(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        role="security_admin",
        tier="business",
        is_active=False,
        company=company,
    )
    employee = Employee(
        employee_id="EMP-9001",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        role="security_admin",
        status="active",
        company=company,
        user=user,
        is_internal=True,
    )
    session.add_all([company, user, employee])
    session.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "tier": user.tier})

    with pytest.raises(Exception) as exc:
        require_employee_context(request=_request(token), db=session)

    assert getattr(exc.value, "status_code", None) == 401
    assert exc.value.detail["error_code"] == "ACCOUNT_DISABLED"
