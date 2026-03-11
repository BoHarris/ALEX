from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from database.models.security_state import SecurityState
from database.models.security_incident import SecurityIncident
from database.models.user import User
from dependencies.tier_guard import require_company_admin, require_security_admin
from routers import redacted_router
from services.audit_service import record_audit_event
from services.retention_service import apply_retention_state
from services.security_service import extract_request_security_context, register_failed_login
from services.security_state_store import SecurityStateStoreError, get_counter, increment_counter


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            CompanySettings.__table__,
            SecurityState.__table__,
            ScanResult.__table__,
            SecurityIncident.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _request():
    return SimpleNamespace(
        headers={"user-agent": "pytest"},
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="req-test"),
    )


def test_audit_log_creation_writes_central_log_and_legacy_event():
    session = _session()
    company = Company(company_name="Acme")
    user = User(first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)

    record_audit_event(
        session,
        company_id=company.id,
        user_id=user.id,
        event_type="login_success",
        event_category="authentication",
        description="Login succeeded.",
        target_type="user",
        target_id=str(user.id),
    )
    session.commit()

    assert session.query(AuditLog).count() == 1
    assert session.query(AuditEvent).count() == 1
    audit_log = session.query(AuditLog).first()
    assert audit_log.event_type == "login_success"
    assert audit_log.event_category == "authentication"


def test_rbac_enforcement_allows_org_admin_and_blocks_standard_user():
    allowed = require_company_admin({"role": "organization_admin", "company_id": 1})
    assert allowed["company_id"] == 1

    with pytest.raises(HTTPException) as exc:
        require_company_admin({"role": "user", "company_id": 1})
    assert exc.value.status_code == 403


def test_security_admin_enforcement_requires_security_role():
    allowed = require_security_admin({"role": "security_admin", "company_id": 1})
    assert allowed["company_id"] == 1

    with pytest.raises(HTTPException) as exc:
        require_security_admin({"role": "organization_admin", "company_id": 1})
    assert exc.value.status_code == 403


def test_archive_scan_updates_lifecycle_state_and_restore_expired_scan_fails():
    session = _session()
    company = Company(company_name="Acme")
    user = User(first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    active_scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="report.csv",
        file_type="csv",
        risk_score=20,
        total_pii_found=2,
        redacted_file_path="redacted/report.csv",
        status="active",
        retention_expiration=datetime.now(timezone.utc) + timedelta(days=10),
    )
    expired_scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="old.csv",
        file_type="csv",
        risk_score=10,
        total_pii_found=1,
        redacted_file_path="redacted/old.csv",
        status="archived",
        archived_at=datetime.now(timezone.utc) - timedelta(days=30),
        retention_expiration=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add_all([active_scan, expired_scan])
    session.commit()

    result = redacted_router.archive_scan(
        scan_id=active_scan.id,
        request=_request(),
        current_user={"user_id": user.id, "role": "organization_admin", "company_id": company.id},
        db=session,
    )
    session.refresh(active_scan)
    assert result["status"] == "archived"
    assert active_scan.status == "archived"

    apply_retention_state(session, expired_scan)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        redacted_router.restore_scan(
            scan_id=expired_scan.id,
            request=_request(),
            current_user={"user_id": user.id, "role": "organization_admin", "company_id": company.id},
            db=session,
        )
    assert exc.value.status_code == 403


def test_failed_login_threshold_generates_security_alert():
    session = _session()
    company = Company(company_name="Acme")
    user = User(first_name="Ada", last_name="Lovelace", email="ada@example.com", role="user")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    for _ in range(5):
        register_failed_login(
            session,
            email=user.email,
            organization_id=company.id,
            user_id=user.id,
            context=SimpleNamespace(ip_address="127.0.0.1", device_fingerprint="pytest", request_id="r1"),
        )
    session.commit()

    alerts = session.query(AuditLog).filter(AuditLog.event_category == "security_alert").all()
    assert alerts
    assert alerts[-1].event_type == "suspicious_login"


def test_retention_policy_marks_expired_scan():
    session = _session()
    scan = ScanResult(
        user_id=1,
        company_id=1,
        filename="expired.csv",
        file_type="csv",
        risk_score=5,
        total_pii_found=1,
        status="active",
        retention_expiration=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session.add(scan)
    session.commit()

    apply_retention_state(session, scan)
    session.commit()
    session.refresh(scan)
    assert scan.status == "expired"


def test_request_security_context_ignores_untrusted_forwarded_headers(monkeypatch):
    request = SimpleNamespace(
        headers={
            "user-agent": "pytest-agent",
            "x-forwarded-for": "203.0.113.10",
            "x-device-fingerprint": "client-asserted",
        },
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="req-test"),
    )

    monkeypatch.setattr("services.security_service.TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr("services.security_service.TRUSTED_PROXY_IPS", set())
    context = extract_request_security_context(request)

    assert context.ip_address == "127.0.0.1"
    assert context.advisory_ip_address == "203.0.113.10"
    assert context.trusted_proxy is False
    assert context.device_fingerprint != "client-asserted"


def test_request_security_context_uses_trusted_forwarded_headers(monkeypatch):
    request = SimpleNamespace(
        headers={"user-agent": "pytest-agent", "x-forwarded-for": "203.0.113.10"},
        client=SimpleNamespace(host="10.0.0.5"),
        state=SimpleNamespace(request_id="req-test"),
    )

    monkeypatch.setattr("services.security_service.TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr("services.security_service.TRUSTED_PROXY_IPS", {"10.0.0.5"})
    context = extract_request_security_context(request)

    assert context.ip_address == "203.0.113.10"
    assert context.trusted_proxy is True


def test_security_counter_persists_across_sessions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[SecurityState.__table__])
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session_one = session_factory()
    count_one = increment_counter(
        session_one,
        namespace="security:test",
        state_key="shared-key",
        window_seconds=120,
    )
    session_one.commit()
    session_one.close()

    session_two = session_factory()
    count_two = get_counter(
        session_two,
        namespace="security:test",
        state_key="shared-key",
    )
    session_two.close()

    assert count_one == 1
    assert count_two == 1


def test_security_counter_expired_state_resets():
    session = _session()
    count = increment_counter(
        session,
        namespace="security:test",
        state_key="expiring-key",
        window_seconds=0,
    )
    session.commit()

    current = get_counter(
        session,
        namespace="security:test",
        state_key="expiring-key",
    )

    assert count == 1
    assert current == 0


def test_register_failed_login_raises_when_shared_store_unavailable(monkeypatch):
    session = _session()

    def _raise(*args, **kwargs):
        raise SecurityStateStoreError()

    monkeypatch.setattr("services.security_service.increment_counter", _raise)

    with pytest.raises(SecurityStateStoreError):
        register_failed_login(
            session,
            email="ada@example.com",
            organization_id=1,
            user_id=1,
            context=SimpleNamespace(ip_address="127.0.0.1", device_fingerprint="pytest", request_id="r1"),
        )
