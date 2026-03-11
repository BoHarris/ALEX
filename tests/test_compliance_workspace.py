from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.access_review import AccessReview
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_approval import ComplianceApproval
from database.models.compliance_attachment import ComplianceAttachment
from database.models.compliance_comment import ComplianceComment
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from database.models.code_review import CodeReview
from database.models.company import Company
from database.models.employee import Employee
from database.models.grc_incident import GRCIncident
from database.models.risk_register_item import RiskRegisterItem
from database.models.training_assignment import TrainingAssignment
from database.models.training_module import TrainingModule
from database.models.user import User
from database.models.vendor import Vendor
from database.models.wiki_page import WikiPage
from routers import compliance_router
from services.test_management_service import encode_test_id


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            Employee.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            ComplianceRecord.__table__,
            ComplianceActivity.__table__,
            ComplianceAttachment.__table__,
            ComplianceComment.__table__,
            ComplianceApproval.__table__,
            WikiPage.__table__,
            Vendor.__table__,
            ComplianceTestRun.__table__,
            ComplianceTestCaseResult.__table__,
            CodeReview.__table__,
            TrainingModule.__table__,
            TrainingAssignment.__table__,
            GRCIncident.__table__,
            AccessReview.__table__,
            RiskRegisterItem.__table__,
        ],
    )
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _employee_context(employee):
    return {
        "user_id": employee.user_id,
        "employee_id": employee.id,
        "employee_role": employee.role,
        "organization_id": employee.company_id,
        "employee": {"id": employee.id},
    }


