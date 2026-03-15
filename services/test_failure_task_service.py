from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_failure_task import ComplianceTestFailureTask
from database.models.compliance_test_run import ComplianceTestRun
from database.models.employee import Employee
from services.compliance_service import add_activity, create_compliance_record, log_compliance_audit, serialize_compliance_record
from services.governance_task_service import create_test_failure_remediation_task
from services.test_discovery_service import build_test_node_id


OPEN_TASK_STATUSES = {"open", "in_progress"}


def _normalize_failure_signature(message: str | None) -> str | None:
    if not message:
        return None
    normalized = " ".join(message.strip().lower().split())
    return normalized[:255] or None


def _task_priority(run: ComplianceTestRun) -> str:
    normalized = (run.category or "").lower()
    if normalized in {"security tests", "integration tests"}:
        return "high"
    if normalized == "privacy tests":
        return "medium"
    return "low"


def _task_title(*, test_name: str) -> str:
    return f"Investigate failing test: {test_name}"


def _task_description(*, test_node_id: str, file_path: str | None, suite_name: str | None, dataset_name: str | None, failure_reason: str | None) -> str:
    parts = [
        f"Pytest node: {test_node_id}",
        f"File path: {file_path or 'Not recorded'}",
        f"Suite: {suite_name or 'Not recorded'}",
        f"Environment: {dataset_name or 'default'}",
    ]
    if failure_reason:
        parts.append(f"Failure summary: {failure_reason}")
    return "\n".join(parts)


def _serialize_assignee(employee: Employee | None) -> dict | None:
    if employee is None:
        return None
    full_name = f"{employee.first_name} {employee.last_name}".strip()
    return {
        "id": employee.id,
        "name": full_name or employee.email,
        "email": employee.email,
        "role": employee.role,
    }


def _sync_governance_task(
    db: Session,
    *,
    organization_id: int,
    test_node_id: str,
    test_name: str,
    title: str,
    description: str,
    priority: str,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    assignee_employee_id: int | None,
    latest_failed_run_id: int,
    latest_failed_result_id: int,
) -> None:
    create_test_failure_remediation_task(
        db,
        company_id=organization_id,
        test_node_id=test_node_id,
        test_name=test_name,
        title=title,
        description=description,
        priority=priority,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        assignee_employee_id=assignee_employee_id,
        metadata={
            "latest_failed_run_id": latest_failed_run_id,
            "latest_failed_result_id": latest_failed_result_id,
        },
    )


def serialize_failure_task(task: ComplianceTestFailureTask, *, record: ComplianceRecord | None = None, assignee: Employee | None = None) -> dict:
    return {
        "id": task.id,
        "compliance_record_id": task.compliance_record_id,
        "organization_id": task.organization_id,
        "test_node_id": task.test_node_id,
        "latest_failed_run_id": task.latest_failed_run_id,
        "latest_failed_result_id": task.latest_failed_result_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "assignee_employee_id": task.assignee_employee_id,
        "assignee": _serialize_assignee(assignee),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "record": serialize_compliance_record(record) if record is not None else None,
    }


def get_failure_task_for_test(db: Session, *, organization_id: int, test_node_id: str) -> dict | None:
    task = (
        db.query(ComplianceTestFailureTask)
        .filter(
            ComplianceTestFailureTask.organization_id == organization_id,
            ComplianceTestFailureTask.test_node_id == test_node_id,
        )
        .order_by(ComplianceTestFailureTask.updated_at.desc(), ComplianceTestFailureTask.id.desc())
        .first()
    )
    if task is None:
        return None
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == task.compliance_record_id).first()
    assignee = db.query(Employee).filter(Employee.id == task.assignee_employee_id).first() if task.assignee_employee_id else None
    return serialize_failure_task(task, record=record, assignee=assignee)


