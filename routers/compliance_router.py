from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.params import Query as FastAPIQueryParam
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.access_review import AccessReview
from database.models.audit_log import AuditLog
from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_attachment import ComplianceAttachment
from database.models.compliance_comment import ComplianceComment
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from database.models.code_review import CodeReview
from database.models.company import Company
from database.models.employee import Employee
from database.models.grc_incident import GRCIncident
from database.models.hr_control import HRControl
from database.models.risk_register_item import RiskRegisterItem
from database.models.training_assignment import TrainingAssignment
from database.models.training_module import TrainingModule
from database.models.vendor import Vendor
from database.models.wiki_page import WikiPage
from dependencies.employee_guard import (
    require_compliance_workspace_access,
    require_employee_context,
    require_security_or_compliance_admin,
)
from services.compliance_service import (
    add_activity,
    add_approval,
    add_attachment,
    create_compliance_record,
    ensure_default_company_and_employee,
    ensure_test_runs,
    log_compliance_audit,
    serialize_compliance_record,
    serialize_employee,
    update_record_status,
)
from services.test_metrics_service import (
    compute_test_metrics,
    create_tracked_test_run,
    list_test_results as query_test_results,
    record_test_result,
)
from services.test_management_service import (
    get_managed_test_detail,
    get_managed_test_history,
    get_test_management_dashboard,
    list_managed_tests,
)
from services.governance_task_service import (
    create_employee_followup_task,
    create_incident_remediation_task,
    create_task,
    create_vendor_review_task,
    get_task_detail,
    list_source_tasks,
    list_tasks,
    summarize_tasks,
    update_task as update_governance_task,
)
from services.automated_changes_service import (
    assign_task_to_automation,
    block_automation_task,
    list_automation_tasks,
    mark_task_ready_for_review,
    start_automation_task,
    start_next_automation_task,
    sync_backlog_tasks,
    update_automation_task_metadata,
    return_task_to_backlog,
)
from services.test_failure_task_service import ensure_failure_task_for_test, get_failure_task_for_test, update_failure_task
from services.test_discovery_service import build_test_node_id, normalize_test_file_path, split_test_node_id
from services.test_execution_service import (
    ACTIVE_RUN_STATUSES,
    DuplicateTestRunError,
    UnsupportedTestExecutionError,
    parse_test_run_metadata,
    queue_test_execution,
    start_category_run,
    start_full_suite_run,
    start_single_test_run,
)
from utils.api_errors import error_payload
from services.task_generation_service import TaskGenerationService

# Initialize TaskGenerationService
task_generation_service = TaskGenerationService(db_session=Depends(get_db))

router = APIRouter(prefix="/compliance", tags=["Compliance Workspace"])


def _demo_workspace_seeding_enabled() -> bool:
    configured = (os.getenv("ENABLE_DEMO_WORKSPACE_SEEDING") or "").strip().lower()
    if configured:
        return configured == "true"
    return os.getenv("ENV", "development").strip().lower() != "production"


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _parse_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _record_or_404(db: Session, record_id: int, organization_id: int) -> ComplianceRecord:
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id, ComplianceRecord.organization_id == organization_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=error_payload(detail="Compliance record not found", error_code="not_found"))
    return record


def _wiki_or_404(db: Session, wiki_id: int, organization_id: int) -> tuple[WikiPage, ComplianceRecord]:
    wiki = db.query(WikiPage).filter(WikiPage.id == wiki_id).first()
    if not wiki:
        raise HTTPException(status_code=404, detail=error_payload(detail="Wiki page not found", error_code="not_found"))
    return wiki, _record_or_404(db, wiki.compliance_record_id, organization_id)


def _vendor_or_404(db: Session, vendor_id: int, organization_id: int) -> tuple[Vendor, ComplianceRecord]:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail=error_payload(detail="Vendor not found", error_code="not_found"))
    return vendor, _record_or_404(db, vendor.compliance_record_id, organization_id)


def _incident_or_404(db: Session, incident_id: int, organization_id: int) -> tuple[GRCIncident, ComplianceRecord]:
    incident = db.query(GRCIncident).filter(GRCIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=error_payload(detail="Incident not found", error_code="not_found"))
    return incident, _record_or_404(db, incident.compliance_record_id, organization_id)


def _access_review_or_404(db: Session, review_id: int, organization_id: int) -> tuple[AccessReview, ComplianceRecord]:
    review = db.query(AccessReview).filter(AccessReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=error_payload(detail="Access review not found", error_code="not_found"))
    return review, _record_or_404(db, review.compliance_record_id, organization_id)


def _training_assignment_or_404(db: Session, assignment_id: int, organization_id: int) -> tuple[TrainingAssignment, ComplianceRecord]:
    assignment = db.query(TrainingAssignment).filter(TrainingAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail=error_payload(detail="Training assignment not found", error_code="not_found"))
    return assignment, _record_or_404(db, assignment.compliance_record_id, organization_id)


def _hr_control_or_404(db: Session, control_id: int, organization_id: int) -> tuple[HRControl, ComplianceRecord]:
    control = db.query(HRControl).filter(HRControl.id == control_id).first()
    if not control:
        raise HTTPException(status_code=404, detail=error_payload(detail="HR control not found", error_code="not_found"))
    return control, _record_or_404(db, control.compliance_record_id, organization_id)


def _risk_or_404(db: Session, risk_id: int, organization_id: int) -> tuple[RiskRegisterItem, ComplianceRecord]:
    risk = db.query(RiskRegisterItem).filter(RiskRegisterItem.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail=error_payload(detail="Risk not found", error_code="not_found"))
    return risk, _record_or_404(db, risk.compliance_record_id, organization_id)


def _code_review_or_404(db: Session, review_id: int, organization_id: int) -> tuple[CodeReview, ComplianceRecord]:
    review = db.query(CodeReview).filter(CodeReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=error_payload(detail="Code review not found", error_code="not_found"))
    return review, _record_or_404(db, review.compliance_record_id, organization_id)


