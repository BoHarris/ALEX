from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from database.models.company import Company
from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from routers import scans as scans_router
from services.scan_service import ScanPipelineResult


def _make_local_test_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".test_tmp" / f"scan_api_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Company.__table__, CompanySettings.__table__, User.__table__, ScanResult.__table__],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _build_app(session_factory):
    app = FastAPI()
    app.state.pii_model = object()
    app.include_router(scans_router.router)
    app.dependency_overrides[get_current_user_context] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    def _get_test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_test_db
    return app


def test_post_scans_creates_scan_and_legacy_predict_route_is_not_mounted(monkeypatch):
    base = _make_local_test_dir()
    session_factory = _session()
    app = _build_app(session_factory)
    client = TestClient(app)

    monkeypatch.chdir(base)
    monkeypatch.setattr(scans_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "register_scan_activity", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "reserve_scan_quota", lambda *args, **kwargs: True)
    monkeypatch.setattr(scans_router, "release_scan_quota_reservation", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "extract_request_security_context", lambda request: {})

    async def _inline_run_in_threadpool(func):
        return func()

    monkeypatch.setattr(scans_router, "run_in_threadpool", _inline_run_in_threadpool)
    monkeypatch.setattr(
        scans_router,
        "run_scan_pipeline",
        lambda **kwargs: ScanPipelineResult(
            filename="sample.csv",
            pii_columns=["email"],
            redacted_file="redacted/redacted_123.csv",
            risk_score=40,
            redacted_count=2,
            total_values=4,
            redacted_type_counts={"Email Address": 2},
            scan_id=55,
        ),
    )

    try:
        response = client.post(
            "/scans",
            files={"file": ("sample.csv", b"email,notes\nada@example.com,ok\n", "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["scan_id"] == 55
        assert response.json()["redacted_file"] == "/scans/55/download"

        legacy = client.post(
            "/predict/",
            files={"file": ("sample.csv", b"email,notes\nada@example.com,ok\n", "text/csv")},
        )
        assert legacy.status_code == 404
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_get_scan_returns_scan_metadata():
    session_factory = _session()
    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="report.csv",
        file_type="csv",
        risk_score=25,
        pii_types_found="email",
        redacted_type_counts='{"Email Address": 2}',
        total_pii_found=2,
        redacted_file_path="redacted/report.csv",
        status="active",
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)

    app = _build_app(session_factory)
    client = TestClient(app)

    try:
        response = client.get(f"/scans/{scan.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["scan_id"] == scan.id
        assert payload["filename"] == "report.csv"
        assert payload["redacted_file"] == f"/scans/{scan.id}/download"
        assert payload["report_file"] == f"/scans/{scan.id}/report"
    finally:
        session.close()


def test_scan_download_and_report_routes_return_assets(monkeypatch):
    base = _make_local_test_dir()
    redacted_dir = base / "redacted"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    (redacted_dir / "report.csv").write_text("email\n[REDACTED]\n", encoding="utf-8")

    session_factory = _session()
    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="report.csv",
        file_type="csv",
        risk_score=25,
        total_pii_found=2,
        redacted_file_path="redacted/report.csv",
        status="active",
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)

    app = _build_app(session_factory)
    client = TestClient(app)

    monkeypatch.setattr(scans_router, "BASE_DIR", base)
    monkeypatch.setattr(scans_router, "REDACTED_BASE_DIR", redacted_dir.resolve())
    monkeypatch.setattr(scans_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "generate_audit_report_html", lambda scan: "<html><body>Audit report</body></html>")

    try:
        download = client.get(f"/scans/{scan.id}/download")
        assert download.status_code == 200
        assert "[REDACTED]" in download.text

        report = client.get(f"/scans/{scan.id}/report")
        assert report.status_code == 200
        assert "Audit report" in report.text
    finally:
        shutil.rmtree(base, ignore_errors=True)
        session.close()
