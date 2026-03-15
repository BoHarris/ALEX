from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from fastapi import HTTPException
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
from services import automated_changes_service


BACKLOG_CONTENT = """# Copilot Improvement Backlog

## ALEX-IMP-001
- Title: Improve task filter clarity
- Area: Governance Tasks UI
- Priority: High
- Risk: Low
- Status: Open
- Eligible for Automation: Yes
- Dependencies: None
- Suggested Branch: improvement/alex-imp-001-task-filter-clarity
- Description: Improve filter clarity in the tasks workspace.
- Suggested Improvement: Use larger segmented controls for operator filters.
- Notes: Safe UI work.

## ALEX-IMP-002
- Title: Harden automation history labels
- Area: Governance Tasks Backend
- Priority: Medium
- Risk: Low
- Status: Open
- Eligible for Automation: Yes
- Dependencies: None
- Suggested Branch: improvement/alex-imp-002-automation-history-labels
- Description: Improve task history labels for automation-owned work.
- Suggested Improvement: Add readable automation labels to the activity timeline.
- Notes: Safe backend workflow polish.

## ALEX-IMP-003
- Title: Rework auth boundaries
- Area: Platform Security
- Priority: Critical
- Risk: High
- Status: Open
- Eligible for Automation: No
- Dependencies: Security review
- Suggested Branch: improvement/alex-imp-003-auth-boundaries
- Description: Revisit workspace authorization boundaries.
- Suggested Improvement: Requires explicit human review before planning.
- Notes: Too risky for automated execution.
"""


@pytest.fixture
def backlog_tmp_dir():
    temp_dir = Path("tests") / f"_automation_tmp_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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


def _write_backlog(backlog_tmp_dir):
    backlog_path = backlog_tmp_dir / f"_automation_backlog_{uuid4().hex}.md"
    backlog_path.write_text(BACKLOG_CONTENT, encoding="utf-8")
    return backlog_path


def test_backlog_parser_and_sync_are_idempotent(monkeypatch, backlog_tmp_dir):
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)
    backlog_path = _write_backlog(backlog_tmp_dir)
    monkeypatch.setattr(automated_changes_service, "DEFAULT_BACKLOG_PATH", backlog_path)

    parsed = automated_changes_service.parse_backlog_file(backlog_path)
    assert len(parsed) == 3
    assert parsed[0].item_id == "ALEX-IMP-001"
    assert parsed[0].eligible_for_automation is True
    assert parsed[2].eligible_for_automation is False

    first = compliance_router.sync_automation_backlog(current_employee=context, db=session)
    second = compliance_router.sync_automation_backlog(current_employee=context, db=session)

    assert first["automation"]["sync"]["created"] == 3
    assert second["automation"]["sync"]["created"] == 0
    assert session.query(GovernanceTask).count() == 3
    synced = session.query(GovernanceTask).filter(GovernanceTask.source_type == "backlog_improvement").all()
    assert {task.source_id for task in synced} == {"ALEX-IMP-001", "ALEX-IMP-002", "ALEX-IMP-003"}


def test_automation_workflow_enforces_one_active_task_and_ready_for_review(monkeypatch, backlog_tmp_dir):
    session = _session()
    _, _, employee = _seed_org(session)
    context = _employee_context(employee)
    backlog_path = _write_backlog(backlog_tmp_dir)
    monkeypatch.setattr(automated_changes_service, "DEFAULT_BACKLOG_PATH", backlog_path)

    compliance_router.sync_automation_backlog(current_employee=context, db=session)

    started = compliance_router.start_next_automation_work(current_employee=context, db=session)
    task = started["task"]
    assert task["status"] == "in_progress"
    assert task["assignee_type"] == "automation"
    assert task["assignee"]["name"] == "Automated Changes"
    assert task["workflow"]["execution_mode"] == "governed_automation"

    with pytest.raises(HTTPException) as exc:
        compliance_router.start_next_automation_work(current_employee=context, db=session)
    assert exc.value.status_code == 409

    ready = compliance_router.mark_automation_work_ready_for_review(
        task["id"],
        compliance_router.AutomationMetadataRequest(
            branch_name="improvement/alex-imp-001-task-filter-clarity",
            commit_message="feat: improve task filter clarity",
            implementation_summary="Updated the filter controls and added clearer queue labels.",
            review_notes="Verify the segmented controls on desktop and mobile.",
        ),
        current_employee=context,
        db=session,
    )

    assert ready["task"]["status"] == "ready_for_review"
    assert ready["task"]["workflow"]["review_state"] == "pending_review"
    assert ready["task"]["metadata"]["branch_name"] == "improvement/alex-imp-001-task-filter-clarity"
    assert any(entry["action"] == "automation_ready_for_review" for entry in ready["task"]["activity"])


def test_automation_routes_respect_company_scoping(monkeypatch, backlog_tmp_dir):
    session = _session()
    _, _, employee = _seed_org(session)
    _, _, other_employee = _seed_org(session, email="grace@example.com", company_name="Beta")
    context = _employee_context(employee)
    other_context = _employee_context(other_employee)
    backlog_path = _write_backlog(backlog_tmp_dir)
    monkeypatch.setattr(automated_changes_service, "DEFAULT_BACKLOG_PATH", backlog_path)

    synced = compliance_router.sync_automation_backlog(current_employee=context, db=session)
    task_id = synced["automation"]["eligible_tasks"][0]["id"]

    with pytest.raises(HTTPException) as exc:
        compliance_router.assign_backlog_task_to_automation(task_id, current_employee=other_context, db=session)
    assert exc.value.status_code == 404