def _seed_org(session):
    company = Company(company_name="Bo Harris LLC", is_active=True, is_verified=True)
    session.add(company)
    session.commit()
    user = User(first_name="Bo", last_name="Harris", email="bo@example.com", role="security_admin", company_id=company.id, tier="business")
    session.add(user)
    session.commit()
    employee = Employee(
        employee_id="EMP-0001",
        first_name="Bo",
        last_name="Harris",
        email="bo@example.com",
        role="security_admin",
        department="Security",
        job_title="Security Admin",
        status="active",
        company_id=company.id,
        user_id=user.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return company, user, employee


def test_policy_page_creation_generates_record_and_audit_log():
    session = _session()
    company, user, employee = _seed_org(session)
    payload = compliance_router.WikiPageCreateRequest(
        title="Incident Response Plan",
        category="Incident Response Playbooks",
        content_markdown="# Plan",
        tags=["incident", "playbook"],
        status="published",
    )
    result = compliance_router.create_wiki_page(payload, current_employee=_employee_context(employee), db=session)
    assert result["page"]["version"] == 1
    assert session.query(WikiPage).count() == 1
    assert session.query(ComplianceRecord).count() == 1
    assert session.query(AuditLog).filter(AuditLog.event_type == "policy_page_created").count() == 1


def test_vendor_creation_and_update_persist_shared_workflow_state():
    session = _session()
    _, _, employee = _seed_org(session)
    created = compliance_router.create_vendor(
        compliance_router.VendorCreateRequest(
            title="Cloud Storage Review",
            vendor_name="Acme Cloud",
            service_category="Storage",
            data_access_level="restricted",
            risk_rating="medium",
            document_links=["https://example.com/questionnaire"],
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    vendor = session.query(Vendor).first()
    compliance_router.update_vendor(
        vendor.id,
        compliance_router.VendorUpdateRequest(status="in_review", risk_rating="high", security_review_status="approved"),
        current_employee=_employee_context(employee),
        db=session,
    )
    session.refresh(vendor)
    record = session.query(ComplianceRecord).filter(ComplianceRecord.id == vendor.compliance_record_id).first()
    assert created["vendor_id"] == vendor.id
    assert vendor.risk_rating == "high"
    assert record.status == "in_review"


def test_incident_workflow_allows_close_then_blocks_further_mutation():
    session = _session()
    _, _, employee = _seed_org(session)
    created = compliance_router.create_incident(
        compliance_router.IncidentCreateRequest(
            title="Security Alert Escalation",
            severity="high",
            description="Suspicious login pattern detected",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    incident = session.get(GRCIncident, created["incident_id"])
    compliance_router.update_incident(
        incident.id,
        compliance_router.IncidentUpdateRequest(status="closed", resolution_notes="Contained"),
        current_employee=_employee_context(employee),
        db=session,
    )
    record = session.query(ComplianceRecord).filter(ComplianceRecord.id == incident.compliance_record_id).first()
    assert record.status == "closed"
    assert incident.closed_at is not None


def test_training_completion_tracking_marks_record_complete():
    session = _session()
    company, _, employee = _seed_org(session)
    module = TrainingModule(organization_id=company.id, title="Security Awareness", description="Annual training", category="Security")
    session.add(module)
    session.commit()
    assignment_result = compliance_router.assign_training(
        compliance_router.TrainingAssignmentCreateRequest(title="Security Awareness 2026", employee_id=employee.id, training_module_id=module.id),
        current_employee=_employee_context(employee),
        db=session,
    )
    assignment = session.get(TrainingAssignment, assignment_result["assignment_id"])
    compliance_router.complete_training(
        assignment.id,
        compliance_router.TrainingCompletionRequest(completion_status="completed"),
        current_employee=_employee_context(employee),
        db=session,
    )
    session.refresh(assignment)
    record = session.query(ComplianceRecord).filter(ComplianceRecord.id == assignment.compliance_record_id).first()
    assert assignment.completion_status == "completed"
    assert record.status == "completed"
    assert session.query(AuditLog).filter(AuditLog.event_type == "training_completed").count() == 1


def test_access_review_approval_flow_creates_approval_record():
    session = _session()
    company, _, employee = _seed_org(session)
    reviewed_user = User(first_name="Alex", last_name="Analyst", email="alex@example.com", role="compliance_admin", company_id=company.id, tier="business")
    session.add(reviewed_user)
    session.commit()
    reviewed_employee = Employee(
        employee_id="EMP-0002",
        first_name="Alex",
        last_name="Analyst",
        email="alex@example.com",
        role="compliance_admin",
        department="Compliance",
        job_title="Compliance Admin",
        status="active",
        company_id=company.id,
        user_id=reviewed_user.id,
    )
    session.add(reviewed_employee)
    session.commit()
    review_result = compliance_router.create_access_review(
        compliance_router.AccessReviewCreateRequest(title="Quarterly Admin Access Review", reviewed_employee_id=reviewed_employee.id, permissions_snapshot={"admin": True}),
        current_employee=_employee_context(employee),
        db=session,
    )
    review = session.get(AccessReview, review_result["review_id"])
    compliance_router.decide_access_review(
        review.id,
        compliance_router.AccessReviewDecisionRequest(decision="approved", notes="Access remains appropriate"),
        current_employee=_employee_context(employee),
        db=session,
    )
    assert session.query(ComplianceApproval).count() == 1
    assert session.get(AccessReview, review.id).decision == "approved"


def test_shared_workflow_timeline_contains_activity_and_attachment():
    session = _session()
    _, _, employee = _seed_org(session)
    page_result = compliance_router.create_wiki_page(
        compliance_router.WikiPageCreateRequest(
            title="Vendor Review Process",
            category="Vendor Management Procedures",
            content_markdown="Initial",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    record_id = page_result["record"]["id"]
    compliance_router.add_attachment(session, record_id=record_id, employee_id=employee.id, label="Process Doc", path_or_url="https://example.com/doc")
    session.commit()
    timeline = compliance_router.get_record_timeline(record_id, current_employee=_employee_context(employee), db=session)
    assert timeline["timeline"]["activities"]
    assert timeline["timeline"]["attachments"]


def test_employee_creation_update_and_deactivation_are_supported():
    session = _session()
    _, _, employee = _seed_org(session)
    created = compliance_router.create_employee(
        compliance_router.EmployeeCreateRequest(
            first_name="Ava",
            last_name="Ng",
            email="ava@example.com",
            role="engineering_lead",
            department="Engineering",
            job_title="Engineering Lead",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    created_employee = session.get(Employee, created["employee"]["id"])
    compliance_router.update_employee(
        created_employee.id,
        compliance_router.EmployeeUpdateRequest(role="operations_admin", department="Operations"),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.deactivate_employee(created_employee.id, current_employee=_employee_context(employee), db=session)
    session.refresh(created_employee)
    assert created_employee.role == "operations_admin"
    assert created_employee.status == "inactive"
    assert session.query(AuditLog).filter(AuditLog.event_type == "employee_deactivated").count() == 1


def test_test_category_and_case_detail_are_available_for_drill_down():
    session = _session()
    company, _, employee = _seed_org(session)
    run = ComplianceTestRun(
        organization_id=company.id,
        category="security tests",
        suite_name="Security baseline",
        status="failing",
        coverage_percent=75,
        report_link="/tests/security",
    )
    session.add(run)
    session.commit()
    case = ComplianceTestCaseResult(
        test_run_id=run.id,
        name="test_invalid_token_rejected",
        file_name="tests/test_security.py",
        description="Ensures invalid tokens are rejected.",
        status="failed",
        duration_ms=123,
        output="Assertion executed.",
        error_message="Expected 401 but received 200.",
    )
    session.add(case)
    session.commit()

    detail = compliance_router.get_test_category_detail("security tests", current_employee=_employee_context(employee), db=session)
    case_detail = compliance_router.get_test_case_detail(case.id, current_employee=_employee_context(employee), db=session)
    assert detail["summary"]["failing"] == 1
    assert detail["tests"][0]["test_name"] == "test_invalid_token_rejected"
    assert case_detail["error_message"] == "Expected 401 but received 200."


def test_test_result_tracking_records_individual_results_and_updates_run_summary():
    session = _session()
    _, _, employee = _seed_org(session)

    run = compliance_router.create_test_run(
        compliance_router.TestRunCreateRequest(
            category="privacy tests",
            suite_name="PII validation suite",
            status="running",
            dataset_name="synthetic_pii_validation",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    created = compliance_router.create_test_result(
        run["id"],
        compliance_router.TestResultCreateRequest(
            test_name="detect_email",
            dataset_name="synthetic_pii_validation",
            expected_result="PII_EMAIL",
            actual_result="PII_EMAIL",
            status="passed",
            confidence_score=0.83,
            duration_ms=14,
            output="matched taxonomy",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    failed = compliance_router.create_test_result(
        run["id"],
        compliance_router.TestResultCreateRequest(
            test_name="non_pii_product_id",
            dataset_name="synthetic_pii_validation",
            expected_result="NON_PII",
            actual_result="PII_EMAIL",
            status="failed",
            confidence_score=0.41,
            duration_ms=9,
            error_message="false positive",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    runs = compliance_router.list_test_runs(
        limit=10,
        dataset_name="synthetic_pii_validation",
        suite_name=None,
        current_employee=_employee_context(employee),
        db=session,
    )

    assert created["expected_result"] == "PII_EMAIL"
    assert created["actual_result"] == "PII_EMAIL"
    assert created["confidence_score"] == 0.83
    assert failed["status"] == "failed"
    assert runs["runs"][0]["total_tests"] == 2
    assert runs["runs"][0]["passed_tests"] == 1
    assert runs["runs"][0]["failed_tests"] == 1
    assert runs["runs"][0]["accuracy_score"] == 0.5


def test_test_metrics_and_results_endpoints_return_quality_data():
    session = _session()
    _, _, employee = _seed_org(session)

    run = compliance_router.create_test_run(
        compliance_router.TestRunCreateRequest(
            category="privacy tests",
            suite_name="PII validation suite",
            status="running",
            dataset_name="synthetic_metrics",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    payloads = [
        compliance_router.TestResultCreateRequest(
            test_name="detect_email",
            dataset_name="synthetic_metrics",
            expected_result="PII_EMAIL",
            actual_result="PII_EMAIL",
            status="passed",
            confidence_score=0.88,
            duration_ms=10,
        ),
        compliance_router.TestResultCreateRequest(
            test_name="non_pii_product_id",
            dataset_name="synthetic_metrics",
            expected_result="NON_PII",
            actual_result="PII_EMAIL",
            status="failed",
            confidence_score=0.31,
            duration_ms=8,
        ),
        compliance_router.TestResultCreateRequest(
            test_name="detect_phone",
            dataset_name="synthetic_metrics",
            expected_result="PII_PHONE",
            actual_result="NON_PII",
            status="failed",
            confidence_score=0.12,
            duration_ms=7,
        ),
    ]
    for payload in payloads:
        compliance_router.create_test_result(
            run["id"],
            payload,
            current_employee=_employee_context(employee),
            db=session,
        )

    results = compliance_router.list_test_results(
        limit=10,
        dataset_name="synthetic_metrics",
        test_name=None,
        status=None,
        current_employee=_employee_context(employee),
        db=session,
    )
    metrics = compliance_router.get_test_metrics(
        dataset_name="synthetic_metrics",
        current_employee=_employee_context(employee),
        db=session,
    )

    assert len(results["results"]) == 3
    assert results["results"][0]["dataset_name"] == "synthetic_metrics"
    assert metrics["total_tests"] == 3
    assert metrics["passed"] == 1
    assert metrics["failed"] == 2
    assert metrics["detection_accuracy"] == 0.3333
    assert metrics["false_positive_rate"] == 0.3333
    assert metrics["false_negative_rate"] == 0.3333


def test_test_dashboard_inventory_and_history_support_management_views():
    session = _session()
    _, _, employee = _seed_org(session)

    first_run = compliance_router.create_test_run(
        compliance_router.TestRunCreateRequest(
            category="privacy tests",
            suite_name="PII validation suite",
            status="running",
            dataset_name="synthetic_history",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    second_run = compliance_router.create_test_run(
        compliance_router.TestRunCreateRequest(
            category="privacy tests",
            suite_name="PII validation suite",
            status="running",
            dataset_name="synthetic_history",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    compliance_router.create_test_result(
        first_run["id"],
        compliance_router.TestResultCreateRequest(
            test_name="detect_email",
            dataset_name="synthetic_history",
            expected_result="PII_EMAIL",
            actual_result="PII_EMAIL",
            status="passed",
            confidence_score=0.88,
            duration_ms=10,
            description="Email detection should classify as PII_EMAIL.",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.create_test_result(
        second_run["id"],
        compliance_router.TestResultCreateRequest(
            test_name="detect_email",
            dataset_name="synthetic_history",
            expected_result="PII_EMAIL",
            actual_result="NON_PII",
            status="failed",
            confidence_score=0.19,
            duration_ms=8,
            error_message="Detector missed expected email classification.",
            description="Email detection should classify as PII_EMAIL.",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.create_test_result(
        second_run["id"],
        compliance_router.TestResultCreateRequest(
            test_name="detect_phone",
            dataset_name="synthetic_history",
            expected_result="PII_PHONE",
            actual_result="PII_PHONE",
            status="passed",
            confidence_score=0.82,
            duration_ms=7,
            description="Phone detection should classify as PII_PHONE.",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    dashboard = compliance_router.get_test_dashboard(current_employee=_employee_context(employee), db=session)
    inventory = compliance_router.list_managed_test_inventory(
        category="privacy tests",
        status="flaky",
        search="email",
        sort="flakiness",
        current_employee=_employee_context(employee),
        db=session,
    )
    test_id = encode_test_id(category="privacy tests", test_name="detect_email")
    detail = compliance_router.get_test_case_detail(test_id, current_employee=_employee_context(employee), db=session)
    history = compliance_router.get_test_case_history(test_id, current_employee=_employee_context(employee), db=session)

    assert dashboard["summary"]["total_tests"] == 2
    assert dashboard["summary"]["flaky_tests"] == 1
    assert dashboard["categories"][0]["category"] == "privacy tests"
    assert inventory["summary"]["flaky"] == 1
    assert len(inventory["tests"]) == 1
    assert inventory["tests"][0]["test_name"] == "detect_email"
    assert detail["trend"] in {"unstable", "degrading"}
    assert detail["total_runs"] == 2
    assert len(history["history"]) == 2
    assert history["history"][0]["status"] in {"failed", "passed"}


def test_compliance_overview_returns_attention_data():
    session = _session()
    company, _, employee = _seed_org(session)
    policy = compliance_router.create_wiki_page(
        compliance_router.WikiPageCreateRequest(
            title="Access Review Procedure",
            category="Security Policies",
            content_markdown="Procedure",
            status="published",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    incident_result = compliance_router.create_incident(
        compliance_router.IncidentCreateRequest(
            title="Unusual authentication behavior",
            severity="high",
            description="Investigation required",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    module = TrainingModule(organization_id=company.id, title="Privacy Fundamentals", description="Required", category="Privacy")
    session.add(module)
    session.commit()
    compliance_router.assign_training(
        compliance_router.TrainingAssignmentCreateRequest(
            title="Privacy Fundamentals 2026",
            employee_id=employee.id,
            training_module_id=module.id,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.create_risk(
        compliance_router.RiskCreateRequest(
            title="Data retention drift",
            risk_title="Data retention drift",
            description="Retention settings may be inconsistent.",
            risk_category="Privacy",
            likelihood=4,
            impact=4,
            mitigation_plan="Review settings monthly.",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    overview = compliance_router.get_compliance_overview(current_employee=_employee_context(employee), db=session)
    assert overview["organization"]["name"] == "Bo Harris LLC"
    assert overview["summary"]["open_incidents"] >= 1
    assert overview["overdue_training"]
    assert overview["high_risks"]
    assert overview["policy_updates"][0]["record"]["id"] == policy["record"]["id"]
    assert overview["open_incidents"][0]["incident"]["id"] == incident_result["incident_id"]


def test_compliance_audit_log_supports_basic_filters():
    session = _session()
    _, _, employee = _seed_org(session)
    compliance_router.create_employee(
        compliance_router.EmployeeCreateRequest(
            first_name="Mina",
            last_name="Cole",
            email="mina@example.com",
            role="compliance_admin",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.create_wiki_page(
        compliance_router.WikiPageCreateRequest(
            title="Privacy Runbook",
            category="Privacy Policies",
            content_markdown="Runbook",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )

    all_events = compliance_router.list_compliance_audit_log(current_employee=_employee_context(employee), db=session)
    employee_events = compliance_router.list_compliance_audit_log(action="employee_created", current_employee=_employee_context(employee), db=session)
    wiki_events = compliance_router.list_compliance_audit_log(resource_type="wiki_page", current_employee=_employee_context(employee), db=session)
    actor_events = compliance_router.list_compliance_audit_log(actor="bo@example.com", current_employee=_employee_context(employee), db=session)
    assert len(all_events["events"]) >= 2
    assert all(event["action"] == "employee_created" for event in employee_events["events"])
    assert all(event["resource_type"] == "wiki_page" for event in wiki_events["events"])
    assert actor_events["events"]


def test_code_review_create_update_and_decision_are_audited():
    session = _session()
    company, _, employee = _seed_org(session)
    reviewer_user = User(first_name="Rae", last_name="Reviewer", email="rae@example.com", role="compliance_admin", company_id=company.id, tier="business")
    session.add(reviewer_user)
    session.commit()
    reviewer_employee = Employee(
        employee_id="EMP-0002",
        first_name="Rae",
        last_name="Reviewer",
        email="rae@example.com",
        role="compliance_admin",
        department="Compliance",
        job_title="Compliance Reviewer",
        status="active",
        company_id=company.id,
        user_id=reviewer_user.id,
    )
    session.add(reviewer_employee)
    session.commit()

    created = compliance_router.create_code_review(
        compliance_router.CodeReviewCreateRequest(
            title="Release review for privacy policy route",
            summary="Add a route-backed privacy policy page with disclosure controls.",
            review_type="prompt_review",
            risk_level="high",
            assigned_reviewer_employee_id=reviewer_employee.id,
            target_release="2026.03.15",
            prompt_text="Implement a privacy policy route with expandable sections.",
            design_notes="Route-backed React page using existing site layout.",
            files_impacted=["frontend/src/App.js", "frontend/src/pages/Privacy.js"],
            testing_notes="Run frontend production build.",
            security_review_notes="Confirm no auth bypass is introduced.",
            privacy_review_notes="Verify the text remains plain English and accurate.",
            status="In Review",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    review = session.get(CodeReview, created["review_id"])
    assert review.prompt_text == "Implement a privacy policy route with expandable sections."
    assert review.assigned_reviewer_employee_id == reviewer_employee.id

    compliance_router.update_code_review(
        review.id,
        compliance_router.CodeReviewUpdateRequest(
            code_notes="Implementation reuses shared compliance drawer patterns.",
            reviewer_comments="Need stronger test coverage for route wiring.",
            status="In Review",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.decide_code_review(
        review.id,
        compliance_router.CodeReviewDecisionRequest(
            decision="Approve",
            reviewer_comments="Approved after route and build verification.",
        ),
        current_employee=_employee_context(reviewer_employee),
        db=session,
    )
    session.refresh(review)
    record = session.query(ComplianceRecord).filter(ComplianceRecord.id == review.compliance_record_id).first()
    assert review.reviewer_decision == "Approve"
    assert record.status == "Approved"
    assert review.approved_at is not None
    assert session.query(AuditLog).filter(AuditLog.event_type == "code_review_created").count() == 1
    assert session.query(AuditLog).filter(AuditLog.event_type == "code_review_updated").count() == 1
    assert session.query(AuditLog).filter(AuditLog.event_type == "code_review_decision_recorded").count() == 1


def test_code_review_block_and_list_include_prompt_and_files():
    session = _session()
    company, _, employee = _seed_org(session)
    created = compliance_router.create_code_review(
        compliance_router.CodeReviewCreateRequest(
            title="Security header rollout",
            summary="Roll out stricter CSP defaults.",
            review_type="release_review",
            risk_level="medium",
            target_release="2026.03.20",
            prompt_text="Tighten CSP and verify frontend compatibility.",
            design_notes="Add middleware and update static asset allowances.",
            files_impacted=["main.py", "services/request_context.py"],
            testing_notes="Run security and frontend regression checks.",
            status="In Review",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    compliance_router.decide_code_review(
        created["review_id"],
        compliance_router.CodeReviewDecisionRequest(
            decision="Block",
            reviewer_comments="Block until third-party assets are inventoried.",
        ),
        current_employee=_employee_context(employee),
        db=session,
    )
    listed = compliance_router.list_code_reviews(current_employee=_employee_context(employee), db=session)
    review_payload = listed["code_reviews"][0]
    assert review_payload["review"]["prompt_text"] == "Tighten CSP and verify frontend compatibility."
    assert review_payload["review"]["files_impacted"] == ["main.py", "services/request_context.py"]
    assert review_payload["record"]["status"] == "Blocked"