def ensure_failure_task_for_test(db: Session, *, organization_id: int, test_node_id: str) -> dict | None:
    existing = get_failure_task_for_test(db, organization_id=organization_id, test_node_id=test_node_id)
    if existing is not None:
        return existing

    result_and_run = (
        db.query(ComplianceTestCaseResult, ComplianceTestRun)
        .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
        .filter(
            ComplianceTestRun.organization_id == organization_id,
            ComplianceTestCaseResult.status == "failed",
        )
        .order_by(ComplianceTestCaseResult.last_run_at.desc(), ComplianceTestCaseResult.id.desc())
        .all()
    )
    for result, run in result_and_run:
        candidate_node_id = build_test_node_id(test_name=result.name, file_path=result.file_name, category=run.category)
        if candidate_node_id == test_node_id:
            return upsert_failure_task_for_result(db, run=run, result=result)
    return None


def upsert_failure_task_for_result(
    db: Session,
    *,
    run: ComplianceTestRun,
    result: ComplianceTestCaseResult,
    actor_employee_id: int | None = None,
    actor_user_id: int | None = None,
) -> dict | None:
    if (result.status or "").lower() != "failed":
        return None

    test_node_id = build_test_node_id(test_name=result.name, file_path=result.file_name, category=run.category)
    existing = (
        db.query(ComplianceTestFailureTask)
        .filter(
            ComplianceTestFailureTask.organization_id == run.organization_id,
            ComplianceTestFailureTask.test_node_id == test_node_id,
            ComplianceTestFailureTask.status.in_(tuple(OPEN_TASK_STATUSES)),
        )
        .order_by(ComplianceTestFailureTask.updated_at.desc(), ComplianceTestFailureTask.id.desc())
        .first()
    )
    signature = _normalize_failure_signature(result.error_message)
    description = _task_description(
        test_node_id=test_node_id,
        file_path=result.file_name,
        suite_name=run.suite_name,
        dataset_name=result.dataset_name or run.dataset_name,
        failure_reason=result.error_message,
    )

    if existing is None:
        record = create_compliance_record(
            db,
            organization_id=run.organization_id,
            module="test_failure_task",
            title=_task_title(test_name=result.name),
            employee_id=actor_employee_id,
            status="open",
            notes=description,
            owner_employee_id=None,
        )
        task = ComplianceTestFailureTask(
            compliance_record_id=record.id,
            organization_id=run.organization_id,
            test_node_id=test_node_id,
            latest_failed_run_id=run.id,
            latest_failed_result_id=result.id,
            title=_task_title(test_name=result.name),
            description=description,
            status="open",
            priority=_task_priority(run),
            assignee_employee_id=None,
            failure_signature=signature,
        )
        db.add(task)
        add_activity(
            db,
            compliance_record_id=record.id,
            employee_id=actor_employee_id,
            action="failure_task_created",
            details=result.error_message or result.name,
        )
        log_compliance_audit(
            db,
            company_id=run.organization_id,
            user_id=actor_user_id,
            employee_id=actor_employee_id,
            action="test_failure_task_created",
            module="test_failure_task",
            resource_type="compliance_test_failure_task",
            resource_id=str(record.id),
            metadata={"test_node_id": test_node_id, "latest_failed_run_id": run.id},
        )
        db.flush()
        _sync_governance_task(
            db,
            organization_id=run.organization_id,
            test_node_id=test_node_id,
            test_name=result.name,
            title=task.title,
            description=description,
            priority=task.priority,
            actor_employee_id=actor_employee_id,
            actor_user_id=actor_user_id,
            assignee_employee_id=task.assignee_employee_id,
            latest_failed_run_id=run.id,
            latest_failed_result_id=result.id,
        )
        return serialize_failure_task(task, record=record, assignee=None)

    existing.latest_failed_run_id = run.id
    existing.latest_failed_result_id = result.id
    existing.description = description
    existing.failure_signature = signature
    existing.title = _task_title(test_name=result.name)
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == existing.compliance_record_id).first()
    if record is not None:
        record.title = existing.title
        record.notes = description
        record.status = existing.status
        record.updated_by_employee_id = actor_employee_id
        db.add(record)
        add_activity(
            db,
            compliance_record_id=record.id,
            employee_id=actor_employee_id,
            action="failure_task_updated",
            details=result.error_message or result.name,
        )
    db.add(existing)
    db.flush()
    _sync_governance_task(
        db,
        organization_id=run.organization_id,
        test_node_id=test_node_id,
        test_name=result.name,
        title=existing.title,
        description=description,
        priority=existing.priority,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        assignee_employee_id=existing.assignee_employee_id,
        latest_failed_run_id=run.id,
        latest_failed_result_id=result.id,
    )
    assignee = db.query(Employee).filter(Employee.id == existing.assignee_employee_id).first() if existing.assignee_employee_id else None
    return serialize_failure_task(existing, record=record, assignee=assignee)


