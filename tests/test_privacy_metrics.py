from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from database.models.company import Company
from database.models.scan_results import ScanResult
from database.models.user import User
from database.models.wiki_page import WikiPage
from dependencies.tier_guard import require_company_admin
from routers.privacy_metrics import router as privacy_metrics_router
from services.privacy_posture_service import calculate_posture_score, map_posture_risk_level
from services.scan_service import build_scan_result_metadata
from utils.pii_taxonomy import PII_EMAIL, PII_PHONE, PII_SENSITIVE_DATA


def _session():
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
            ScanResult.__table__,
            ComplianceRecord.__table__,
            WikiPage.__table__,
            ComplianceTestRun.__table__,
            ComplianceTestCaseResult.__table__,
        ],
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
        redacted_file_path="redacted/week1.csv",
        redacted_type_counts=json.dumps(
            build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 2, PII_PHONE: 1},
                detection_results=[
                    {
                        "column": "email",
                        "detected_type": PII_EMAIL,
                        "display_name": "Email Address",
                        "policy_categories": ["GDPR_PERSONAL_DATA"],
                        "confidence_score": 0.92,
                        "signals": ["pattern_match_email_regex"],
                    }
                ],
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
        redacted_file_path="redacted/week2.csv",
        redacted_type_counts=json.dumps(
            build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 1, PII_PHONE: 3},
                detection_results=[
                    {
                        "column": "notes",
                        "detected_type": PII_SENSITIVE_DATA,
                        "display_name": "Sensitive Data Pattern",
                        "policy_categories": ["GDPR_PERSONAL_DATA"],
                        "confidence_score": 0.61,
                        "signals": ["ml_model_prediction"],
                    }
                ],
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
        redacted_file_path="redacted/older.csv",
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


def _seed_posture_dependencies(session):
    record = ComplianceRecord(
        organization_id=1,
        module="wiki",
        title="Privacy taxonomy guidance",
        status="published",
    )
    session.add(record)
    session.commit()
    session.add(
        WikiPage(
            compliance_record_id=record.id,
            slug="privacy-taxonomy-guidance",
            category="Privacy Policies",
            content_markdown="Guidance",
            version=1,
        )
    )
    session.commit()

    first_run = ComplianceTestRun(
        organization_id=1,
        category="privacy tests",
        suite_name="PII validation suite",
        dataset_name="week2.csv",
        status="passed",
        total_tests=1,
        passed_tests=1,
        failed_tests=0,
        skipped_tests=0,
    )
    second_run = ComplianceTestRun(
        organization_id=1,
        category="privacy tests",
        suite_name="PII validation suite",
        dataset_name="week2.csv",
        status="failed",
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        skipped_tests=0,
    )
    session.add_all([first_run, second_run])
    session.commit()
    session.add_all(
        [
            ComplianceTestCaseResult(
                test_run_id=first_run.id,
                name="detect_email",
                dataset_name="week2.csv",
                file_name="tests/privacy_tests.py",
                expected_result="PII_EMAIL",
                actual_result="PII_EMAIL",
                status="passed",
                last_run_at=datetime.now(timezone.utc) - timedelta(days=2),
            ),
            ComplianceTestCaseResult(
                test_run_id=second_run.id,
                name="detect_email",
                dataset_name="week2.csv",
                file_name="tests/privacy_tests.py",
                expected_result="PII_EMAIL",
                actual_result="NON_PII",
                status="failed",
                error_message="Detector missed expected email classification.",
                last_run_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
        ]
    )
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



def test_privacy_posture_score_calculation_uses_weighted_components():
    score = calculate_posture_score(
        {
            "detection_coverage": 0.9,
            "redaction_effectiveness": 0.8,
            "policy_compliance": 0.7,
            "testing_reliability": 0.6,
        }
    )

    assert score == 75



def test_privacy_posture_score_respects_custom_component_weights():
    score = calculate_posture_score(
        {
            "detection_coverage": 1.0,
            "redaction_effectiveness": 0.5,
            "policy_compliance": 0.5,
            "testing_reliability": 0.5,
        },
        weights={
            "detection_coverage": 0.4,
            "redaction_effectiveness": 0.2,
            "policy_compliance": 0.2,
            "testing_reliability": 0.2,
        },
    )

    assert score == 70



def test_privacy_posture_risk_level_mapping_matches_thresholds():
    assert map_posture_risk_level(85) == "low"
    assert map_posture_risk_level(84) == "moderate"
    assert map_posture_risk_level(69) == "elevated"
    assert map_posture_risk_level(49) == "critical"



def test_privacy_posture_endpoint_returns_expected_structure():
    session_factory = _session()
    session = session_factory()
    _seed_scans(session)
    _seed_posture_dependencies(session)
    session.close()

    app = _build_app(session_factory)
    client = TestClient(app)

    response = client.get("/privacy/posture")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) >= {"posture_score", "risk_level", "component_scores", "top_risks"}
    assert set(payload["component_scores"].keys()) == {
        "detection_coverage",
        "redaction_effectiveness",
        "policy_compliance",
        "testing_reliability",
    }
    assert isinstance(payload["top_risks"], list)
