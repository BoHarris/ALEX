from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from database.models.api_key import ApiKey
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.company_settings import CompanySettings
from database.models.organization_membership import OrganizationMembership
from database.models.refresh_session import RefreshSession
from database.models.scan_job import ScanJob
from database.models.scan_results import ScanResult
from database.models.security_event import SecurityEvent
from database.models.user import User
from dependencies.tier_guard import get_current_user_context, require_company_admin
from routers import organizations, protected, scan_jobs, scans, sessions
from utils.api_key_auth import ApiKeyAuthMiddleware, hash_api_key


def _make_local_test_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".test_tmp" / f"mvp_features_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            CompanySettings.__table__,
            User.__table__,
            ScanResult.__table__,
            ScanJob.__table__,
            RefreshSession.__table__,
            ApiKey.__table__,
            OrganizationMembership.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            SecurityEvent.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _override_db(app: FastAPI, session_factory):
    app.state.session_factory = session_factory

    def _get_test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db


def test_async_scan_job_submission_returns_queued_job(monkeypatch):
    session_factory = _session_factory()
    app = FastAPI()
    app.state.pii_model = object()
    app.include_router(scans.router)
    app.include_router(scan_jobs.router)
    _override_db(app, session_factory)
    app.dependency_overrides[get_current_user_context] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    client = TestClient(app)

    monkeypatch.setattr(scans, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans, "register_scan_activity", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans, "reserve_scan_quota", lambda *args, **kwargs: True)
    monkeypatch.setattr(scans, "release_scan_quota_reservation", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans, "extract_request_security_context", lambda request: SimpleNamespace(ip_address="127.0.0.1"))
    monkeypatch.setattr(scans, "should_run_async", lambda _size: True)
    monkeypatch.setattr(scans, "enqueue_scan_job", lambda *args, **kwargs: None)

    response = client.post(
        "/scans",
        files={"file": ("sample.csv", b"email,notes\nada@example.com,ok\n", "text/csv")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] is not None
    assert payload["job_status"] == "QUEUED"

    job_response = client.get(f"/scan-jobs/{payload['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "QUEUED"


def test_session_revocation_endpoint_revokes_selected_session():
    session_factory = _session_factory()
    app = FastAPI()
    app.include_router(sessions.router)
    _override_db(app, session_factory)
    app.dependency_overrides[get_current_user_context] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    client = TestClient(app)

    session = session_factory()
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add(user)
    session.commit()
    session.add_all(
        [
            RefreshSession(user_id=user.id, refresh_jti_hash="one", device_info="Browser A", revoked=False),
            RefreshSession(user_id=user.id, refresh_jti_hash="two", device_info="Browser B", revoked=False),
        ]
    )
    session.commit()
    target = session.query(RefreshSession).filter(RefreshSession.refresh_jti_hash == "two").first()
    session.close()

    response = client.delete(f"/sessions/{target.id}")

    assert response.status_code == 200
    session = session_factory()
    revoked = session.query(RefreshSession).filter(RefreshSession.id == target.id).first()
    assert revoked.revoked is True
    session.close()


def test_api_key_auth_allows_protected_route_access():
    session_factory = _session_factory()
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware)
    app.include_router(protected.router)
    _override_db(app, session_factory)
    client = TestClient(app)

    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin", company_id=1)
    raw_key = "alex_test_key"
    api_key = ApiKey(company_id=1, created_by_user_id=1, name="Automation", hashed_key=hash_api_key(raw_key), usage_count=0)
    session.add_all([company, user, api_key])
    session.commit()
    session.close()

    response = client.get("/protected/me", headers={"Authorization": f"ApiKey {raw_key}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == 1


def test_organization_invite_and_accept_flow():
    session_factory = _session_factory()
    app = FastAPI()
    app.include_router(organizations.router)
    _override_db(app, session_factory)
    client = TestClient(app)

    session = session_factory()
    company = Company(id=1, company_name="Acme")
    admin = User(id=1, first_name="Admin", last_name="User", email="admin@example.com", role="organization_admin", company_id=1)
    invitee = User(id=2, first_name="Grace", last_name="Hopper", email="grace@example.com", role="member", company_id=None)
    session.add_all([company, admin, invitee])
    session.commit()
    session.close()

    app.dependency_overrides[require_company_admin] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    invite_response = client.post(
        "/organizations/1/invite",
        json={"email": "grace@example.com", "role": "AUDITOR"},
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["status"] == "INVITED"

    app.dependency_overrides[get_current_user_context] = lambda: {
        "user_id": 2,
        "company_id": None,
        "role": "member",
        "tier": "pro",
    }
    accept_response = client.post("/organizations/1/accept-invite")
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "ACTIVE"

    session = session_factory()
    membership = session.query(OrganizationMembership).filter(OrganizationMembership.user_id == 2).first()
    invitee = session.query(User).filter(User.id == 2).first()
    assert membership.status == "ACTIVE"
    assert invitee.company_id == 1
    session.close()


def test_audit_export_bundle_contains_reports_and_metadata(monkeypatch):
    base = _make_local_test_dir()
    session_factory = _session_factory()
    app = FastAPI()
    app.include_router(organizations.router)
    _override_db(app, session_factory)
    app.dependency_overrides[require_company_admin] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    client = TestClient(app)

    session = session_factory()
    company = Company(id=1, company_name="Acme")
    admin = User(id=1, first_name="Admin", last_name="User", email="admin@example.com", role="organization_admin", company_id=1)
    scan = ScanResult(
        id=1,
        user_id=1,
        company_id=1,
        filename="report.csv",
        file_type="csv",
        risk_score=25,
        total_pii_found=2,
        redacted_file_path="redacted/report.csv",
        status="active",
    )
    event = AuditEvent(company_id=1, user_id=1, event_type="scan_completed", event_category="scan", description="Done")
    log = AuditLog(user_id=1, organization_id=1, event_type="scan_completed", event_category="scan")
    security_event = SecurityEvent(company_id=1, user_id=1, event_type="LOGIN_SUCCESS", severity="low", description="Login ok")
    session.add_all([company, admin, scan, event, log, security_event])
    session.commit()
    session.close()

    try:
        html_path = base / "report.html"
        html_path.write_text("<html><body>cached html</body></html>", encoding="utf-8")
        pdf_path = base / "report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        monkeypatch.setattr(organizations, "cache_html_report", lambda db, scan: html_path)
        monkeypatch.setattr(organizations, "cache_pdf_report", lambda db, scan: pdf_path)

        response = client.get("/organizations/1/audit-export")

        assert response.status_code == 200
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = set(archive.namelist())
        assert "scan_summary.json" in names
        assert "audit_events.json" in names
        assert "report_metadata.json" in names
        assert "reports/report.html" in names
        assert "reports/report.pdf" in names
    finally:
        shutil.rmtree(base, ignore_errors=True)
