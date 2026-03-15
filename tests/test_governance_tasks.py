from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_failure_task import ComplianceTestFailureTask
from database.models.compliance_test_run import ComplianceTestRun
from database.models.employee import Employee
from database.models.governance_task import GovernanceTask
from database.models.governance_task_activity import GovernanceTaskActivity
from database.models.grc_incident import GRCIncident
from database.models.security_event import SecurityEvent
from database.models.user import User
from database.models.vendor import Vendor
from routers import compliance_router
from services.governance_task_service import list_source_tasks
from utils.security_events import record_security_event


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
            Vendor.__table__,
            GRCIncident.__table__,
            ComplianceTestRun.__table__,
            ComplianceTestCaseResult.__table__,
            ComplianceTestFailureTask.__table__,
            GovernanceTask.__table__,
            GovernanceTaskActivity.__table__,
            SecurityEvent.__table__,
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


def _seed_org(session, *, email: str = "ada@example.com", company_name: str = "Acme"):
    company = Company(company_name=company_name, is_active=True, is_verified=True)
    session.add(company)
    session.commit()
    user = User(first_name="Ada", last_name="Lovelace", email=email, role="security_admin", company_id=company.id, tier="business")
    session.add(user)
    session.commit()
    employee = Employee(
        employee_id=f"EMP-{company.id:04d}",
        first_name="Ada",
        last_name="Lovelace",
        email=email,
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


def test_manual_task_create_update_assign_and_status_flow():
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)

    created = compliance_router.create_governance_task(
        compliance_router.TaskCreateRequest(
            title="Quarterly access review follow-up",
            description="Review the remaining privileged access exceptions.",
            priority="high",
        ),
        current_employee=context,
        db=session,
    )

    task = created["task"]
    assert task["task_key"] == "TASK-001"
    assert task["status"] == "todo"

    assigned = compliance_router.assign_governance_task(
        task["id"],
        compliance_router.TaskAssignRequest(assignee_employee_id=employee.id),
        current_employee=context,
        db=session,
    )
    assert assigned["task"]["assignee_employee_id"] == employee.id

    updated = compliance_router.patch_governance_task(
        task["id"],
        compliance_router.TaskUpdateRequest(priority="critical", description="Escalated for this quarter."),
        current_employee=context,
        db=session,
    )
    assert updated["task"]["priority"] == "critical"

    completed = compliance_router.update_governance_task_status(
        task["id"],
        compliance_router.TaskStatusRequest(status="done"),
        current_employee=context,
        db=session,
    )
    assert completed["task"]["status"] == "done"
    assert completed["task"]["resolved_at"] is not None


def test_incident_creation_auto_generates_linked_task():
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)

    created = compliance_router.create_incident(
        compliance_router.IncidentCreateRequest(
            title="Suspicious refresh token reuse",
            severity="high",
            description="Revoked session token was reused by a browser session.",
        ),
        current_employee=context,
        db=session,
    )

    incident = session.get(GRCIncident, created["incident_id"])
    tasks = list_source_tasks(session, company_id=employee.company_id, source_type="incident", source_id=str(incident.id))
    assert len(tasks) == 1
    assert tasks[0]["priority"] == "high"


def test_vendor_task_deduplicates_when_review_is_retriggered():
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)

    created = compliance_router.create_vendor(
        compliance_router.VendorCreateRequest(
            title="Cloud storage vendor",
            vendor_name="Acme Cloud",
            service_category="Storage",
            data_access_level="restricted",
            risk_rating="high",
            security_review_status="pending",
        ),
        current_employee=context,
        db=session,
    )
    vendor = session.get(Vendor, created["vendor_id"])
    first_tasks = list_source_tasks(session, company_id=employee.company_id, source_type="vendor_review", source_id=str(vendor.id))
    assert len(first_tasks) == 1

    compliance_router.update_vendor(
        vendor.id,
        compliance_router.VendorUpdateRequest(security_review_status="needs follow-up", risk_rating="high"),
        current_employee=context,
        db=session,
    )
    second_tasks = list_source_tasks(session, company_id=employee.company_id, source_type="vendor_review", source_id=str(vendor.id))
    assert len(second_tasks) == 1
    assert second_tasks[0]["metadata"]["recurrence_count"] >= 1


def test_repeated_failed_test_results_reuse_one_task():
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)

    run = compliance_router.create_test_run(
        compliance_router.TestRunCreateRequest(category="integration tests", suite_name="Integration", status="failed"),
        current_employee=context,
        db=session,
    )

    for _ in range(2):
        compliance_router.create_test_result(
            run["id"],
            compliance_router.TestResultCreateRequest(
                test_name="test_refresh_regression_guard",
                test_node_id="tests/test_refresh.py::test_refresh_regression_guard",
                file_path="tests/test_refresh.py",
                status="failed",
                error_message="Expected 200 but received 500.",
            ),
            current_employee=context,
            db=session,
        )

    tasks = list_source_tasks(
        session,
        company_id=employee.company_id,
        source_type="test_failure",
        source_id="tests/test_refresh.py::test_refresh_regression_guard",
    )
    assert len(tasks) == 1
    assert tasks[0]["metadata"]["latest_failed_result_id"] is not None


def test_security_event_generates_security_task_and_company_scoping_applies():
    session = _session()
    company, user, _employee = _seed_org(session)
    _other_company, _other_user, other_employee = _seed_org(session, email="grace@example.com", company_name="Beta")

    event = record_security_event(
        session,
        company_id=company.id,
        user_id=user.id,
        event_type="token_abuse",
        severity="high",
        description="Repeated invalid refresh token activity detected.",
        event_metadata={"token_issue": "refresh_session_revoked_session"},
    )
    session.commit()

    same_company_tasks = list_source_tasks(session, company_id=company.id, source_type="security_alert", source_id=str(event.id))
    other_company_tasks = compliance_router.list_governance_tasks(
        current_employee=_employee_context(other_employee),
        db=session,
    )

    assert len(same_company_tasks) == 1
    assert same_company_tasks[0]["source_module"] == "security"
    assert other_company_tasks["tasks"] == []