def update_failure_task(
    db: Session,
    *,
    organization_id: int,
    task_id: int,
    actor_employee_id: int,
    actor_user_id: int | None,
    status: str | None = None,
    priority: str | None = None,
    assignee_employee_id: int | None = None,
) -> dict:
    task = (
        db.query(ComplianceTestFailureTask)
        .filter(
            ComplianceTestFailureTask.id == task_id,
            ComplianceTestFailureTask.organization_id == organization_id,
        )
        .first()
    )
    if task is None:
        raise ValueError("Task not found")

    if assignee_employee_id is not None:
        task.assignee_employee_id = assignee_employee_id
    if priority is not None:
        task.priority = priority
    if status is not None:
        task.status = status

    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == task.compliance_record_id).first()
    if record is not None:
        record.owner_employee_id = task.assignee_employee_id
        record.status = task.status
        record.updated_by_employee_id = actor_employee_id
        record.closed_at = datetime.now(timezone.utc) if task.status == "resolved" else None
        db.add(record)
        add_activity(
            db,
            compliance_record_id=record.id,
            employee_id=actor_employee_id,
            action="failure_task_assignment_updated",
            details=f"status={task.status}, assignee={task.assignee_employee_id}",
        )

    db.add(task)
    log_compliance_audit(
        db,
        company_id=organization_id,
        user_id=actor_user_id,
        employee_id=actor_employee_id,
        action="test_failure_task_updated",
        module="test_failure_task",
        resource_type="compliance_test_failure_task",
        resource_id=str(task.id),
        metadata={"status": task.status, "assignee_employee_id": task.assignee_employee_id, "priority": task.priority},
    )
    db.flush()
    _sync_governance_task(
        db,
        organization_id=organization_id,
        test_node_id=task.test_node_id,
        test_name=task.title.replace("Investigate failing test: ", "", 1),
        title=task.title,
        description=(task.description or record.notes) if record is not None else task.description,
        priority=task.priority,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        assignee_employee_id=task.assignee_employee_id,
        latest_failed_run_id=task.latest_failed_run_id,
        latest_failed_result_id=task.latest_failed_result_id,
    )
    assignee = db.query(Employee).filter(Employee.id == task.assignee_employee_id).first() if task.assignee_employee_id else None
    return serialize_failure_task(task, record=record, assignee=assignee)


class TestFailureTaskService:
    def __init__(self, db: Session):
        self.db = db

    def get_failure_task_for_test(self, organization_id: int, test_node_id: str) -> dict | None:
        return get_failure_task_for_test(self.db, organization_id=organization_id, test_node_id=test_node_id)

    def ensure_failure_task_for_test(self, organization_id: int, test_node_id: str) -> dict | None:
        return ensure_failure_task_for_test(self.db, organization_id=organization_id, test_node_id=test_node_id)

    def sync_governance_task(self, **kwargs) -> None:
        _sync_governance_task(self.db, **kwargs)
