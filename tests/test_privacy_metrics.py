from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from database.models.company import Company
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import require_company_admin
from routers.privacy_metrics import router as privacy_metrics_router
from services.scan_service import build_scan_result_metadata
from utils.pii_taxonomy import PII_EMAIL, PII_PHONE


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Company.__table__, User.__table__, ScanResult.__table__],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _build_app(session_factory):
    app = FastAPI()
    app.include_router(privacy_metrics_router)

    def _get_test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[require_company_admin] = lambda: {
        "user_id": 1,
        "company_id": 1,
        "role": "organization_admin",
        "tier": "pro",
    }
    return app


def _seed_scans(session):
    company = Company(id=1, company_name="Acme")
    user = User(id=1, first_name="Ada", last_name="Lovelace", email="ada@example.com", role="organization_admin")
    session.add_all([company, user])
    session.commit()
    user.company_id = company.id
    session.add(user)
    session.commit()

    first_scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="week1.csv",
        file_type="csv",
        risk_score=35,
        total_pii_found=3,
        redacted_type_counts=json.dumps(
            build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 2, PII_PHONE: 1},
                detection_results=[],
            )
        ),
        scanned_at=datetime.now(timezone.utc) - timedelta(days=2),
        status="active",
    )
    second_scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="week2.csv",
        file_type="csv",
        risk_score=15,
        total_pii_found=4,
        redacted_type_counts=json.dumps(
            build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 1, PII_PHONE: 3},
                detection_results=[],
            )
        ),
        scanned_at=datetime.now(timezone.utc) - timedelta(days=1),
        status="active",
    )
    old_scan = ScanResult(
        user_id=user.id,
        company_id=company.id,
        filename="older.csv",
        file_type="csv",
        risk_score=10,
        total_pii_found=2,
        redacted_type_counts=json.dumps(
            build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 2},
                detection_results=[],
            )
        ),
        scanned_at=datetime.now(timezone.utc) - timedelta(days=45),
        status="active",
    )
    session.add_all([first_scan, second_scan, old_scan])
    session.commit()


def test_privacy_metrics_endpoint_returns_valid_payload():
    session_factory = _session()
    session = session_factory()
    _seed_scans(session)
    session.close()

    app = _build_app(session_factory)
    client = TestClient(app)

    response = client.get("/privacy-metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_scans"] == 3
    assert payload["total_redactions"] == 9
    assert payload["total_sensitive_fields_detected"] == 9


def test_privacy_metrics_pii_distribution_matches_stored_counts():
    session_factory = _session()
    session = session_factory()
    _seed_scans(session)
    session.close()

    app = _build_app(session_factory)
    client = TestClient(app)

    payload = client.get("/privacy-metrics").json()

    assert payload["pii_distribution"][PII_EMAIL] == 5
    assert payload["pii_distribution"][PII_PHONE] == 4


def test_privacy_metrics_scan_activity_groups_scans_by_date():
    session_factory = _session()
    session = session_factory()
    _seed_scans(session)
    session.close()

    app = _build_app(session_factory)
    client = TestClient(app)

    payload = client.get("/privacy-metrics", params={"activity_window_days": 7}).json()

    assert len(payload["recent_scan_activity"]) == 2
    assert payload["recent_scan_activity"][0]["scans"] == 1
    assert payload["recent_scan_activity"][1]["scans"] == 1


def test_privacy_metrics_requires_admin_access():
    session_factory = _session()
    app = FastAPI()
    app.include_router(privacy_metrics_router)

    def _get_test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    client = TestClient(app)

    response = client.get("/privacy-metrics")

    assert response.status_code in {401, 403, 422}
