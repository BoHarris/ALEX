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
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from routers import admin_router, scans as scans_router
from services import scan_service
from services.audit_service import parse_audit_event_metadata


class _FakeModel:
    def predict(self, frame):
        return [0 if index == 0 else 1 for index in range(len(frame))]


def _fake_redactor(series, column_name="", aggressive=False):
    redacted = series.astype(str).map(lambda value: "[REDACTED_PII_EMAIL]" if value else value)
    count = int(series.notna().sum())
    return redacted, count, len(series), 1.0 if len(series) else 0.0, {"PII_EMAIL": count}


def _make_local_test_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".test_tmp" / f"audit_lineage_{uuid.uuid4().hex}"
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
            User.__table__,
            CompanySettings.__table__,
            ScanResult.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _build_app(session_factory):
    app = FastAPI()
    app.state.pii_model = object()
    app.include_router(scans_router.router)
    app.include_router(admin_router.router)
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


def test_run_scan_pipeline_records_scan_created_audit_event(monkeypatch):
    base = _make_local_test_dir()
    session_factory = _session_factory()
    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()
    session.close()

    input_path = base / "sample.csv"
    input_path.write_text("email,notes\nada@example.com,ok\n", encoding="utf-8")

    monkeypatch.chdir(base)
    monkeypatch.setattr(scan_service, "SessionLocal", session_factory)
    monkeypatch.setattr(scan_service, "scan_and_redact_column_with_details", _fake_redactor)

    try:
        result = scan_service.run_scan_pipeline(
            source_path=str(input_path),
            filename="sample.csv",
            context=scan_service.ScanContext(user_id=1, company_id=1, tier="pro"),
            model=_FakeModel(),
        )

        session = session_factory()
        event = session.query(AuditEvent).filter(AuditEvent.event_type == "scan_created").one()
        metadata = parse_audit_event_metadata(event.event_metadata)

        assert event.target_type == "scan"
        assert event.target_id == str(result.scan_id)
        assert metadata["scan_id"] == result.scan_id
        assert metadata["filename"] == "sample.csv"
        assert metadata["file_type"] == "csv"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_downloads_record_audit_events_and_lineage_endpoint_returns_them(monkeypatch):
    base = _make_local_test_dir()
    redacted_dir = base / "redacted"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    (redacted_dir / "report.csv").write_text("email\n[REDACTED]\n", encoding="utf-8")

    session_factory = _session_factory()
    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    scan = ScanResult(
        id=17,
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
    session.close()

    app = _build_app(session_factory)
    client = TestClient(app)

    monkeypatch.setattr(scans_router, "BASE_DIR", base)
    monkeypatch.setattr(scans_router, "REDACTED_BASE_DIR", redacted_dir.resolve())
    monkeypatch.setattr(scans_router, "generate_audit_report_html", lambda scan: "<html><body>Audit report</body></html>")

    download = client.get("/scans/17/download")
    report = client.get("/scans/17/report")
    lineage = client.get("/scans/17/lineage")

    assert download.status_code == 200
    assert report.status_code == 200
    assert lineage.status_code == 200

    event_types = [event["event_type"] for event in lineage.json()["events"]]
    assert "redacted_file_downloaded" in event_types
    assert "report_html_downloaded" in event_types

    report_event = next(event for event in lineage.json()["events"] if event["event_type"] == "report_html_downloaded")
    assert report_event["metadata"]["scan_id"] == 17
    assert report_event["metadata"]["report_format"] == "html"


def test_admin_audit_events_support_scan_filters():
    session_factory = _session_factory()
    session = session_factory()
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    session.add_all(
        [
            AuditEvent(
                company_id=company.id,
                user_id=user.id,
                event_type="scan_completed",
                event_category="scan",
                description="Scan 10 completed.",
                target_type="scan",
                target_id="10",
                event_metadata='{"scan_id": 10, "file_type": "csv"}',
            ),
            AuditEvent(
                company_id=company.id,
                user_id=user.id,
                event_type="redacted_file_downloaded",
                event_category="scan",
                description="Scan 10 downloaded.",
                target_type="scan",
                target_id="10",
                event_metadata='{"scan_id": 10, "file_type": "csv"}',
            ),
            AuditEvent(
                company_id=company.id,
                user_id=user.id,
                event_type="scan_completed",
                event_category="scan",
                description="Scan 11 completed.",
                target_type="scan",
                target_id="11",
                event_metadata='{"scan_id": 11, "file_type": "csv"}',
            ),
        ]
    )
    session.commit()

    payload = admin_router.list_audit_events(
        limit=50,
        user_id=None,
        scan_id=10,
        event_type="scan_completed",
        date_from=None,
        date_to=None,
        current_user={"company_id": company.id, "tier": "pro"},
        db=session,
    )

    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_type"] == "scan_completed"
    assert payload["events"][0]["metadata"]["scan_id"] == 10