def _timeline(db: Session, record_id: int) -> dict:
    activities = db.query(ComplianceActivity).filter(ComplianceActivity.compliance_record_id == record_id).order_by(ComplianceActivity.created_at.asc()).all()
    comments = db.query(ComplianceComment).filter(ComplianceComment.compliance_record_id == record_id).order_by(ComplianceComment.created_at.asc()).all()
    attachments = db.query(ComplianceAttachment).filter(ComplianceAttachment.compliance_record_id == record_id).order_by(ComplianceAttachment.created_at.asc()).all()
    return {
        "activities": [
            {"id": item.id, "employee_id": item.employee_id, "action": item.action, "details": item.details, "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in activities
        ],
        "comments": [
            {"id": item.id, "employee_id": item.employee_id, "comment": item.comment, "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in comments
        ],
        "attachments": [
            {"id": item.id, "employee_id": item.employee_id, "label": item.label, "path_or_url": item.path_or_url, "attachment_type": item.attachment_type, "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in attachments
        ],
    }


def _safe_json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _normalize_optional_query_value(value):
    return None if isinstance(value, FastAPIQueryParam) else value


def _serialize_test_run(run: ComplianceTestRun, triggered_by: Employee | None = None, *, include_logs: bool = False) -> dict:
    started_at = run.started_at.isoformat() if run.started_at else None
    completed_at = run.completed_at.isoformat() if run.completed_at else None
    created_at = run.run_at.isoformat() if run.run_at else None
    payload = {
        "id": run.id,
        "suite_name": run.suite_name,
        "category": run.category,
        "dataset_name": run.dataset_name,
        "status": run.status,
        "run_type": run.run_type,
        "trigger_source": run.trigger_source,
        "execution_engine": run.execution_engine,
        "pytest_node_id": run.pytest_node_id,
        "triggered_by_user_id": run.triggered_by_user_id,
        "triggered_by_employee_id": run.triggered_by_employee_id,
        "triggered_by": {
            "id": triggered_by.id,
            "name": f"{triggered_by.first_name} {triggered_by.last_name}".strip() or triggered_by.email,
            "email": triggered_by.email,
        } if triggered_by is not None else None,
        "total_tests": run.total_tests,
        "passed_tests": run.passed_tests,
        "failed_tests": run.failed_tests,
        "skipped_tests": run.skipped_tests,
        "accuracy_score": float(run.accuracy_score) if run.accuracy_score is not None else None,
        "coverage_percent": float(run.coverage_percent) if run.coverage_percent is not None else None,
        "report_link": run.report_link,
        "started_at": started_at,
        "completed_at": completed_at,
        "run_at": created_at,
        "created_at": created_at,
        "return_code": run.return_code,
        "failure_summary": run.failure_summary,
        "metadata": parse_test_run_metadata(run.metadata_json),
        "is_active": run.status in ACTIVE_RUN_STATUSES,
    }
    if started_at and completed_at:
        started = datetime.fromisoformat(started_at)
        completed = datetime.fromisoformat(completed_at)
        payload["duration_ms"] = max(0, round((completed - started).total_seconds() * 1000))
    else:
        payload["duration_ms"] = None
    if include_logs:
        payload["stdout"] = run.stdout
        payload["stderr"] = run.stderr
    return payload


def _serialize_test_case(case: ComplianceTestCaseResult, run: ComplianceTestRun | None = None) -> dict:
    file_path = normalize_test_file_path(case.file_name)
    payload = {
        "id": case.id,
        "test_name": case.name,
        "test_node_id": build_test_node_id(test_name=case.name, file_path=file_path, category=run.category if run is not None else None),
        "dataset_name": case.dataset_name,
        "status": case.status,
        "description": case.description,
        "file_path": file_path,
        "file_name": file_path,
        "expected_result": case.expected_result,
        "actual_result": case.actual_result,
        "confidence_score": float(case.confidence_score) if case.confidence_score is not None else None,
        "duration_ms": case.duration_ms,
        "last_run_timestamp": case.last_run_at.isoformat() if case.last_run_at else None,
        "output_summary": case.output,
        "error_details": case.error_message,
    }
    if run is not None:
        payload["category"] = run.category
        payload["suite_name"] = run.suite_name
    return payload


def _test_run_or_404(db: Session, run_id: int, organization_id: int) -> ComplianceTestRun:
    run = (
        db.query(ComplianceTestRun)
        .filter(
            ComplianceTestRun.id == run_id,
            ComplianceTestRun.organization_id == organization_id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Test run not found", error_code="not_found"))
    return run


def _serialize_test_run_result(db: Session, *, organization_id: int, case: ComplianceTestCaseResult, run: ComplianceTestRun) -> dict:
    payload = _serialize_test_case(case, run)
    payload["linked_tasks"] = list_source_tasks(
        db,
        company_id=organization_id,
        source_type="test_failure",
        source_id=payload["test_node_id"],
    )
    return payload


def _queue_test_run(background_tasks: BackgroundTasks | None, db: Session, run: ComplianceTestRun) -> ComplianceTestRun:
    queue_test_execution(
        run.id,
        background_tasks=background_tasks,
        execute_inline=background_tasks is None,
    )
    db.refresh(run)
    return run


def _serialize_audit_log(event: AuditLog, employee_lookup: dict[int, Employee]) -> dict:
    employee = employee_lookup.get(event.user_id) if event.user_id is not None else None
    actor_name = None
    actor_email = None
    if employee:
        actor_name = f"{employee.first_name} {employee.last_name}".strip()
        actor_email = employee.email
    return {
        "id": event.id,
        "timestamp": event.created_at.isoformat() if event.created_at else None,
        "actor_user_id": event.user_id,
        "actor_name": actor_name,
        "actor_email": actor_email,
        "action": event.event_type,
        "category": event.event_category,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "ip_address": event.ip_address,
        "device_fingerprint": event.device_fingerprint,
        "details": _safe_json(event.event_metadata),
        "outcome": "alert" if event.event_category == "security_alert" else "recorded",
    }


class WorkflowPayload(BaseModel):
    title: str
    status: str = "draft"
    due_date: datetime | None = None
    review_date: datetime | None = None
    notes: str | None = None
    owner_employee_id: int | None = None


class WikiPageCreateRequest(WorkflowPayload):
    category: str
    content_markdown: str = ""
    parent_page_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    template_name: str | None = None


class WikiPageUpdateRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    review_date: datetime | None = None
    notes: str | None = None
    content_markdown: str | None = None
    tags: list[str] | None = None


class VendorCreateRequest(WorkflowPayload):
    vendor_name: str
    service_category: str
    data_access_level: str
    contract_start_date: datetime | None = None
    contract_end_date: datetime | None = None
    risk_rating: str | None = None
    security_review_status: str = "pending"
    last_review_date: datetime | None = None
    document_links: list[str] = Field(default_factory=list)


class VendorUpdateRequest(BaseModel):
    status: str | None = None
    risk_rating: str | None = None
    security_review_status: str | None = None
    last_review_date: datetime | None = None
    notes: str | None = None
    document_links: list[str] | None = None


class TestRunCreateRequest(BaseModel):
    category: str
    suite_name: str
    status: str
    dataset_name: str | None = None
    coverage_percent: Decimal | None = None
    report_link: str | None = None


class TestResultCreateRequest(BaseModel):
    test_name: str
    test_node_id: str | None = None
    dataset_name: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    description: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    status: str
    confidence_score: Decimal | None = None
    duration_ms: int | None = None
    output: str | None = None
    error_message: str | None = None


class TestFailureTaskCreateRequest(BaseModel):
    priority: str | None = "medium"
    assignee_employee_id: int | None = None


class TestFailureTaskUpdateRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee_employee_id: int | None = None


class AccessReviewCreateRequest(WorkflowPayload):
    reviewed_employee_id: int
    permissions_snapshot: dict = Field(default_factory=dict)


class AccessReviewDecisionRequest(BaseModel):
    decision: str
    notes: str | None = None


class TrainingAssignmentCreateRequest(WorkflowPayload):
    employee_id: int
    training_module_id: int
    due_date: datetime | None = None


class TrainingCompletionRequest(BaseModel):
    completion_status: str = "completed"
    quiz_score: Decimal | None = None


class IncidentCreateRequest(WorkflowPayload):
    severity: str
    description: str
    assigned_to_employee_id: int | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IncidentUpdateRequest(BaseModel):
    status: str | None = None
    assigned_to_employee_id: int | None = None
    resolution_notes: str | None = None
    root_cause: str | None = None
    lessons_learned: str | None = None


class HRControlCreateRequest(WorkflowPayload):
    employee_id: int
    control_type: str


class HRControlUpdateRequest(BaseModel):
    status: str
    completed_at: datetime | None = None
    reviewed_by_employee_id: int | None = None


class RiskCreateRequest(WorkflowPayload):
    risk_title: str
    description: str
    risk_category: str
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    mitigation_plan: str | None = None
    owner_employee_id: int | None = None
    review_date: datetime | None = None


class RiskUpdateRequest(BaseModel):
    status: str | None = None
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    mitigation_plan: str | None = None
    review_date: datetime | None = None


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_email(value: str) -> str:
    normalized = _normalize_required_text(value, field_name="email").lower()
    local, separator, domain = normalized.partition("@")
    if separator != "@" or not local or not domain or "." not in domain:
        raise ValueError("email must be a valid email address")
    return normalized


def _display_field_name(info: ValidationInfo) -> str:
    return (info.field_name or "field").replace("_", " ")


TASK_STATUS_VALUES = {"todo", "in_progress", "blocked", "ready_for_review", "done", "canceled"}
TASK_PRIORITY_VALUES = {"low", "medium", "high", "critical"}


def _normalize_task_status(value: str, *, field_name: str = "status") -> str:
    normalized = _normalize_required_text(value, field_name=field_name).lower()
    if normalized not in TASK_STATUS_VALUES:
        allowed = ", ".join(sorted(TASK_STATUS_VALUES))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return normalized


def _normalize_task_priority(value: str, *, field_name: str = "priority") -> str:
    normalized = _normalize_required_text(value, field_name=field_name).lower()
    if normalized not in TASK_PRIORITY_VALUES:
        allowed = ", ".join(sorted(TASK_PRIORITY_VALUES))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return normalized


def _employee_for_company_or_404(db: Session, employee_id: int, organization_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == organization_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Employee not found", error_code="not_found"))
    return employee


def _raise_automation_error(exc: ValueError) -> None:
    message = str(exc) or "Automation workflow action could not be completed"
    status_code = 404 if "not found" in message.lower() else 409
    raise HTTPException(status_code=status_code, detail=error_payload(detail=message, error_code="conflict" if status_code == 409 else "not_found")) from exc


class EmployeeCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str
    department: str | None = None
    job_title: str | None = None
    status: str = "active"

    @field_validator("first_name", "last_name", "role", "status")
    @classmethod
    def validate_required_employee_text(cls, value: str, info: ValidationInfo) -> str:
        return _normalize_required_text(value, field_name=_display_field_name(info))

    @field_validator("department", "job_title")
    @classmethod
    def normalize_optional_employee_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("email")
    @classmethod
    def validate_employee_email(cls, value: str) -> str:
        return _normalize_email(value)


class EmployeeUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    role: str | None = None
    department: str | None = None
    job_title: str | None = None
    status: str | None = None

    @field_validator("first_name", "last_name", "role", "status")
    @classmethod
    def validate_optional_employee_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, field_name=_display_field_name(info))

    @field_validator("department", "job_title")
    @classmethod
    def normalize_optional_employee_update_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("email")
    @classmethod
    def validate_optional_employee_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_email(value)


class TrainingModuleCreateRequest(BaseModel):
    title: str
    description: str | None = None
    category: str
    document_link: str | None = None


class CodeReviewCreateRequest(WorkflowPayload):
    summary: str
    review_type: str = "internal_change"
    risk_level: str = "medium"
    assigned_reviewer_employee_id: int | None = None
    target_release: str | None = None
    prompt_text: str
    design_notes: str | None = None
    code_notes: str | None = None
    files_impacted: list[str] = Field(default_factory=list)
    testing_notes: str | None = None
    security_review_notes: str | None = None
    privacy_review_notes: str | None = None
    reviewer_comments: str | None = None


class CodeReviewUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    review_type: str | None = None
    status: str | None = None
    risk_level: str | None = None
    assigned_reviewer_employee_id: int | None = None
    target_release: str | None = None
    prompt_text: str | None = None
    design_notes: str | None = None
    code_notes: str | None = None
    files_impacted: list[str] | None = None
    testing_notes: str | None = None
    security_review_notes: str | None = None
    privacy_review_notes: str | None = None
    reviewer_comments: str | None = None


class CodeReviewDecisionRequest(BaseModel):
    decision: str
    reviewer_comments: str | None = None


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    source_type: str = "manual"
    source_id: str | None = None
    source_module: str = "manual"
    incident_id: int | None = None
    assignee_employee_id: int | None = None
    due_date: datetime | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_task_title(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="title")

    @field_validator("description", "source_id")
    @classmethod
    def normalize_optional_task_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("status")
    @classmethod
    def validate_task_status(cls, value: str) -> str:
        return _normalize_task_status(value)

    @field_validator("priority")
    @classmethod
    def validate_task_priority(cls, value: str) -> str:
        return _normalize_task_priority(value)

    @field_validator("source_type", "source_module")
    @classmethod
    def normalize_required_task_source_text(cls, value: str, info: ValidationInfo) -> str:
        return _normalize_required_text(value, field_name=_display_field_name(info)).lower()


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_employee_id: int | None = None
    due_date: datetime | None = None
    incident_id: int | None = None
    metadata: dict | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_task_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, field_name="title")

    @field_validator("description")
    @classmethod
    def normalize_optional_task_description(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("status")
    @classmethod
    def validate_optional_task_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_task_status(value)

    @field_validator("priority")
    @classmethod
    def validate_optional_task_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_task_priority(value)


class TaskAssignRequest(BaseModel):
    assignee_employee_id: int | None = None


class TaskStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _normalize_task_status(value)


class TaskLinkIncidentRequest(BaseModel):
    incident_id: int


class TaskLinkSourceRequest(BaseModel):
    source_type: str
    source_id: str
    source_module: str

    @field_validator("source_type", "source_module")
    @classmethod
    def normalize_source_link_text(cls, value: str, info: ValidationInfo) -> str:
        return _normalize_required_text(value, field_name=_display_field_name(info)).lower()

    @field_validator("source_id")
    @classmethod
    def validate_source_link_id(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="source id")


class SourceTaskCreateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    assignee_employee_id: int | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_source_task_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, field_name="title")

    @field_validator("description")
    @classmethod
    def normalize_optional_source_task_description(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("priority")
    @classmethod
    def validate_optional_source_task_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_task_priority(value)


class AutomationMetadataRequest(BaseModel):
    branch_name: str | None = None
    commit_message: str | None = None
    implementation_summary: str | None = None
    review_notes: str | None = None

    @field_validator("branch_name", "commit_message", "implementation_summary", "review_notes")
    @classmethod
    def normalize_automation_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class AutomationBlockRequest(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


@router.get("/me")
def get_current_employee(current_employee: dict = Depends(require_employee_context), db: Session = Depends(get_db)):
    if _demo_workspace_seeding_enabled():
        ensure_default_company_and_employee(db)
        ensure_test_runs(db, current_employee["organization_id"])
    employees = db.query(Employee).filter(Employee.company_id == current_employee["organization_id"]).order_by(Employee.first_name.asc()).all()
    company = db.query(Company).filter(Company.id == current_employee["organization_id"]).first()
    return {
        "employee": current_employee["employee"],
        "organization_id": current_employee["organization_id"],
        "organization_name": company.company_name if company else "Compliance Workspace",
        "directory_count": len(employees),
    }


@router.get("/dashboard")
def get_compliance_dashboard(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    organization_id = current_employee["organization_id"]
    task_summary = summarize_tasks(db, company_id=organization_id, my_employee_id=current_employee["employee_id"])
    policy_count = db.query(func.count(WikiPage.id)).join(ComplianceRecord, ComplianceRecord.id == WikiPage.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id).scalar() or 0
    vendor_total = db.query(func.count(Vendor.id)).join(ComplianceRecord, ComplianceRecord.id == Vendor.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id).scalar() or 0
    open_incidents = db.query(func.count(GRCIncident.id)).join(ComplianceRecord, ComplianceRecord.id == GRCIncident.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, ComplianceRecord.status != "closed").scalar() or 0
    completed_training = db.query(func.count(TrainingAssignment.id)).join(ComplianceRecord, ComplianceRecord.id == TrainingAssignment.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, TrainingAssignment.completion_status == "completed").scalar() or 0
    total_training = db.query(func.count(TrainingAssignment.id)).join(ComplianceRecord, ComplianceRecord.id == TrainingAssignment.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id).scalar() or 0
    access_reviews_pending = db.query(func.count(AccessReview.id)).join(ComplianceRecord, ComplianceRecord.id == AccessReview.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, AccessReview.decision == "pending").scalar() or 0
    high_risk_items = db.query(func.count(RiskRegisterItem.id)).join(ComplianceRecord, ComplianceRecord.id == RiskRegisterItem.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, RiskRegisterItem.risk_score >= 15).scalar() or 0
    pending_code_reviews = db.query(func.count(CodeReview.id)).join(ComplianceRecord, ComplianceRecord.id == CodeReview.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, ComplianceRecord.status.in_(["Draft", "In Review", "Changes Requested"])).scalar() or 0
    approved_code_reviews = db.query(func.count(CodeReview.id)).join(ComplianceRecord, ComplianceRecord.id == CodeReview.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, ComplianceRecord.status == "Approved").scalar() or 0
    blocked_code_reviews = db.query(func.count(CodeReview.id)).join(ComplianceRecord, ComplianceRecord.id == CodeReview.compliance_record_id).filter(ComplianceRecord.organization_id == organization_id, ComplianceRecord.status == "Blocked").scalar() or 0
    test_runs = db.query(ComplianceTestRun).filter(ComplianceTestRun.organization_id == organization_id).order_by(ComplianceTestRun.run_at.desc()).limit(10).all()
    return {
        "summary": {
            "policy_coverage": policy_count,
            "vendor_risk_status": vendor_total,
            "open_incidents": open_incidents,
            "access_review_status": access_reviews_pending,
            "training_completion_rate": round((completed_training / total_training) * 100, 2) if total_training else 0,
            "high_risk_items": high_risk_items,
            "pending_code_reviews": pending_code_reviews,
            "approved_code_reviews": approved_code_reviews,
            "blocked_code_reviews": blocked_code_reviews,
            "open_tasks": task_summary["open"],
            "overdue_tasks": task_summary["overdue"],
            "critical_tasks": task_summary["critical"],
        },
        "test_coverage_status": [
            {
                "id": run.id,
                "category": run.category,
                "suite_name": run.suite_name,
                "status": run.status,
                "coverage_percent": float(run.coverage_percent) if run.coverage_percent is not None else None,
                "report_link": run.report_link,
                "run_at": run.run_at.isoformat() if run.run_at else None,
            }
            for run in test_runs
        ],
    }


@router.get("/overview")
def get_compliance_overview(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    organization_id = current_employee["organization_id"]
    company = db.query(Company).filter(Company.id == organization_id).first()
    dashboard = get_compliance_dashboard(current_employee=current_employee, db=db)
    recent_records = (
        db.query(ComplianceRecord)
        .filter(ComplianceRecord.organization_id == organization_id)
        .order_by(ComplianceRecord.updated_at.desc())
        .limit(12)
        .all()
    )
    open_incidents = (
        db.query(GRCIncident, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == GRCIncident.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id, ComplianceRecord.status != "closed")
        .order_by(ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    pending_reviews = (
        db.query(AccessReview, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == AccessReview.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id, AccessReview.decision == "pending")
        .order_by(ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    overdue_training = (
        db.query(TrainingAssignment, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == TrainingAssignment.compliance_record_id)
        .filter(
            ComplianceRecord.organization_id == organization_id,
            TrainingAssignment.completion_status != "completed",
            TrainingAssignment.due_date.isnot(None),
            TrainingAssignment.due_date < datetime.now(timezone.utc),
        )
        .order_by(TrainingAssignment.due_date.asc())
        .limit(6)
        .all()
    )
    high_risks = (
        db.query(RiskRegisterItem, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == RiskRegisterItem.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id, RiskRegisterItem.risk_score >= 12)
        .order_by(RiskRegisterItem.risk_score.desc(), ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    policy_updates = (
        db.query(WikiPage, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == WikiPage.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id)
        .order_by(ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    vendor_reviews_due = (
        db.query(Vendor, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == Vendor.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id)
        .order_by(Vendor.last_review_date.asc().nullsfirst(), ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    recent_audit = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(12)
        .all()
    )
    code_reviews = (
        db.query(CodeReview, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == CodeReview.compliance_record_id)
        .filter(ComplianceRecord.organization_id == organization_id)
        .order_by(ComplianceRecord.updated_at.desc())
        .limit(6)
        .all()
    )
    recent_tasks = list_tasks(db, company_id=organization_id, only_open=True)[:6]
    task_summary = summarize_tasks(db, company_id=organization_id, my_employee_id=current_employee["employee_id"])
    employee_lookup = {
        employee.user_id: employee
        for employee in db.query(Employee).filter(Employee.company_id == organization_id).all()
        if employee.user_id is not None
    }
    return {
        "organization": {
            "id": organization_id,
            "name": company.company_name if company else "Compliance Workspace",
        },
        "summary": dashboard["summary"],
        "testing_summary": dashboard["test_coverage_status"],
        "task_summary": task_summary,
        "recent_tasks": recent_tasks,
        "recent_activity": [
            {
                "id": record.id,
                "module": record.module,
                "title": record.title,
                "status": record.status,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            for record in recent_records
        ],
        "open_incidents": [
            {
                "record": serialize_compliance_record(record),
                "incident": {
                    "id": incident.id,
                    "severity": incident.severity,
                    "assigned_to_employee_id": incident.assigned_to_employee_id,
                    "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                },
            }
            for incident, record in open_incidents
        ],
        "pending_reviews": [
            {
                "record": serialize_compliance_record(record),
                "review": {
                    "id": review.id,
                    "reviewed_employee_id": review.reviewed_employee_id,
                    "reviewer_employee_id": review.reviewer_employee_id,
                    "decision": review.decision,
                },
            }
            for review, record in pending_reviews
        ],
        "overdue_training": [
            {
                "record": serialize_compliance_record(record),
                "assignment": {
                    "id": assignment.id,
                    "employee_id": assignment.employee_id,
                    "training_module_id": assignment.training_module_id,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "completion_status": assignment.completion_status,
                },
            }
            for assignment, record in overdue_training
        ],
        "high_risks": [
            {
                "record": serialize_compliance_record(record),
                "risk": {
                    "id": risk.id,
                    "risk_title": risk.risk_title,
                    "risk_category": risk.risk_category,
                    "risk_score": risk.risk_score,
                    "review_date": risk.review_date.isoformat() if risk.review_date else None,
                },
            }
            for risk, record in high_risks
        ],
        "policy_updates": [
            {
                "record": serialize_compliance_record(record),
                "page": {
                    "id": page.id,
                    "category": page.category,
                    "version": page.version,
                    "tags": _parse_json_list(page.tags),
                },
            }
            for page, record in policy_updates
        ],
        "vendor_reviews_due": [
            {
                "record": serialize_compliance_record(record),
                "vendor": {
                    "id": vendor.id,
                    "vendor_name": vendor.vendor_name,
                    "risk_rating": vendor.risk_rating,
                    "security_review_status": vendor.security_review_status,
                    "contract_end_date": vendor.contract_end_date.isoformat() if vendor.contract_end_date else None,
                    "last_review_date": vendor.last_review_date.isoformat() if vendor.last_review_date else None,
                },
            }
            for vendor, record in vendor_reviews_due
        ],
        "recent_audit_log": [_serialize_audit_log(event, employee_lookup) for event in recent_audit],
        "code_review_snapshot": [
            {
                "record": serialize_compliance_record(record),
                "review": {
                    "id": review.id,
                    "review_type": review.review_type,
                    "risk_level": review.risk_level,
                    "assigned_reviewer_employee_id": review.assigned_reviewer_employee_id,
                    "target_release": review.target_release,
                    "reviewer_decision": review.reviewer_decision,
                },
            }
            for review, record in code_reviews
        ],
    }


@router.get("/audit-log")
def list_compliance_audit_log(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    organization_id = current_employee["organization_id"]
    if not isinstance(limit, int):
        limit = 100
    if not isinstance(actor, str):
        actor = None
    if not isinstance(action, str):
        action = None
    if not isinstance(resource_type, str):
        resource_type = None
    query = db.query(AuditLog).filter(AuditLog.organization_id == organization_id)
    if action:
        query = query.filter(AuditLog.event_type == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    events = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    employees = db.query(Employee).filter(Employee.company_id == organization_id).all()
    employee_lookup = {employee.user_id: employee for employee in employees if employee.user_id is not None}
    serialized = [_serialize_audit_log(event, employee_lookup) for event in events]
    if actor:
        actor_term = actor.lower()
        serialized = [
            event
            for event in serialized
            if actor_term in (event["actor_name"] or "").lower() or actor_term in (event["actor_email"] or "").lower()
        ]
    return {"events": serialized}


@router.get("/tasks/summary")
def get_governance_task_summary(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    return {
        "summary": summarize_tasks(
            db,
            company_id=current_employee["organization_id"],
            my_employee_id=current_employee["employee_id"],
        )
    }


@router.get("/automation/tasks")
def get_automation_queue(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    return list_automation_tasks(db, company_id=current_employee["organization_id"])


@router.post("/automation/sync-backlog")
def sync_automation_backlog(current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        automation = sync_backlog_tasks(
            db,
            company_id=current_employee["organization_id"],
            actor_user_id=current_employee["user_id"],
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    db.commit()
    return {"automation": automation}


@router.post("/automation/tasks/start-next")
def start_next_automation_work(current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = start_next_automation_task(
            db,
            company_id=current_employee["organization_id"],
            actor_user_id=current_employee["user_id"],
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=409, detail=error_payload(detail="No eligible automation task is ready to start.", error_code="conflict"))
    db.commit()
    return {"task": task, "automation": list_automation_tasks(db, company_id=current_employee["organization_id"])}


@router.post("/automation/tasks/{task_id}/assign")
def assign_backlog_task_to_automation(task_id: int, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = assign_task_to_automation(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.post("/automation/tasks/{task_id}/start")
def start_automation_work(task_id: int, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = start_automation_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_user_id=current_employee["user_id"],
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.post("/automation/tasks/{task_id}/block")
def block_automation_work(task_id: int, payload: AutomationBlockRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = block_automation_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_user_id=current_employee["user_id"],
            reason=payload.reason,
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.post("/automation/tasks/{task_id}/ready-for-review")
def mark_automation_work_ready_for_review(task_id: int, payload: AutomationMetadataRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = mark_task_ready_for_review(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_user_id=current_employee["user_id"],
            branch_name=payload.branch_name,
            commit_message=payload.commit_message,
            implementation_summary=payload.implementation_summary,
            review_notes=payload.review_notes,
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.post("/automation/tasks/{task_id}/return-to-backlog")
def return_automation_work_to_backlog(task_id: int, payload: AutomationMetadataRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = return_task_to_backlog(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            review_notes=payload.review_notes,
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.patch("/automation/tasks/{task_id}/metadata")
def patch_automation_task_metadata(task_id: int, payload: AutomationMetadataRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    try:
        task = update_automation_task_metadata(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            branch_name=payload.branch_name,
            commit_message=payload.commit_message,
            implementation_summary=payload.implementation_summary,
            review_notes=payload.review_notes,
        )
    except ValueError as exc:
        _raise_automation_error(exc)
    if task is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": task}


@router.get("/tasks")
def list_governance_tasks(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    source_module: str | None = Query(default=None),
    assignee_employee_id: int | None = Query(default=None),
    open_only: bool | None = Query(default=None),
    due_before: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    my_tasks: bool = Query(default=False),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    if not isinstance(status, str):
        status = None
    if not isinstance(priority, str):
        priority = None
    if not isinstance(source_module, str):
        source_module = None
    if not isinstance(assignee_employee_id, int):
        assignee_employee_id = None
    if not isinstance(open_only, bool):
        open_only = None
    if not isinstance(due_before, datetime):
        due_before = None
    if not isinstance(search, str):
        search = None
    if not isinstance(my_tasks, bool):
        my_tasks = False
    tasks = list_tasks(
        db,
        company_id=current_employee["organization_id"],
        status=status,
        priority=priority,
        source_module=source_module,
        assignee_employee_id=assignee_employee_id,
        only_open=open_only,
        due_before=due_before,
        search=search,
        mine_employee_id=current_employee["employee_id"] if my_tasks else None,
    )
    return {"tasks": tasks}


@router.post("/tasks")
def create_governance_task(
    payload: TaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    if payload.incident_id is not None:
        _incident_or_404(db, payload.incident_id, current_employee["organization_id"])
    task = create_task(
        db,
        company_id=current_employee["organization_id"],
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        source_type=payload.source_type,
        source_id=payload.source_id,
        source_module=payload.source_module,
        incident_id=payload.incident_id,
        assignee_employee_id=payload.assignee_employee_id,
        reporter_employee_id=current_employee["employee_id"],
        due_date=payload.due_date,
        metadata=payload.metadata,
        actor_user_id=current_employee["user_id"],
    )
    db.commit()
    detail = get_task_detail(db, company_id=current_employee["organization_id"], task_id=task.id) if task is not None else None
    if detail is None:
        raise HTTPException(status_code=503, detail=error_payload(detail="Task workflow is unavailable", error_code="service_unavailable"))
    return {"task": detail}


@router.get("/tasks/{task_id}")
def get_governance_task(task_id: int, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    detail = get_task_detail(db, company_id=current_employee["organization_id"], task_id=task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    return {"task": detail}


@router.patch("/tasks/{task_id}")
def patch_governance_task(
    task_id: int,
    payload: TaskUpdateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    provided_fields = payload.model_fields_set
    if "assignee_employee_id" in provided_fields and payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    if "incident_id" in provided_fields and payload.incident_id is not None:
        _incident_or_404(db, payload.incident_id, current_employee["organization_id"])

    update_kwargs = {}
    for field_name in ("title", "description", "status", "priority", "assignee_employee_id", "due_date", "incident_id", "metadata"):
        if field_name in provided_fields:
            update_kwargs[field_name] = getattr(payload, field_name)

    detail = update_governance_task(
        db,
        company_id=current_employee["organization_id"],
        task_id=task_id,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        **update_kwargs,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": detail}


@router.post("/tasks/{task_id}/assign")
def assign_governance_task(
    task_id: int,
    payload: TaskAssignRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    detail = update_governance_task(
        db,
        company_id=current_employee["organization_id"],
        task_id=task_id,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        assignee_employee_id=payload.assignee_employee_id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": detail}


@router.post("/tasks/{task_id}/status")
def update_governance_task_status(
    task_id: int,
    payload: TaskStatusRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    detail = update_governance_task(
        db,
        company_id=current_employee["organization_id"],
        task_id=task_id,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        status=payload.status,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": detail}


@router.post("/tasks/{task_id}/link-incident")
def link_governance_task_to_incident(
    task_id: int,
    payload: TaskLinkIncidentRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    incident, _record = _incident_or_404(db, payload.incident_id, current_employee["organization_id"])
    detail = update_governance_task(
        db,
        company_id=current_employee["organization_id"],
        task_id=task_id,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        incident_id=incident.id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": detail}


@router.post("/tasks/{task_id}/link-source")
def link_governance_task_to_source(
    task_id: int,
    payload: TaskLinkSourceRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    detail = update_governance_task(
        db,
        company_id=current_employee["organization_id"],
        task_id=task_id,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        source_type=payload.source_type,
        source_id=payload.source_id,
        source_module=payload.source_module,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Task not found", error_code="not_found"))
    db.commit()
    return {"task": detail}


@router.post("/tasks/from/incident/{incident_id}")
def create_task_from_incident(
    incident_id: int,
    payload: SourceTaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    incident, record = _incident_or_404(db, incident_id, current_employee["organization_id"])
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    task = create_incident_remediation_task(
        db,
        company_id=current_employee["organization_id"],
        incident=incident,
        incident_title=payload.title or record.title,
        incident_status=record.status,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
    )
    if task is None:
        raise HTTPException(status_code=503, detail=error_payload(detail="Task workflow is unavailable", error_code="service_unavailable"))
    if any(value is not None for value in (payload.description, payload.priority, payload.assignee_employee_id, payload.due_date, payload.title)):
        update_governance_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task.id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            title=payload.title or task.title,
            description=payload.description or incident.description,
            priority=payload.priority or task.priority,
            assignee_employee_id=payload.assignee_employee_id,
            due_date=payload.due_date,
        )
    db.commit()
    return {"task": get_task_detail(db, company_id=current_employee["organization_id"], task_id=task.id)}


@router.post("/tasks/from/vendor/{vendor_id}")
def create_task_from_vendor(
    vendor_id: int,
    payload: SourceTaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    vendor, record = _vendor_or_404(db, vendor_id, current_employee["organization_id"])
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    task = create_vendor_review_task(
        db,
        company_id=current_employee["organization_id"],
        vendor=vendor,
        title=payload.title or f"Start vendor review: {vendor.vendor_name}",
        description=payload.description or "Review vendor evidence, contract posture, and current risk signals.",
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        due_date=payload.due_date or vendor.contract_end_date or record.review_date,
    )
    if task is None:
        raise HTTPException(status_code=503, detail=error_payload(detail="Task workflow is unavailable", error_code="service_unavailable"))
    if payload.priority or payload.assignee_employee_id:
        update_governance_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task.id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            priority=payload.priority or task.priority,
            assignee_employee_id=payload.assignee_employee_id,
        )
    db.commit()
    return {"task": get_task_detail(db, company_id=current_employee["organization_id"], task_id=task.id)}


@router.post("/tasks/from/test-failure")
def create_task_from_test_failure_query(
    test_id: str = Query(...),
    payload: SourceTaskCreateRequest | None = None,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    effective_payload = payload or SourceTaskCreateRequest()
    return create_task_from_test_failure(test_id, effective_payload, current_employee=current_employee, db=db)


@router.post("/tasks/from/test-failure/{test_id:path}")
def create_task_from_test_failure(
    test_id: str,
    payload: SourceTaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    detail = get_test_case_detail(test_id, current_employee=current_employee, db=db)
    if detail.get("status") != "failed":
        raise HTTPException(status_code=409, detail=error_payload(detail="Task can only be created for failing tests", error_code="conflict"))
    if detail.get("task") is None:
        ensure_failure_task_for_test(
            db,
            organization_id=current_employee["organization_id"],
            test_node_id=detail["test_node_id"],
        )
    tasks = list_source_tasks(db, company_id=current_employee["organization_id"], source_type="test_failure", source_id=detail["test_node_id"])
    if not tasks:
        raise HTTPException(status_code=503, detail=error_payload(detail="Task workflow is unavailable", error_code="service_unavailable"))
    task_id = tasks[0]["id"]
    if any(value is not None for value in (payload.title, payload.description, payload.priority, payload.assignee_employee_id, payload.due_date)):
        update_governance_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task_id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            title=payload.title or tasks[0]["title"],
            description=payload.description or tasks[0]["description"],
            priority=payload.priority or tasks[0]["priority"],
            assignee_employee_id=payload.assignee_employee_id,
            due_date=payload.due_date,
        )
    db.commit()
    return {"task": get_task_detail(db, company_id=current_employee["organization_id"], task_id=task_id)}


@router.post("/tasks/from/employee/{employee_id}")
def create_task_from_employee(
    employee_id: int,
    payload: SourceTaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == current_employee["organization_id"]).first()
    if employee is None:
        raise HTTPException(status_code=404, detail=error_payload(detail="Employee not found", error_code="not_found"))
    if payload.assignee_employee_id is not None:
        _employee_for_company_or_404(db, payload.assignee_employee_id, current_employee["organization_id"])
    task = create_employee_followup_task(
        db,
        company_id=current_employee["organization_id"],
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}".strip(),
        title=payload.title or f"Employee governance follow-up: {employee.first_name} {employee.last_name}",
        description=payload.description or "Review employee access, profile completeness, and open governance follow-up.",
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        priority=payload.priority or "medium",
    )
    if task is None:
        raise HTTPException(status_code=503, detail=error_payload(detail="Task workflow is unavailable", error_code="service_unavailable"))
    if payload.assignee_employee_id or payload.due_date:
        update_governance_task(
            db,
            company_id=current_employee["organization_id"],
            task_id=task.id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            assignee_employee_id=payload.assignee_employee_id,
            due_date=payload.due_date,
        )
    db.commit()
    return {"task": get_task_detail(db, company_id=current_employee["organization_id"], task_id=task.id)}


@router.get("/directory")
def list_employee_directory(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    employees = db.query(Employee).filter(Employee.company_id == current_employee["organization_id"]).order_by(Employee.first_name.asc(), Employee.last_name.asc()).all()
    return {"employees": [serialize_employee(item) for item in employees]}


@router.post("/directory")
def create_employee(payload: EmployeeCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    normalized_email = payload.email
    if db.query(Employee).filter(Employee.email == normalized_email).first():
        raise HTTPException(status_code=409, detail=error_payload(detail="Employee email already exists", error_code="conflict"))
    employee_count = db.query(func.count(Employee.id)).filter(Employee.company_id == current_employee["organization_id"]).scalar() or 0
    employee = Employee(
        employee_id=f"EMP-{employee_count + 1:04d}",
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=normalized_email,
        role=payload.role,
        department=payload.department,
        job_title=payload.job_title,
        status=payload.status,
        company_id=current_employee["organization_id"],
        is_internal=True,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    if not employee.department or not employee.job_title:
        create_employee_followup_task(
            db,
            company_id=current_employee["organization_id"],
            employee_id=employee.id,
            employee_name=f"{employee.first_name} {employee.last_name}".strip(),
            title=f"Complete employee governance profile: {employee.first_name} {employee.last_name}",
            description="Employee profile is missing required governance metadata. Add department and job title details.",
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            priority="medium",
        )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="employee_created", module="employee_directory", resource_type="employee", resource_id=str(employee.id), metadata={"role": employee.role})
    db.commit()
    return {"employee": serialize_employee(employee)}


@router.put("/directory/{employee_id}")
def update_employee(employee_id: int, payload: EmployeeUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == current_employee["organization_id"]).first()
    if not employee:
        raise HTTPException(status_code=404, detail=error_payload(detail="Employee not found", error_code="not_found"))
    if payload.email is not None:
        duplicate = (
            db.query(Employee)
            .filter(Employee.email == payload.email, Employee.id != employee.id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail=error_payload(detail="Employee email already exists", error_code="conflict"))
    for field in ("first_name", "last_name", "role", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(employee, field, value)
    for field in ("department", "job_title"):
        if field in payload.model_fields_set:
            setattr(employee, field, getattr(payload, field))
    if payload.email is not None:
        employee.email = payload.email
    db.add(employee)
    if employee.status in {"inactive", "suspended"}:
        create_employee_followup_task(
            db,
            company_id=current_employee["organization_id"],
            employee_id=employee.id,
            employee_name=f"{employee.first_name} {employee.last_name}".strip(),
            title=f"Review access for inactive employee: {employee.first_name} {employee.last_name}",
            description="Employee status changed away from active. Review access, assignments, and related governance records.",
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            priority="high",
        )
    elif not employee.department or not employee.job_title:
        create_employee_followup_task(
            db,
            company_id=current_employee["organization_id"],
            employee_id=employee.id,
            employee_name=f"{employee.first_name} {employee.last_name}".strip(),
            title=f"Complete employee governance profile: {employee.first_name} {employee.last_name}",
            description="Employee profile is missing required governance metadata. Add department and job title details.",
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            priority="medium",
        )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="employee_updated", module="employee_directory", resource_type="employee", resource_id=str(employee.id), metadata={"status": employee.status, "role": employee.role})
    db.commit()
    return {"employee": serialize_employee(employee)}


@router.post("/directory/{employee_id}/deactivate")
def deactivate_employee(employee_id: int, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == current_employee["organization_id"]).first()
    if not employee:
        raise HTTPException(status_code=404, detail=error_payload(detail="Employee not found", error_code="not_found"))
    employee.status = "inactive"
    db.add(employee)
    create_employee_followup_task(
        db,
        company_id=current_employee["organization_id"],
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}".strip(),
        title=f"Access audit for inactive employee: {employee.first_name} {employee.last_name}",
        description="Employee was deactivated. Review current access, assigned training, and remediation follow-up.",
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        priority="high",
    )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="employee_deactivated", module="employee_directory", resource_type="employee", resource_id=str(employee.id))
    db.commit()
    return {"employee": serialize_employee(employee)}


@router.get("/records")
def list_compliance_records(
    module: str | None = Query(default=None),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    query = db.query(ComplianceRecord).filter(ComplianceRecord.organization_id == current_employee["organization_id"])
    if module:
        query = query.filter(ComplianceRecord.module == module)
    records = query.order_by(ComplianceRecord.updated_at.desc()).all()
    return {"records": [serialize_compliance_record(record) for record in records]}


@router.get("/records/{record_id}/timeline")
def get_record_timeline(record_id: int, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    record = _record_or_404(db, record_id, current_employee["organization_id"])
    return {"record": serialize_compliance_record(record), "timeline": _timeline(db, record.id)}


@router.post("/wiki/pages")
def create_wiki_page(payload: WikiPageCreateRequest, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    record = create_compliance_record(
        db,
        organization_id=current_employee["organization_id"],
        module="wiki",
        title=payload.title,
        employee_id=current_employee["employee_id"],
        status=payload.status,
        due_date=payload.due_date,
        review_date=payload.review_date,
        notes=payload.notes,
        owner_employee_id=payload.owner_employee_id,
    )
    page = WikiPage(
        compliance_record_id=record.id,
        parent_page_id=payload.parent_page_id,
        slug=f"{payload.category.lower().replace(' ', '-')}-{payload.title.lower().replace(' ', '-')}-{record.id}",
        category=payload.category,
        template_name=payload.template_name,
        tags=json.dumps(payload.tags),
        content_markdown=payload.content_markdown,
        version=1,
    )
    db.add(page)
    log_compliance_audit(
        db,
        company_id=current_employee["organization_id"],
        user_id=current_employee["user_id"],
        employee_id=current_employee["employee_id"],
        action="policy_page_created",
        module="wiki",
        resource_type="wiki_page",
        resource_id=str(record.id),
        metadata={"category": payload.category},
    )
    db.commit()
    db.refresh(page)
    return {"record": serialize_compliance_record(record), "page": {"id": page.id, "slug": page.slug, "category": page.category, "version": page.version}}


@router.get("/wiki/pages")
def list_wiki_pages(search: str | None = Query(default=None), current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    query = db.query(WikiPage, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == WikiPage.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"])
    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(func.lower(ComplianceRecord.title).like(pattern))
    results = query.order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "pages": [
            {
                "record": serialize_compliance_record(record),
                "page": {
                    "id": page.id,
                    "parent_page_id": page.parent_page_id,
                    "slug": page.slug,
                    "category": page.category,
                    "template_name": page.template_name,
                    "tags": _parse_json_list(page.tags),
                    "content_markdown": page.content_markdown,
                    "version": page.version,
                },
            }
            for page, record in results
        ]
    }


@router.put("/wiki/pages/{wiki_id}")
def update_wiki_page(wiki_id: int, payload: WikiPageUpdateRequest, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    page, record = _wiki_or_404(db, wiki_id, current_employee["organization_id"])
    if payload.title is not None:
        record.title = payload.title
    if payload.status is not None:
        update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status)
    if payload.review_date is not None:
        record.review_date = payload.review_date
    if payload.notes is not None:
        record.notes = payload.notes
    if payload.content_markdown is not None:
        page.content_markdown = payload.content_markdown
        page.version += 1
        add_activity(db, compliance_record_id=record.id, employee_id=current_employee["employee_id"], action="wiki_updated", details=f"Version {page.version}")
    if payload.tags is not None:
        page.tags = json.dumps(payload.tags)
    record.updated_by_employee_id = current_employee["employee_id"]
    db.add(record)
    db.add(page)
    log_compliance_audit(
        db,
        company_id=current_employee["organization_id"],
        user_id=current_employee["user_id"],
        employee_id=current_employee["employee_id"],
        action="policy_page_updated",
        module="wiki",
        resource_type="wiki_page",
        resource_id=str(page.id),
        metadata={"version": page.version},
    )
    db.commit()
    return {"record": serialize_compliance_record(record), "page": {"id": page.id, "version": page.version}}


@router.post("/vendors")
def create_vendor(payload: VendorCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    record = create_compliance_record(
        db,
        organization_id=current_employee["organization_id"],
        module="vendor",
        title=payload.title or payload.vendor_name,
        employee_id=current_employee["employee_id"],
        status=payload.status,
        due_date=payload.due_date,
        review_date=payload.review_date,
        notes=payload.notes,
        owner_employee_id=payload.owner_employee_id,
    )
    vendor = Vendor(
        compliance_record_id=record.id,
        vendor_name=payload.vendor_name,
        service_category=payload.service_category,
        data_access_level=payload.data_access_level,
        contract_start_date=payload.contract_start_date,
        contract_end_date=payload.contract_end_date,
        risk_rating=payload.risk_rating,
        security_review_status=payload.security_review_status,
        last_review_date=payload.last_review_date,
        document_links=json.dumps(payload.document_links),
    )
    db.add(vendor)
    db.flush()
    for link in payload.document_links:
        add_attachment(db, record_id=record.id, employee_id=current_employee["employee_id"], label="vendor-link", path_or_url=link)
    if vendor.security_review_status != "approved" or (vendor.risk_rating or "").lower() == "high":
        create_vendor_review_task(
            db,
            company_id=current_employee["organization_id"],
            vendor=vendor,
            title=f"Begin vendor review: {vendor.vendor_name}",
            description="Vendor was added or updated and needs a governance review. Collect evidence, review the contract, and confirm risk posture.",
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            due_date=payload.review_date or payload.contract_end_date,
        )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="vendor_created", module="vendor", resource_type="vendor", resource_id=str(record.id), metadata={"risk_rating": payload.risk_rating})
    response_payload = {"record": serialize_compliance_record(record), "vendor_id": vendor.id}
    db.commit()
    return response_payload


@router.get("/vendors")
def list_vendors(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(Vendor, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == Vendor.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "vendors": [
            {
                "record": serialize_compliance_record(record),
                "vendor": {
                    "id": vendor.id,
                    "vendor_name": vendor.vendor_name,
                    "service_category": vendor.service_category,
                    "data_access_level": vendor.data_access_level,
                    "contract_start_date": vendor.contract_start_date.isoformat() if vendor.contract_start_date else None,
                    "contract_end_date": vendor.contract_end_date.isoformat() if vendor.contract_end_date else None,
                    "risk_rating": vendor.risk_rating,
                    "security_review_status": vendor.security_review_status,
                    "last_review_date": vendor.last_review_date.isoformat() if vendor.last_review_date else None,
                    "document_links": _parse_json_list(vendor.document_links),
                },
                "linked_tasks": list_source_tasks(db, company_id=current_employee["organization_id"], source_type="vendor_review", source_id=str(vendor.id)),
            }
            for vendor, record in results
        ]
    }


@router.put("/vendors/{vendor_id}")
def update_vendor(vendor_id: int, payload: VendorUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    vendor, record = _vendor_or_404(db, vendor_id, current_employee["organization_id"])
    if payload.status is not None:
        update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status)
    if payload.risk_rating is not None:
        vendor.risk_rating = payload.risk_rating
    if payload.security_review_status is not None:
        vendor.security_review_status = payload.security_review_status
    if payload.last_review_date is not None:
        vendor.last_review_date = payload.last_review_date
    if payload.notes is not None:
        record.notes = payload.notes
    if payload.document_links is not None:
        vendor.document_links = json.dumps(payload.document_links)
    record.updated_by_employee_id = current_employee["employee_id"]
    db.add(vendor)
    db.add(record)
    if vendor.security_review_status in {"pending", "needs follow-up"} or (vendor.risk_rating or "").lower() == "high":
        create_vendor_review_task(
            db,
            company_id=current_employee["organization_id"],
            vendor=vendor,
            title=f"Review vendor risk: {vendor.vendor_name}",
            description="Vendor review requires follow-up based on current risk, review status, or contract timing.",
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            due_date=payload.last_review_date or record.review_date or vendor.contract_end_date,
        )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="vendor_updated", module="vendor", resource_type="vendor", resource_id=str(vendor.id), metadata={"risk_rating": vendor.risk_rating, "security_review_status": vendor.security_review_status})
    db.commit()
    return {"vendor_id": vendor.id, "record": serialize_compliance_record(record)}


@router.get("/tests/dashboard")
def get_test_dashboard(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    if _demo_workspace_seeding_enabled():
        ensure_test_runs(db, current_employee["organization_id"])
    return get_test_management_dashboard(db, organization_id=current_employee["organization_id"])


@router.get("/tests/inventory")
def list_managed_test_inventory(
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    file_path: str | None = None,
    sort: str = "last_run",
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    return list_managed_tests(
        db,
        organization_id=current_employee["organization_id"],
        category=category,
        status=status,
        search=search,
        file_path=file_path,
        sort=sort,
    )


@router.get("/tests/categories/{category_name}")
def get_test_category_detail(category_name: str, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    payload = list_managed_tests(
        db,
        organization_id=current_employee["organization_id"],
        category=category_name,
        sort="last_run",
    )
    if not payload["tests"]:
        raise HTTPException(status_code=404, detail=error_payload(detail="Test category not found", error_code="not_found"))
    summary = payload["summary"]
    latest_run_timestamp = max((item["last_run_timestamp"] for item in payload["tests"] if item["last_run_timestamp"]), default=None)
    return {
        "category": category_name,
        "summary": {
            "total_tests": summary["total_tests"],
            "passing": summary["passing"],
            "failing": summary["failing"],
            "skipped": summary["skipped"],
            "not_run": summary["not_run"],
            "flaky": summary["flaky"],
            "pass_rate": summary["average_pass_rate"],
            "last_run_timestamp": latest_run_timestamp,
        },
        "tests": payload["tests"],
    }


@router.get("/tests/case-detail")
def get_test_case_detail_query(
    test_id: str = Query(...),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    return get_test_case_detail(test_id, current_employee=current_employee, db=db)


@router.get("/tests/cases/{test_id}")
def get_test_case_detail(test_id: str, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    test_id_value = str(test_id)
    if test_id_value.isdigit():
        case = (
            db.query(ComplianceTestCaseResult, ComplianceTestRun)
            .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
            .filter(ComplianceTestCaseResult.id == int(test_id_value), ComplianceTestRun.organization_id == current_employee["organization_id"])
            .first()
        )
        if not case:
            raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))
        result, run = case
        payload = _serialize_test_case(result, run)
        payload["test_id"] = test_id_value
        payload["last_execution_time"] = payload.pop("last_run_timestamp")
        payload["output"] = payload.pop("output_summary")
        payload["error_message"] = payload.pop("error_details")
        payload["task"] = ensure_failure_task_for_test(
            db,
            organization_id=current_employee["organization_id"],
            test_node_id=payload["test_node_id"],
        ) if payload.get("status") == "failed" else get_failure_task_for_test(
            db,
            organization_id=current_employee["organization_id"],
            test_node_id=payload["test_node_id"],
        )
        payload["linked_tasks"] = list_source_tasks(db, company_id=current_employee["organization_id"], source_type="test_failure", source_id=payload["test_node_id"])
        if payload.get("status") == "failed":
            db.commit()
        return payload

    try:
        payload = get_managed_test_detail(
            db,
            organization_id=current_employee["organization_id"],
            test_id=test_id_value,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))

    detail = dict(payload)
    detail["last_execution_time"] = detail.get("last_run_timestamp")
    detail["output"] = detail.get("latest_execution", {}).get("output")
    detail["error_message"] = detail.get("latest_execution", {}).get("error_message")
    if detail.get("status") == "failed" and detail.get("task") is None:
        detail["task"] = ensure_failure_task_for_test(
            db,
            organization_id=current_employee["organization_id"],
            test_node_id=detail["test_node_id"],
        )
        db.commit()
    detail["linked_tasks"] = list_source_tasks(db, company_id=current_employee["organization_id"], source_type="test_failure", source_id=detail["test_node_id"])
    return detail


@router.get("/tests/case-history")
def get_test_case_history_query(
    test_id: str = Query(...),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    return get_test_case_history(test_id, current_employee=current_employee, db=db)


@router.get("/tests/cases/{test_id}/history")
def get_test_case_history(test_id: str, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    test_id_value = str(test_id)
    if test_id_value.isdigit():
        case = (
            db.query(ComplianceTestCaseResult, ComplianceTestRun)
            .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
            .filter(ComplianceTestCaseResult.id == int(test_id_value), ComplianceTestRun.organization_id == current_employee["organization_id"])
            .first()
        )
        if not case:
            raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))
        result, run = case
        payload = _serialize_test_case(result, run)
        payload["test_node_id"] = build_test_node_id(test_name=result.name, file_path=result.file_name, category=run.category)
        payload["output"] = payload.pop("output_summary")
        payload["error_message"] = payload.pop("error_details")
        return {"history": [payload]}
    try:
        history = get_managed_test_history(
            db,
            organization_id=current_employee["organization_id"],
            test_id=test_id_value,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))
    return {"history": history}


@router.post("/tests/run-all")
def run_full_test_suite(
    background_tasks: BackgroundTasks,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    try:
        run = start_full_suite_run(
            db,
            organization_id=current_employee["organization_id"],
            triggered_by_user_id=current_employee["user_id"],
            triggered_by_employee_id=current_employee["employee_id"],
        )
    except DuplicateTestRunError as exc:
        raise HTTPException(status_code=409, detail=error_payload(detail=str(exc), error_code="conflict"))
    run = _queue_test_run(background_tasks, db, run)
    triggered_by = db.query(Employee).filter(Employee.id == run.triggered_by_employee_id).first() if run.triggered_by_employee_id else None
    return {"run": _serialize_test_run(run, triggered_by)}


@router.post("/tests/run-test")
def run_single_test_query(
    test_id: str = Query(...),
    background_tasks: BackgroundTasks = None,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    return run_single_test(test_id, background_tasks=background_tasks, current_employee=current_employee, db=db)


@router.post("/tests/run-test/{test_id:path}")
def run_single_test(
    test_id: str,
    background_tasks: BackgroundTasks,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    try:
        run = start_single_test_run(
            db,
            organization_id=current_employee["organization_id"],
            triggered_by_user_id=current_employee["user_id"],
            triggered_by_employee_id=current_employee["employee_id"],
            test_id=test_id,
        )
    except UnsupportedTestExecutionError as exc:
        raise HTTPException(status_code=409, detail=error_payload(detail=str(exc), error_code="conflict"))
    except DuplicateTestRunError as exc:
        raise HTTPException(status_code=409, detail=error_payload(detail=str(exc), error_code="conflict"))
    run = _queue_test_run(background_tasks, db, run)
    triggered_by = db.query(Employee).filter(Employee.id == run.triggered_by_employee_id).first() if run.triggered_by_employee_id else None
    return {"run": _serialize_test_run(run, triggered_by)}


@router.post("/tests/categories/{category_name}/run")
def run_test_category(
    category_name: str,
    background_tasks: BackgroundTasks,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    try:
        run = start_category_run(
            db,
            organization_id=current_employee["organization_id"],
            triggered_by_user_id=current_employee["user_id"],
            triggered_by_employee_id=current_employee["employee_id"],
            category_name=category_name,
        )
    except UnsupportedTestExecutionError as exc:
        raise HTTPException(status_code=409, detail=error_payload(detail=str(exc), error_code="conflict"))
    except DuplicateTestRunError as exc:
        raise HTTPException(status_code=409, detail=error_payload(detail=str(exc), error_code="conflict"))
    run = _queue_test_run(background_tasks, db, run)
    triggered_by = db.query(Employee).filter(Employee.id == run.triggered_by_employee_id).first() if run.triggered_by_employee_id else None
    return {"run": _serialize_test_run(run, triggered_by)}


@router.post("/tests/runs")
def create_test_run(payload: TestRunCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    run = create_tracked_test_run(
        db,
        organization_id=current_employee["organization_id"],
        category=payload.category,
        suite_name=payload.suite_name,
        status=payload.status,
        dataset_name=payload.dataset_name,
        coverage_percent=payload.coverage_percent,
        report_link=payload.report_link,
        triggered_by_user_id=current_employee["user_id"],
        triggered_by_employee_id=current_employee["employee_id"],
    )
    db.commit()
    return _serialize_test_run(run)


@router.post("/tests/runs/{run_id}/results")
def create_test_result(
    run_id: int,
    payload: TestResultCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    run = db.query(ComplianceTestRun).filter(
        ComplianceTestRun.id == run_id,
        ComplianceTestRun.organization_id == current_employee["organization_id"],
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail=error_payload(detail="Test run not found", error_code="not_found"))

    derived_file_path, derived_test_name = split_test_node_id(payload.test_node_id) if payload.test_node_id else (None, payload.test_name)
    result = record_test_result(
        db,
        test_run_id=run.id,
        test_name=derived_test_name,
        test_node_id=payload.test_node_id,
        dataset_name=payload.dataset_name or run.dataset_name,
        expected_result=payload.expected_result,
        actual_result=payload.actual_result,
        status=payload.status,
        confidence_score=float(payload.confidence_score) if payload.confidence_score is not None else None,
        file_name=payload.file_path or derived_file_path or payload.file_name,
        description=payload.description,
        duration_ms=payload.duration_ms,
        output=payload.output,
        error_message=payload.error_message,
        created_by_employee_id=current_employee["employee_id"],
        created_by_user_id=current_employee["user_id"],
    )
    response_payload = _serialize_test_case(result, run)
    db.commit()
    return response_payload


@router.get("/tests/case-task")
def get_test_case_task_query(
    test_id: str = Query(...),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    return get_test_case_task(test_id, current_employee=current_employee, db=db)


@router.get("/tests/cases/{test_id}/task")
def get_test_case_task(test_id: str, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    test_id_value = str(test_id)
    if test_id_value.isdigit():
        case = (
            db.query(ComplianceTestCaseResult, ComplianceTestRun)
            .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
            .filter(ComplianceTestCaseResult.id == int(test_id_value), ComplianceTestRun.organization_id == current_employee["organization_id"])
            .first()
        )
        if not case:
            raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))
        result, run = case
        test_node_id = build_test_node_id(test_name=result.name, file_path=result.file_name, category=run.category)
    else:
        try:
            detail = get_managed_test_detail(db, organization_id=current_employee["organization_id"], test_id=test_id_value)
        except ValueError:
            raise HTTPException(status_code=404, detail=error_payload(detail="Test case not found", error_code="not_found"))
        test_node_id = detail["test_node_id"]

    task = get_failure_task_for_test(db, organization_id=current_employee["organization_id"], test_node_id=test_node_id)
    return {"task": task}


@router.post("/tests/case-task")
def create_or_update_test_case_task_query(
    test_id: str = Query(...),
    payload: TestFailureTaskCreateRequest | None = None,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    effective_payload = payload or TestFailureTaskCreateRequest()
    return create_or_update_test_case_task(test_id, effective_payload, current_employee=current_employee, db=db)


@router.post("/tests/cases/{test_id}/task")
def create_or_update_test_case_task(
    test_id: str,
    payload: TestFailureTaskCreateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    detail = get_test_case_detail(test_id, current_employee=current_employee, db=db)
    task = detail.get("task")
    if task is None and detail.get("status") == "failed":
        task = ensure_failure_task_for_test(
            db,
            organization_id=current_employee["organization_id"],
            test_node_id=detail["test_node_id"],
        )
    if task is None:
        raise HTTPException(status_code=409, detail=error_payload(detail="Task can only be created for failing tests", error_code="conflict"))
    updated = update_failure_task(
        db,
        organization_id=current_employee["organization_id"],
        task_id=task["id"],
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
        priority=payload.priority,
        assignee_employee_id=payload.assignee_employee_id,
    )
    db.commit()
    return {"task": updated}


@router.patch("/tests/tasks/{task_id}")
def patch_test_failure_task(
    task_id: int,
    payload: TestFailureTaskUpdateRequest,
    current_employee: dict = Depends(require_security_or_compliance_admin),
    db: Session = Depends(get_db),
):
    try:
        updated = update_failure_task(
            db,
            organization_id=current_employee["organization_id"],
            task_id=task_id,
            actor_employee_id=current_employee["employee_id"],
            actor_user_id=current_employee["user_id"],
            status=payload.status,
            priority=payload.priority,
            assignee_employee_id=payload.assignee_employee_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=error_payload(detail="Failure task not found", error_code="not_found"))
    db.commit()
    return {"task": updated}


@router.get("/tests/results")
def list_test_results(
    limit: int = Query(default=50, ge=1, le=200),
    dataset_name: str | None = Query(default=None),
    test_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    rows = query_test_results(
        db,
        organization_id=current_employee["organization_id"],
        limit=limit,
        dataset_name=dataset_name,
        test_name=test_name,
        status=status,
    )
    return {
        "results": [_serialize_test_case(result, run) for result, run in rows]
    }


@router.get("/tests/runs")
def list_test_runs(
    limit: int = Query(default=25, ge=1, le=100),
    dataset_name: str | None = Query(default=None),
    suite_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    run_type: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    dataset_name = _normalize_optional_query_value(dataset_name)
    suite_name = _normalize_optional_query_value(suite_name)
    status = _normalize_optional_query_value(status)
    run_type = _normalize_optional_query_value(run_type)
    active_only = _normalize_optional_query_value(active_only)
    query = db.query(ComplianceTestRun).filter(ComplianceTestRun.organization_id == current_employee["organization_id"])
    if dataset_name:
        query = query.filter(ComplianceTestRun.dataset_name == dataset_name)
    if suite_name:
        query = query.filter(ComplianceTestRun.suite_name == suite_name)
    if status:
        query = query.filter(ComplianceTestRun.status == status)
    if run_type:
        query = query.filter(ComplianceTestRun.run_type == run_type)
    if active_only is True:
        query = query.filter(ComplianceTestRun.status.in_(tuple(ACTIVE_RUN_STATUSES)))
    elif active_only is False:
        query = query.filter(~ComplianceTestRun.status.in_(tuple(ACTIVE_RUN_STATUSES)))
    runs = query.order_by(ComplianceTestRun.run_at.desc(), ComplianceTestRun.id.desc()).limit(limit).all()
    employee_ids = {run.triggered_by_employee_id for run in runs if run.triggered_by_employee_id is not None}
    employees = {
        employee.id: employee
        for employee in db.query(Employee).filter(Employee.company_id == current_employee["organization_id"], Employee.id.in_(employee_ids)).all()
    } if employee_ids else {}
    return {"runs": [_serialize_test_run(run, employees.get(run.triggered_by_employee_id)) for run in runs]}


@router.get("/tests/runs/{run_id}")
def get_test_run_detail(run_id: int, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    run = _test_run_or_404(db, run_id, current_employee["organization_id"])
    triggered_by = db.query(Employee).filter(Employee.id == run.triggered_by_employee_id).first() if run.triggered_by_employee_id else None
    results = (
        db.query(ComplianceTestCaseResult)
        .filter(ComplianceTestCaseResult.test_run_id == run.id)
        .order_by(ComplianceTestCaseResult.last_run_at.desc(), ComplianceTestCaseResult.id.desc())
        .all()
    )
    serialized_results = [
        _serialize_test_run_result(
            db,
            organization_id=current_employee["organization_id"],
            case=result,
            run=run,
        )
        for result in results
    ]
    linked_tasks: dict[int, dict] = {}
    for item in serialized_results:
        for task in item.get("linked_tasks", []):
            linked_tasks[int(task["id"])] = task
    return {
        "run": _serialize_test_run(run, triggered_by, include_logs=True),
        "results": serialized_results,
        "linked_tasks": list(linked_tasks.values()),
    }


@router.get("/tests/metrics")
def get_test_metrics(
    dataset_name: str | None = Query(default=None),
    current_employee: dict = Depends(require_compliance_workspace_access),
    db: Session = Depends(get_db),
):
    metrics = compute_test_metrics(
        db,
        organization_id=current_employee["organization_id"],
        dataset_name=dataset_name,
    )
    metrics["dataset_name"] = dataset_name
    return metrics


@router.post("/access-reviews")
def create_access_review(payload: AccessReviewCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    reviewed_employee = db.query(Employee).filter(Employee.id == payload.reviewed_employee_id, Employee.company_id == current_employee["organization_id"]).first()
    if not reviewed_employee:
        raise HTTPException(status_code=404, detail=error_payload(detail="Reviewed employee not found", error_code="not_found"))
    record = create_compliance_record(db, organization_id=current_employee["organization_id"], module="access_review", title=payload.title, employee_id=current_employee["employee_id"], status=payload.status, due_date=payload.due_date, review_date=payload.review_date, notes=payload.notes, owner_employee_id=payload.owner_employee_id)
    review = AccessReview(
        compliance_record_id=record.id,
        reviewer_employee_id=current_employee["employee_id"],
        reviewed_employee_id=payload.reviewed_employee_id,
        permissions_snapshot=json.dumps(payload.permissions_snapshot),
        last_access_review_date=datetime.now(timezone.utc),
    )
    db.add(review)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="access_review_created", module="access_review", resource_type="access_review", resource_id=str(record.id), metadata={"reviewed_employee_id": payload.reviewed_employee_id})
    db.commit()
    db.refresh(review)
    return {"review_id": review.id, "record": serialize_compliance_record(record)}


@router.post("/access-reviews/{review_id}/decision")
def decide_access_review(review_id: int, payload: AccessReviewDecisionRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    review, record = _access_review_or_404(db, review_id, current_employee["organization_id"])
    review.decision = payload.decision
    review.reviewed_at = datetime.now(timezone.utc)
    update_record_status(db, record=record, employee_id=current_employee["employee_id"], status="completed", details=f"Access review {payload.decision}")
    add_approval(db, record_id=record.id, approver_employee_id=current_employee["employee_id"], status=payload.decision, notes=payload.notes)
    db.add(review)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="access_review_decided", module="access_review", resource_type="access_review", resource_id=str(review.id), metadata={"decision": payload.decision})
    db.commit()
    return {"review_id": review.id, "decision": review.decision}


@router.get("/access-reviews")
def list_access_reviews(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(AccessReview, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == AccessReview.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "access_reviews": [
            {
                "record": serialize_compliance_record(record),
                "review": {
                    "id": review.id,
                    "reviewer_employee_id": review.reviewer_employee_id,
                    "reviewed_employee_id": review.reviewed_employee_id,
                    "decision": review.decision,
                    "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
                    "permissions_snapshot": _parse_json_dict(review.permissions_snapshot),
                    "last_access_review_date": review.last_access_review_date.isoformat() if review.last_access_review_date else None,
                },
            }
            for review, record in results
        ]
    }


@router.get("/training/modules")
def list_training_modules(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    modules = db.query(TrainingModule).filter(TrainingModule.organization_id == current_employee["organization_id"]).order_by(TrainingModule.title.asc()).all()
    return {"modules": [{"id": item.id, "title": item.title, "description": item.description, "category": item.category, "document_link": item.document_link} for item in modules]}


@router.post("/training/assignments")
def assign_training(payload: TrainingAssignmentCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == payload.employee_id, Employee.company_id == current_employee["organization_id"]).first()
    training_module = db.query(TrainingModule).filter(TrainingModule.id == payload.training_module_id, TrainingModule.organization_id == current_employee["organization_id"]).first()
    if not employee or not training_module:
        raise HTTPException(status_code=404, detail=error_payload(detail="Training target not found", error_code="not_found"))
    record = create_compliance_record(db, organization_id=current_employee["organization_id"], module="training", title=payload.title or training_module.title, employee_id=current_employee["employee_id"], status=payload.status, due_date=payload.due_date, review_date=payload.review_date, notes=payload.notes, owner_employee_id=payload.owner_employee_id or payload.employee_id)
    assignment = TrainingAssignment(compliance_record_id=record.id, employee_id=payload.employee_id, training_module_id=payload.training_module_id, due_date=payload.due_date)
    db.add(assignment)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="training_assigned", module="training", resource_type="training_assignment", resource_id=str(record.id), metadata={"employee_id": payload.employee_id, "training_module_id": payload.training_module_id})
    db.commit()
    db.refresh(assignment)
    return {"assignment_id": assignment.id}


@router.post("/training/modules")
def create_training_module(payload: TrainingModuleCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    training_module = TrainingModule(
        organization_id=current_employee["organization_id"],
        title=payload.title,
        description=payload.description,
        category=payload.category,
        document_link=payload.document_link,
    )
    db.add(training_module)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="training_module_created", module="training", resource_type="training_module", resource_id=str(training_module.id or "pending"))
    db.commit()
    db.refresh(training_module)
    return {"module": {"id": training_module.id, "title": training_module.title, "category": training_module.category}}


@router.post("/training/assignments/{assignment_id}/complete")
def complete_training(assignment_id: int, payload: TrainingCompletionRequest, current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    assignment, record = _training_assignment_or_404(db, assignment_id, current_employee["organization_id"])
    if assignment.employee_id != current_employee["employee_id"] and current_employee["employee_role"] not in {"security_admin", "compliance_admin"}:
        raise HTTPException(status_code=403, detail=error_payload(detail="Not authorized to complete this training record", error_code="forbidden"))
    assignment.completion_status = payload.completion_status
    assignment.completed_at = datetime.now(timezone.utc)
    assignment.quiz_score = payload.quiz_score
    update_record_status(db, record=record, employee_id=current_employee["employee_id"], status="completed", details="Training completed")
    db.add(assignment)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="training_completed", module="training", resource_type="training_assignment", resource_id=str(assignment.id), metadata={"quiz_score": str(payload.quiz_score) if payload.quiz_score is not None else None})
    db.commit()
    return {"assignment_id": assignment.id, "completion_status": assignment.completion_status}


@router.get("/training/assignments")
def list_training_assignments(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(TrainingAssignment, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == TrainingAssignment.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "assignments": [
            {
                "record": serialize_compliance_record(record),
                "assignment": {
                    "id": assignment.id,
                    "employee_id": assignment.employee_id,
                    "training_module_id": assignment.training_module_id,
                    "completion_status": assignment.completion_status,
                    "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "quiz_score": float(assignment.quiz_score) if assignment.quiz_score is not None else None,
                },
            }
            for assignment, record in results
        ]
    }


@router.post("/incidents")
def create_incident(payload: IncidentCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    record = create_compliance_record(db, organization_id=current_employee["organization_id"], module="incident", title=payload.title, employee_id=current_employee["employee_id"], status=payload.status, due_date=payload.due_date, review_date=payload.review_date, notes=payload.notes, owner_employee_id=payload.owner_employee_id or payload.assigned_to_employee_id)
    incident = GRCIncident(
        compliance_record_id=record.id,
        severity=payload.severity,
        description=payload.description,
        detected_by_employee_id=current_employee["employee_id"],
        detected_at=payload.detected_at,
        assigned_to_employee_id=payload.assigned_to_employee_id,
    )
    db.add(incident)
    db.flush()
    create_incident_remediation_task(
        db,
        company_id=current_employee["organization_id"],
        incident=incident,
        incident_title=record.title,
        incident_status=record.status,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
    )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="incident_created", module="incident", resource_type="grc_incident", resource_id=str(record.id), metadata={"severity": payload.severity})
    incident_id = incident.id
    db.commit()
    return {"incident_id": incident_id}


@router.put("/incidents/{incident_id}")
def update_incident(incident_id: int, payload: IncidentUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    incident, record = _incident_or_404(db, incident_id, current_employee["organization_id"])
    if record.closed_at is not None:
        raise HTTPException(status_code=409, detail=error_payload(detail="Closed incidents are immutable", error_code="conflict"))
    if payload.assigned_to_employee_id is not None:
        incident.assigned_to_employee_id = payload.assigned_to_employee_id
    if payload.resolution_notes is not None:
        incident.resolution_notes = payload.resolution_notes
    if payload.root_cause is not None:
        incident.root_cause = payload.root_cause
    if payload.lessons_learned is not None:
        incident.lessons_learned = payload.lessons_learned
    if payload.status is not None:
        update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status, details=f"Incident status -> {payload.status}")
        if payload.status == "closed":
            incident.closed_at = datetime.now(timezone.utc)
    db.add(incident)
    create_incident_remediation_task(
        db,
        company_id=current_employee["organization_id"],
        incident=incident,
        incident_title=record.title,
        incident_status=record.status,
        actor_employee_id=current_employee["employee_id"],
        actor_user_id=current_employee["user_id"],
    )
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="incident_updated", module="incident", resource_type="grc_incident", resource_id=str(incident.id), metadata={"status": record.status})
    db.commit()
    return {"incident_id": incident.id, "status": record.status}


@router.get("/incidents")
def list_incidents(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(GRCIncident, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == GRCIncident.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "incidents": [
            {
                "record": serialize_compliance_record(record),
                "incident": {
                    "id": incident.id,
                    "severity": incident.severity,
                    "description": incident.description,
                    "detected_by_employee_id": incident.detected_by_employee_id,
                    "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                    "assigned_to_employee_id": incident.assigned_to_employee_id,
                    "resolution_notes": incident.resolution_notes,
                    "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
                    "root_cause": incident.root_cause,
                    "lessons_learned": incident.lessons_learned,
                },
                "linked_tasks": list_source_tasks(db, company_id=current_employee["organization_id"], source_type="incident", source_id=str(incident.id)),
            }
            for incident, record in results
        ]
    }


@router.post("/hr-controls")
def create_hr_control(payload: HRControlCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    record = create_compliance_record(db, organization_id=current_employee["organization_id"], module="hr_control", title=payload.title, employee_id=current_employee["employee_id"], status=payload.status, due_date=payload.due_date, review_date=payload.review_date, notes=payload.notes, owner_employee_id=payload.owner_employee_id or payload.employee_id)
    control = HRControl(compliance_record_id=record.id, employee_id=payload.employee_id, control_type=payload.control_type, status=payload.status)
    db.add(control)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="hr_control_created", module="hr_control", resource_type="hr_control", resource_id=str(record.id), metadata={"control_type": payload.control_type})
    db.commit()
    db.refresh(control)
    return {"control_id": control.id}


@router.put("/hr-controls/{control_id}")
def update_hr_control(control_id: int, payload: HRControlUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    control, record = _hr_control_or_404(db, control_id, current_employee["organization_id"])
    control.status = payload.status
    control.completed_at = payload.completed_at or (datetime.now(timezone.utc) if payload.status == "completed" else None)
    control.reviewed_by_employee_id = payload.reviewed_by_employee_id or current_employee["employee_id"]
    update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status, details=f"HR control -> {payload.status}")
    db.add(control)
    db.commit()
    return {"control_id": control.id, "status": control.status}


@router.get("/hr-controls")
def list_hr_controls(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(HRControl, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == HRControl.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "controls": [
            {
                "record": serialize_compliance_record(record),
                "control": {
                    "id": control.id,
                    "employee_id": control.employee_id,
                    "control_type": control.control_type,
                    "status": control.status,
                    "completed_at": control.completed_at.isoformat() if control.completed_at else None,
                    "reviewed_by_employee_id": control.reviewed_by_employee_id,
                },
            }
            for control, record in results
        ]
    }


@router.post("/risks")
def create_risk(payload: RiskCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    score = payload.likelihood * payload.impact
    record = create_compliance_record(db, organization_id=current_employee["organization_id"], module="risk", title=payload.title or payload.risk_title, employee_id=current_employee["employee_id"], status=payload.status, due_date=payload.due_date, review_date=payload.review_date, notes=payload.notes, owner_employee_id=payload.owner_employee_id)
    risk = RiskRegisterItem(
        compliance_record_id=record.id,
        risk_title=payload.risk_title,
        description=payload.description,
        risk_category=payload.risk_category,
        likelihood=payload.likelihood,
        impact=payload.impact,
        risk_score=score,
        mitigation_plan=payload.mitigation_plan,
        owner_employee_id=payload.owner_employee_id,
        review_date=payload.review_date,
    )
    db.add(risk)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="risk_created", module="risk", resource_type="risk_register_item", resource_id=str(record.id), metadata={"risk_score": score})
    db.commit()
    db.refresh(risk)
    return {"risk_id": risk.id, "risk_score": risk.risk_score}


@router.put("/risks/{risk_id}")
def update_risk(risk_id: int, payload: RiskUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    risk, record = _risk_or_404(db, risk_id, current_employee["organization_id"])
    if payload.status is not None:
        update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status)
    if payload.likelihood is not None:
        risk.likelihood = payload.likelihood
    if payload.impact is not None:
        risk.impact = payload.impact
    if payload.mitigation_plan is not None:
        risk.mitigation_plan = payload.mitigation_plan
    if payload.review_date is not None:
        risk.review_date = payload.review_date
    risk.risk_score = risk.likelihood * risk.impact
    db.add(risk)
    db.commit()
    return {"risk_id": risk.id, "risk_score": risk.risk_score}


@router.get("/risks")
def list_risks(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(RiskRegisterItem, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == RiskRegisterItem.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(RiskRegisterItem.risk_score.desc()).all()
    return {
        "risks": [
            {
                "record": serialize_compliance_record(record),
                "risk": {
                    "id": risk.id,
                    "risk_title": risk.risk_title,
                    "description": risk.description,
                    "risk_category": risk.risk_category,
                    "likelihood": risk.likelihood,
                    "impact": risk.impact,
                    "risk_score": risk.risk_score,
                    "mitigation_plan": risk.mitigation_plan,
                    "owner_employee_id": risk.owner_employee_id,
                    "review_date": risk.review_date.isoformat() if risk.review_date else None,
                },
            }
            for risk, record in results
        ]
    }


@router.post("/code-reviews")
def create_code_review(payload: CodeReviewCreateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    record = create_compliance_record(
        db,
        organization_id=current_employee["organization_id"],
        module="code_review",
        title=payload.title,
        employee_id=current_employee["employee_id"],
        status=payload.status or "Draft",
        due_date=payload.due_date,
        review_date=payload.review_date,
        notes=payload.notes,
        owner_employee_id=payload.owner_employee_id or payload.assigned_reviewer_employee_id,
    )
    review = CodeReview(
        compliance_record_id=record.id,
        summary=payload.summary,
        review_type=payload.review_type,
        risk_level=payload.risk_level,
        created_by_employee_id=current_employee["employee_id"],
        assigned_reviewer_employee_id=payload.assigned_reviewer_employee_id,
        target_release=payload.target_release,
        prompt_text=payload.prompt_text,
        design_notes=payload.design_notes,
        code_notes=payload.code_notes,
        files_impacted=json.dumps(payload.files_impacted),
        testing_notes=payload.testing_notes,
        security_review_notes=payload.security_review_notes,
        privacy_review_notes=payload.privacy_review_notes,
        reviewer_comments=payload.reviewer_comments,
    )
    db.add(review)
    add_activity(db, compliance_record_id=record.id, employee_id=current_employee["employee_id"], action="code_review_created", details=payload.review_type)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="code_review_created", module="code_review", resource_type="code_review", resource_id=str(record.id), metadata={"risk_level": payload.risk_level, "target_release": payload.target_release})
    db.commit()
    db.refresh(review)
    return {"review_id": review.id, "record": serialize_compliance_record(record)}


@router.get("/code-reviews")
def list_code_reviews(current_employee: dict = Depends(require_compliance_workspace_access), db: Session = Depends(get_db)):
    results = db.query(CodeReview, ComplianceRecord).join(ComplianceRecord, ComplianceRecord.id == CodeReview.compliance_record_id).filter(ComplianceRecord.organization_id == current_employee["organization_id"]).order_by(ComplianceRecord.updated_at.desc()).all()
    return {
        "code_reviews": [
            {
                "record": serialize_compliance_record(record),
                "review": {
                    "id": review.id,
                    "summary": review.summary,
                    "review_type": review.review_type,
                    "risk_level": review.risk_level,
                    "created_by_employee_id": review.created_by_employee_id,
                    "assigned_reviewer_employee_id": review.assigned_reviewer_employee_id,
                    "target_release": review.target_release,
                    "prompt_text": review.prompt_text,
                    "design_notes": review.design_notes,
                    "code_notes": review.code_notes,
                    "files_impacted": _parse_json_list(review.files_impacted),
                    "testing_notes": review.testing_notes,
                    "security_review_notes": review.security_review_notes,
                    "privacy_review_notes": review.privacy_review_notes,
                    "reviewer_decision": review.reviewer_decision,
                    "reviewer_comments": review.reviewer_comments,
                    "approved_at": review.approved_at.isoformat() if review.approved_at else None,
                    "archived_at": review.archived_at.isoformat() if review.archived_at else None,
                },
            }
            for review, record in results
        ]
    }


@router.put("/code-reviews/{review_id}")
def update_code_review(review_id: int, payload: CodeReviewUpdateRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    review, record = _code_review_or_404(db, review_id, current_employee["organization_id"])
    if record.closed_at is not None and record.status in {"Ready for Production", "Archived"}:
        raise HTTPException(status_code=409, detail=error_payload(detail="Finalized code reviews are immutable", error_code="conflict"))
    if payload.title is not None:
        record.title = payload.title
    if payload.status is not None:
        update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=payload.status, details=f"Code review status -> {payload.status}")
        if payload.status == "Archived":
            review.archived_at = datetime.now(timezone.utc)
    for field in ("summary", "review_type", "risk_level", "assigned_reviewer_employee_id", "target_release", "prompt_text", "design_notes", "code_notes", "testing_notes", "security_review_notes", "privacy_review_notes", "reviewer_comments"):
        value = getattr(payload, field)
        if value is not None:
            setattr(review, field, value)
    if payload.files_impacted is not None:
        review.files_impacted = json.dumps(payload.files_impacted)
    record.updated_by_employee_id = current_employee["employee_id"]
    db.add(record)
    db.add(review)
    add_activity(db, compliance_record_id=record.id, employee_id=current_employee["employee_id"], action="code_review_updated", details=payload.status or "fields_updated")
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="code_review_updated", module="code_review", resource_type="code_review", resource_id=str(review.id), metadata={"status": record.status, "assigned_reviewer_employee_id": review.assigned_reviewer_employee_id})
    db.commit()
    return {"review_id": review.id, "record": serialize_compliance_record(record)}


@router.post("/code-reviews/{review_id}/decision")
def decide_code_review(review_id: int, payload: CodeReviewDecisionRequest, current_employee: dict = Depends(require_security_or_compliance_admin), db: Session = Depends(get_db)):
    review, record = _code_review_or_404(db, review_id, current_employee["organization_id"])
    decision_to_status = {
        "Approve": "Approved",
        "Request Changes": "Changes Requested",
        "Block": "Blocked",
        "Mark Ready for Production": "Ready for Production",
    }
    next_status = decision_to_status.get(payload.decision, payload.decision)
    review.reviewer_decision = payload.decision
    review.reviewer_comments = payload.reviewer_comments
    review.assigned_reviewer_employee_id = review.assigned_reviewer_employee_id or current_employee["employee_id"]
    if next_status == "Approved":
        review.approved_at = datetime.now(timezone.utc)
    if next_status == "Archived":
        review.archived_at = datetime.now(timezone.utc)
    update_record_status(db, record=record, employee_id=current_employee["employee_id"], status=next_status, details=f"Decision: {payload.decision}")
    add_approval(db, record_id=record.id, approver_employee_id=current_employee["employee_id"], status=payload.decision, notes=payload.reviewer_comments)
    db.add(review)
    log_compliance_audit(db, company_id=current_employee["organization_id"], user_id=current_employee["user_id"], employee_id=current_employee["employee_id"], action="code_review_decision_recorded", module="code_review", resource_type="code_review", resource_id=str(review.id), metadata={"decision": payload.decision, "status": next_status})
    db.commit()
    return {"review_id": review.id, "decision": review.reviewer_decision, "status": record.status}




