from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session

from database.models.compliance_record import ComplianceRecord
from database.models.employee import Employee
from database.models.governance_task import GovernanceTask
from database.models.governance_task_activity import GovernanceTaskActivity
from database.models.grc_incident import GRCIncident
from database.models.security_event import SecurityEvent
from database.models.vendor import Vendor
from services.audit_service import record_audit_event

_UNSET = object()

OPEN_TASK_STATUSES = {"todo", "in_progress", "blocked", "ready_for_review"}
CLOSED_TASK_STATUSES = {"done", "canceled"}
TASK_STATUSES = OPEN_TASK_STATUSES | CLOSED_TASK_STATUSES
TASK_PRIORITIES = {"low", "medium", "high", "critical"}
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

SECURITY_EVENT_LABELS = {
    "LOGIN_SUCCESS": "Successful login",
    "LOGIN_FAILURE": "Failed login attempt",
    "REFRESH_TOKEN_MISMATCH": "Refresh token mismatch",
    "SUSPICIOUS_ACTIVITY": "Suspicious activity",
    "FAILED_SCAN": "Failed scan",
    "token_abuse": "Token abuse detected",
    "suspicious_login": "Repeated failed login attempts",
    "refresh_session_revoked_session": "Reuse of revoked session token",
}

SOURCE_URLS = {
    "incidents": "/compliance/incidents",
    "vendors": "/compliance/vendors",
    "employees": "/compliance/employees",
    "testing": "/compliance/testing",
    "security": "/dashboard",
    "audit_log": "/compliance/audit-log",
    "access_reviews": "/compliance/access-reviews",
    "automation": "/compliance/tasks",
    "manual": "/compliance/tasks",
}

def _labelize(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("_", " ").strip().title()


def _coerce_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _task_tables_available(db: Session) -> bool:
    # Use the session's active connection so SQLite in-memory tests do not
    # accidentally introspect through a separate connection and rollback work.
    connection = db.connection()
    inspector = inspect(connection)
    return inspector.has_table("governance_tasks") and inspector.has_table("governance_task_activities")


def task_display_id(task_id: int) -> str:
    return f"TASK-{task_id:03d}"


def _priority_rank(priority: str | None) -> int:
    return PRIORITY_ORDER.get((priority or "").lower(), 0)


def _serialize_person(employee: Employee | None) -> dict[str, Any] | None:
    if employee is None:
        return None
    name = f"{employee.first_name} {employee.last_name}".strip() or employee.email
    return {
        "id": employee.id,
        "name": name,
        "email": employee.email,
        "role": employee.role,
        "status": employee.status,
    }


def _serialize_actor_label(label: str | None, actor_type: str | None) -> dict[str, Any] | None:
    if not label:
        return None
    return {
        "id": None,
        "name": label,
        "email": None,
        "role": None,
        "status": None,
        "type": actor_type,
        "label": label,
    }


def _serialize_assignee(task: GovernanceTask, assignee: Employee | None) -> dict[str, Any] | None:
    payload = _serialize_person(assignee)
    if payload is not None:
        payload["type"] = task.assignee_type or "employee"
        payload["label"] = task.assignee_label or payload["name"]
        return payload
    return _serialize_actor_label(task.assignee_label, task.assignee_type)


def _assignee_display_value(db: Session, company_id: int, employee_id: int | None, assignee_type: str | None, assignee_label: str | None) -> str:
    if employee_id is not None:
        employee = db.query(Employee).filter(Employee.company_id == company_id, Employee.id == employee_id).first()
        if employee is not None:
            return f"{employee.first_name} {employee.last_name}".strip() or employee.email
        return f"Employee #{employee_id}"
    if assignee_label:
        return assignee_label
    if assignee_type:
        return _labelize(assignee_type) or assignee_type
    return "Unassigned"


def _employee_lookup(db: Session, company_id: int, employee_ids: set[int]) -> dict[int, Employee]:
    effective_ids = {employee_id for employee_id in employee_ids if employee_id}
    if not effective_ids:
        return {}
    employees = (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.id.in_(effective_ids))
        .all()
    )
    return {employee.id: employee for employee in employees}


def _format_security_event_label(event_type: str | None) -> str:
    if not event_type:
        return "Security alert"
    return SECURITY_EVENT_LABELS.get(event_type, event_type.replace("_", " ").strip().title())


def _priority_from_severity(severity: str | None) -> str:
    normalized = (severity or "").lower()
    if normalized in {"critical"}:
        return "critical"
    if normalized in {"high", "severe"}:
        return "high"
    if normalized in {"low"}:
        return "low"
    return "medium"


def _task_source_summary(db: Session, task: GovernanceTask) -> dict[str, Any]:
    label = task.source_module.replace("_", " ").title() if task.source_module else "Task"
    summary = None
    source_url = SOURCE_URLS.get(task.source_module or "manual", "/compliance/tasks")

    if task.source_type == "incident" and task.source_id and str(task.source_id).isdigit():
        incident = db.query(GRCIncident).filter(GRCIncident.id == int(task.source_id)).first()
        if incident is not None:
            label = f"Incident INC-{incident.id}"
            summary = incident.description
    elif task.source_type == "vendor_review" and task.source_id and str(task.source_id).isdigit():
        vendor = db.query(Vendor).filter(Vendor.id == int(task.source_id)).first()
        if vendor is not None:
            label = f"Vendor {vendor.vendor_name}"
            summary = f"{vendor.service_category} | {vendor.risk_rating or 'unrated'} risk"
    elif task.source_type == "security_alert" and task.source_id and str(task.source_id).isdigit():
        event = db.query(SecurityEvent).filter(SecurityEvent.id == int(task.source_id)).first()
        if event is not None:
            label = _format_security_event_label(event.event_type)
            summary = event.description
    elif task.source_type == "test_failure":
        label = f"Test {task.source_id}"
        summary = _json_loads(task.metadata_json).get("test_name")
    elif task.source_type in {"employee_followup", "access_review"}:
        label = f"Employee #{task.source_id}"
        summary = _json_loads(task.metadata_json).get("employee_name")
    elif task.source_type == "audit_event":
        label = f"Audit event {task.source_id}"
        summary = _json_loads(task.metadata_json).get("event_type")
    elif task.source_type == "manual":
        label = "Manual task"
    elif task.source_type in {"backlog_improvement", "automated_change", "system_improvement"}:
        metadata = _json_loads(task.metadata_json)
        backlog_id = task.source_id or metadata.get("backlog_item_id")
        label = f"Backlog {backlog_id}" if backlog_id else "Automation backlog item"
        summary = metadata.get("suggested_improvement") or metadata.get("operator_summary")

    return {
        "type": task.source_type,
        "id": task.source_id,
        "module": task.source_module,
        "label": label,
        "summary": summary,
        "url": source_url,
    }


def _serialize_incident_link(db: Session, task: GovernanceTask) -> dict[str, Any] | None:
    if task.incident_id is None:
        return None

    result = (
        db.query(GRCIncident, ComplianceRecord)
        .join(ComplianceRecord, ComplianceRecord.id == GRCIncident.compliance_record_id)
        .filter(
            GRCIncident.id == task.incident_id,
            ComplianceRecord.organization_id == task.company_id,
        )
        .first()
    )
    if result is None:
        return {
            "id": task.incident_id,
            "title": f"Incident #{task.incident_id}",
            "status": None,
            "severity": None,
            "description": None,
            "url": SOURCE_URLS["incidents"],
        }

    incident, record = result
    return {
        "id": incident.id,
        "record_id": record.id,
        "title": record.title,
        "status": record.status,
        "severity": incident.severity,
        "description": incident.description,
        "url": SOURCE_URLS["incidents"],
    }


def _task_workflow_summary(task: GovernanceTask, metadata: dict[str, Any]) -> dict[str, Any]:
    review_state = metadata.get("review_state")
    if not review_state:
        review_state = "pending_review" if task.status == "ready_for_review" else "none"

    return {
        "owner_type": str(
            metadata.get("owner_type")
            or task.assignee_type
            or ("employee" if task.assignee_employee_id else "unassigned")
        ).lower(),
        "execution_mode": str(metadata.get("execution_mode") or "manual").lower(),
        "review_state": str(review_state).lower(),
        "automation_source": metadata.get("automation_source"),
    }


def serialize_task_activity(activity: GovernanceTaskActivity, actor: Employee | None = None) -> dict[str, Any]:
    actor_payload = _serialize_person(actor)
    if actor_payload is not None:
        actor_payload["type"] = activity.actor_type or "employee"
        actor_payload["label"] = activity.actor_label or actor_payload["name"]
    elif activity.actor_label:
        actor_payload = _serialize_actor_label(activity.actor_label, activity.actor_type)
    return {
        "id": activity.id,
        "action": activity.action,
        "from_value": activity.from_value,
        "to_value": activity.to_value,
        "details": activity.details,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
        "actor": actor_payload,
    }


def serialize_task(
    db: Session,
    task: GovernanceTask,
    *,
    assignee: Employee | None = None,
    reporter: Employee | None = None,
    activities: list[GovernanceTaskActivity] | None = None,
    activity_actor_lookup: dict[int, Employee] | None = None,
) -> dict[str, Any]:
    metadata = _json_loads(task.metadata_json)
    due_date = task.due_date.isoformat() if task.due_date else None
    source = _task_source_summary(db, task)
    is_overdue = bool(task.due_date and task.status in OPEN_TASK_STATUSES and _coerce_dt(task.due_date) < _now())
    payload = {
        "id": task.id,
        "task_key": task_display_id(task.id),
        "company_id": task.company_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "source_type": task.source_type,
        "source_id": task.source_id,
        "source_module": task.source_module,
        "source": source,
        "incident_id": task.incident_id,
        "incident": _serialize_incident_link(db, task),
        "assignee_employee_id": task.assignee_employee_id,
        "assignee_type": task.assignee_type,
        "assignee_label": task.assignee_label,
        "reporter_employee_id": task.reporter_employee_id,
        "assignee": _serialize_assignee(task, assignee),
        "reporter": _serialize_person(reporter),
        "due_date": due_date,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "metadata": metadata,
        "workflow": _task_workflow_summary(task, metadata),
        "summary": metadata.get("operator_summary") or metadata.get("summary") or task.description or source.get("summary"),
        "is_overdue": is_overdue,
        "is_open": task.status in OPEN_TASK_STATUSES,
    }
    if activities is not None:
        actor_lookup = activity_actor_lookup or {}
        payload["activity"] = [
            serialize_task_activity(activity, actor_lookup.get(activity.actor_employee_id))
            for activity in activities
        ]
    return payload


def add_task_activity(
    db: Session,
    *,
    task_id: int,
    company_id: int,
    actor_employee_id: int | None,
    actor_type: str | None = None,
    actor_label: str | None = None,
    action: str,
    from_value: str | None = None,
    to_value: str | None = None,
    details: str | None = None,
) -> GovernanceTaskActivity | None:
    if not _task_tables_available(db):
        return None
    activity = GovernanceTaskActivity(
        task_id=task_id,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        actor_type=actor_type,
        actor_label=actor_label,
        action=action,
        from_value=from_value,
        to_value=to_value,
        details=details,
    )
    db.add(activity)
    return activity


def _record_task_audit(
    db: Session,
    *,
    company_id: int,
    user_id: int | None,
    task_id: int,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_audit_event(
        db,
        company_id=company_id,
        user_id=user_id,
        event_type=action,
        event_category="compliance",
        description="Governance task updated.",
        target_type="governance_task",
        target_id=str(task_id),
        event_metadata=metadata,
    )


def _latest_task_for_source(db: Session, *, company_id: int, source_type: str, source_id: str) -> GovernanceTask | None:
    if not _task_tables_available(db):
        return None
    return (
        db.query(GovernanceTask)
        .filter(
            GovernanceTask.company_id == company_id,
            GovernanceTask.source_type == source_type,
            GovernanceTask.source_id == source_id,
        )
        .order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc())
        .first()
    )


def list_tasks(
    db: Session,
    *,
    company_id: int,
    status: str | None = None,
    priority: str | None = None,
    source_module: str | None = None,
    assignee_employee_id: int | None = None,
    only_open: bool | None = None,
    due_before: datetime | None = None,
    search: str | None = None,
    mine_employee_id: int | None = None,
) -> list[dict[str, Any]]:
    if not _task_tables_available(db):
        return []

    query = db.query(GovernanceTask).filter(GovernanceTask.company_id == company_id)
    if status:
        query = query.filter(GovernanceTask.status == status)
    if priority:
        query = query.filter(GovernanceTask.priority == priority)
    if source_module:
        query = query.filter(GovernanceTask.source_module == source_module)
    if assignee_employee_id is not None:
        query = query.filter(GovernanceTask.assignee_employee_id == assignee_employee_id)
    if only_open is True:
        query = query.filter(GovernanceTask.status.in_(tuple(OPEN_TASK_STATUSES)))
    elif only_open is False:
        query = query.filter(GovernanceTask.status.in_(tuple(CLOSED_TASK_STATUSES)))
    if due_before is not None:
        query = query.filter(GovernanceTask.due_date.isnot(None), GovernanceTask.due_date <= _coerce_dt(due_before))
    if mine_employee_id is not None:
        query = query.filter(GovernanceTask.assignee_employee_id == mine_employee_id)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (GovernanceTask.title.ilike(search_term))
            | (GovernanceTask.description.ilike(search_term))
            | (GovernanceTask.source_id.ilike(search_term))
        )
        normalized = search.strip().upper()
        if normalized.startswith("TASK-") and normalized[5:].isdigit():
            query = query.union(
                db.query(GovernanceTask).filter(
                    GovernanceTask.company_id == company_id,
                    GovernanceTask.id == int(normalized[5:]),
                )
            )

    tasks = query.order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc()).all()
    employee_ids = {
        task.assignee_employee_id
        for task in tasks
        if task.assignee_employee_id is not None
    } | {
        task.reporter_employee_id
        for task in tasks
        if task.reporter_employee_id is not None
    }
    employees = _employee_lookup(db, company_id, employee_ids)
    return [
        serialize_task(
            db,
            task,
            assignee=employees.get(task.assignee_employee_id),
            reporter=employees.get(task.reporter_employee_id),
        )
        for task in tasks
    ]


def summarize_tasks(db: Session, *, company_id: int, my_employee_id: int | None = None) -> dict[str, int]:
    if not _task_tables_available(db):
        return {
            "open": 0,
            "overdue": 0,
            "critical": 0,
            "mine": 0,
            "security": 0,
            "testing": 0,
        }

    tasks = db.query(GovernanceTask).filter(GovernanceTask.company_id == company_id).all()
    now = _now()
    return {
        "open": sum(1 for task in tasks if task.status in OPEN_TASK_STATUSES),
        "overdue": sum(1 for task in tasks if task.status in OPEN_TASK_STATUSES and task.due_date and _coerce_dt(task.due_date) < now),
        "critical": sum(1 for task in tasks if task.status in OPEN_TASK_STATUSES and _priority_rank(task.priority) >= _priority_rank("critical")),
        "mine": sum(1 for task in tasks if my_employee_id is not None and task.assignee_employee_id == my_employee_id and task.status in OPEN_TASK_STATUSES),
        "security": sum(1 for task in tasks if task.source_module == "security" and task.status in OPEN_TASK_STATUSES),
        "testing": sum(1 for task in tasks if task.source_module == "testing" and task.status in OPEN_TASK_STATUSES),
    }


def get_task_detail(db: Session, *, company_id: int, task_id: int) -> dict[str, Any] | None:
    if not _task_tables_available(db):
        return None

    task = db.query(GovernanceTask).filter(GovernanceTask.id == task_id, GovernanceTask.company_id == company_id).first()
    if task is None:
        return None

    activities = (
        db.query(GovernanceTaskActivity)
        .filter(
            GovernanceTaskActivity.task_id == task.id,
            GovernanceTaskActivity.company_id == company_id,
        )
        .order_by(GovernanceTaskActivity.created_at.asc(), GovernanceTaskActivity.id.asc())
        .all()
    )
    employee_ids = {task.assignee_employee_id, task.reporter_employee_id, *[activity.actor_employee_id for activity in activities]}
    employees = _employee_lookup(db, company_id, employee_ids)
    return serialize_task(
        db,
        task,
        assignee=employees.get(task.assignee_employee_id),
        reporter=employees.get(task.reporter_employee_id),
        activities=activities,
        activity_actor_lookup=employees,
    )


def create_task(
    db: Session,
    *,
    company_id: int,
    title: str,
    description: str | None,
    status: str = "todo",
    priority: str = "medium",
    source_type: str = "manual",
    source_id: str | None = None,
    source_module: str = "manual",
    incident_id: int | None = None,
    assignee_employee_id: int | None = None,
    assignee_type: str | None = None,
    assignee_label: str | None = None,
    reporter_employee_id: int | None = None,
    due_date: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    actor_user_id: int | None = None,
    activity_actor_type: str | None = None,
    activity_actor_label: str | None = None,
) -> GovernanceTask | None:
    if not _task_tables_available(db):
        return None

    task = GovernanceTask(
        company_id=company_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        source_type=source_type,
        source_id=str(source_id) if source_id is not None else None,
        source_module=source_module,
        incident_id=incident_id,
        assignee_employee_id=assignee_employee_id,
        assignee_type=assignee_type or ("employee" if assignee_employee_id is not None else None),
        assignee_label=None if assignee_employee_id is not None else assignee_label,
        reporter_employee_id=reporter_employee_id,
        due_date=_coerce_dt(due_date),
        metadata_json=_json_dumps(metadata),
        resolved_at=_now() if status in CLOSED_TASK_STATUSES else None,
    )
    db.add(task)
    db.flush()
    add_task_activity(
        db,
        task_id=task.id,
        company_id=company_id,
        actor_employee_id=reporter_employee_id,
        actor_type=activity_actor_type,
        actor_label=activity_actor_label,
        action="created",
        to_value=status,
        details=description,
    )
    _record_task_audit(
        db,
        company_id=company_id,
        user_id=actor_user_id,
        task_id=task.id,
        action="governance_task_created",
        metadata={"source_type": source_type, "source_id": source_id, "priority": priority},
    )
    return task


def update_task(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    title: str | None | object = _UNSET,
    description: str | None | object = _UNSET,
    status: str | None | object = _UNSET,
    priority: str | None | object = _UNSET,
    assignee_employee_id: int | None | object = _UNSET,
    assignee_type: str | None | object = _UNSET,
    assignee_label: str | None | object = _UNSET,
    due_date: datetime | None | object = _UNSET,
    incident_id: int | None | object = _UNSET,
    source_type: str | None | object = _UNSET,
    source_id: str | None | object = _UNSET,
    source_module: str | None | object = _UNSET,
    metadata: dict[str, Any] | None | object = _UNSET,
    activity_actor_type: str | None = None,
    activity_actor_label: str | None = None,
) -> dict[str, Any] | None:
    if not _task_tables_available(db):
        return None

    task = db.query(GovernanceTask).filter(GovernanceTask.company_id == company_id, GovernanceTask.id == task_id).first()
    if task is None:
        return None

    if title is not _UNSET and title is not None and title != task.title:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="title_changed",
            from_value=task.title,
            to_value=title,
        )
        task.title = title

    if description is not _UNSET and description != task.description:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="description_changed",
        )
        task.description = description

    if status is not _UNSET and status is not None and status != task.status:
        previous_status = task.status
        task.status = status
        if status in CLOSED_TASK_STATUSES:
            task.resolved_at = _now()
        elif previous_status in CLOSED_TASK_STATUSES and status in OPEN_TASK_STATUSES:
            task.resolved_at = None
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="status_changed",
            from_value=previous_status,
            to_value=status,
        )

    if priority is not _UNSET and priority is not None and priority != task.priority:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="priority_changed",
            from_value=task.priority,
            to_value=priority,
        )
        task.priority = priority

    assignee_changed = any(
        value is not _UNSET
        for value in (assignee_employee_id, assignee_type, assignee_label)
    )
    if assignee_changed:
        next_assignee_employee_id = task.assignee_employee_id if assignee_employee_id is _UNSET else assignee_employee_id
        next_assignee_type = task.assignee_type if assignee_type is _UNSET else assignee_type
        next_assignee_label = task.assignee_label if assignee_label is _UNSET else assignee_label

        if assignee_employee_id is not _UNSET:
            if assignee_employee_id is not None:
                if assignee_type is _UNSET:
                    next_assignee_type = "employee"
                if assignee_label is _UNSET:
                    next_assignee_label = None
            elif assignee_type is _UNSET and assignee_label is _UNSET:
                next_assignee_type = None
                next_assignee_label = None

        previous_assignee_display = _assignee_display_value(
            db,
            company_id,
            task.assignee_employee_id,
            task.assignee_type,
            task.assignee_label,
        )
        next_assignee_display = _assignee_display_value(
            db,
            company_id,
            next_assignee_employee_id,
            next_assignee_type,
            next_assignee_label,
        )
        if (
            next_assignee_employee_id != task.assignee_employee_id
            or next_assignee_type != task.assignee_type
            or next_assignee_label != task.assignee_label
        ):
            add_task_activity(
                db,
                task_id=task.id,
                company_id=company_id,
                actor_employee_id=actor_employee_id,
                actor_type=activity_actor_type,
                actor_label=activity_actor_label,
                action="assignee_changed",
                from_value=previous_assignee_display,
                to_value=next_assignee_display,
                details=f"{previous_assignee_display} -> {next_assignee_display}",
            )
            task.assignee_employee_id = next_assignee_employee_id
            task.assignee_type = next_assignee_type
            task.assignee_label = next_assignee_label

    if due_date is not _UNSET:
        coerced_due_date = _coerce_dt(due_date) if due_date is not None else None
        if coerced_due_date != task.due_date:
            add_task_activity(
                db,
                task_id=task.id,
                company_id=company_id,
                actor_employee_id=actor_employee_id,
                actor_type=activity_actor_type,
                actor_label=activity_actor_label,
                action="due_date_changed",
                from_value=task.due_date.isoformat() if task.due_date else None,
                to_value=coerced_due_date.isoformat() if coerced_due_date else None,
            )
            task.due_date = coerced_due_date

    if incident_id is not _UNSET and incident_id != task.incident_id:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="incident_linked",
            from_value=str(task.incident_id) if task.incident_id is not None else None,
            to_value=str(incident_id) if incident_id is not None else None,
        )
        task.incident_id = incident_id

    previous_source_snapshot = f"{task.source_type}:{task.source_id or ''}:{task.source_module}"
    source_changed = False
    if source_type is not _UNSET and source_type is not None and source_type != task.source_type:
        task.source_type = source_type
        source_changed = True
    if source_id is not _UNSET and source_id is not None and source_id != task.source_id:
        task.source_id = source_id
        source_changed = True
    if source_module is not _UNSET and source_module is not None and source_module != task.source_module:
        task.source_module = source_module
        source_changed = True
    if source_changed:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            actor_type=activity_actor_type,
            actor_label=activity_actor_label,
            action="source_linked",
            from_value=previous_source_snapshot,
            to_value=f"{task.source_type}:{task.source_id or ''}:{task.source_module}",
        )

    if metadata is not _UNSET and metadata is not None:
        existing_metadata = _json_loads(task.metadata_json)
        merged = {**existing_metadata, **metadata}
        task.metadata_json = _json_dumps(merged)

    db.add(task)
    _record_task_audit(
        db,
        company_id=company_id,
        user_id=actor_user_id,
        task_id=task.id,
        action="governance_task_updated",
        metadata={"status": task.status, "priority": task.priority},
    )
    db.flush()
    return get_task_detail(db, company_id=company_id, task_id=task.id)


def ensure_task_for_source(
    db: Session,
    *,
    company_id: int,
    title: str,
    description: str | None,
    source_type: str,
    source_id: str,
    source_module: str,
    priority: str = "medium",
    incident_id: int | None = None,
    assignee_employee_id: int | None = None,
    reporter_employee_id: int | None = None,
    due_date: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    actor_user_id: int | None = None,
    reopen_closed: bool = True,
) -> GovernanceTask | None:
    if not _task_tables_available(db):
        return None

    existing = _latest_task_for_source(db, company_id=company_id, source_type=source_type, source_id=str(source_id))
    if existing is None:
        return create_task(
            db,
            company_id=company_id,
            title=title,
            description=description,
            priority=priority,
            source_type=source_type,
            source_id=str(source_id),
            source_module=source_module,
            incident_id=incident_id,
            assignee_employee_id=assignee_employee_id,
            reporter_employee_id=reporter_employee_id,
            due_date=due_date,
            metadata=metadata,
            actor_user_id=actor_user_id,
        )

    existing_metadata = _json_loads(existing.metadata_json)
    merged_metadata = {**existing_metadata, **(metadata or {})}
    recurrence_count = int(merged_metadata.get("recurrence_count") or 0) + 1
    merged_metadata["recurrence_count"] = recurrence_count
    merged_metadata["last_triggered_at"] = _now().isoformat()

    reopening = reopen_closed and existing.status in CLOSED_TASK_STATUSES
    if reopening:
        existing.status = "todo"
        existing.resolved_at = None
        add_task_activity(
            db,
            task_id=existing.id,
            company_id=company_id,
            actor_employee_id=reporter_employee_id,
            action="reopened",
            from_value="closed",
            to_value="todo",
        )

    existing.title = title
    existing.description = description
    if _priority_rank(priority) > _priority_rank(existing.priority):
        add_task_activity(
            db,
            task_id=existing.id,
            company_id=company_id,
            actor_employee_id=reporter_employee_id,
            action="priority_changed",
            from_value=existing.priority,
            to_value=priority,
        )
        existing.priority = priority
    if incident_id is not None:
        existing.incident_id = incident_id
    if assignee_employee_id is not None and existing.assignee_employee_id is None:
        existing.assignee_employee_id = assignee_employee_id
    if due_date is not None:
        existing.due_date = _coerce_dt(due_date)
    existing.metadata_json = _json_dumps(merged_metadata)
    db.add(existing)
    add_task_activity(
        db,
        task_id=existing.id,
        company_id=company_id,
        actor_employee_id=reporter_employee_id,
        action="source_retriggered",
        details=f"recurrence_count={recurrence_count}",
    )
    _record_task_audit(
        db,
        company_id=company_id,
        user_id=actor_user_id,
        task_id=existing.id,
        action="governance_task_source_retriggered",
        metadata={"source_type": source_type, "source_id": source_id, "recurrence_count": recurrence_count},
    )
    db.flush()
    return existing


def list_source_tasks(db: Session, *, company_id: int, source_type: str, source_id: str) -> list[dict[str, Any]]:
    if not _task_tables_available(db):
        return []
    tasks = (
        db.query(GovernanceTask)
        .filter(
            GovernanceTask.company_id == company_id,
            GovernanceTask.source_type == source_type,
            GovernanceTask.source_id == str(source_id),
        )
        .order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc())
        .all()
    )
    employee_ids = {
        task.assignee_employee_id
        for task in tasks
        if task.assignee_employee_id is not None
    } | {
        task.reporter_employee_id
        for task in tasks
        if task.reporter_employee_id is not None
    }
    employees = _employee_lookup(db, company_id, employee_ids)
    return [
        serialize_task(
            db,
            task,
            assignee=employees.get(task.assignee_employee_id),
            reporter=employees.get(task.reporter_employee_id),
        )
        for task in tasks
    ]


def create_incident_remediation_task(
    db: Session,
    *,
    company_id: int,
    incident: GRCIncident,
    incident_title: str,
    incident_status: str,
    actor_employee_id: int | None,
    actor_user_id: int | None,
) -> GovernanceTask | None:
    return ensure_task_for_source(
        db,
        company_id=company_id,
        title=f"Remediate incident: {incident_title}",
        description=incident.description,
        source_type="incident",
        source_id=str(incident.id),
        source_module="incidents",
        priority=_priority_from_severity(incident.severity),
        incident_id=incident.id,
        assignee_employee_id=incident.assigned_to_employee_id,
        reporter_employee_id=actor_employee_id,
        metadata={"severity": incident.severity, "incident_status": incident_status},
        actor_user_id=actor_user_id,
    )


def create_vendor_review_task(
    db: Session,
    *,
    company_id: int,
    vendor: Vendor,
    title: str,
    description: str,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    due_date: datetime | None = None,
) -> GovernanceTask | None:
    priority = "high" if (vendor.risk_rating or "").lower() == "high" else "medium"
    return ensure_task_for_source(
        db,
        company_id=company_id,
        title=title,
        description=description,
        source_type="vendor_review",
        source_id=str(vendor.id),
        source_module="vendors",
        priority=priority,
        reporter_employee_id=actor_employee_id,
        due_date=due_date,
        metadata={
            "vendor_name": vendor.vendor_name,
            "risk_rating": vendor.risk_rating,
            "security_review_status": vendor.security_review_status,
        },
        actor_user_id=actor_user_id,
    )


def create_employee_followup_task(
    db: Session,
    *,
    company_id: int,
    employee_id: int,
    employee_name: str,
    title: str,
    description: str,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    priority: str = "medium",
) -> GovernanceTask | None:
    return ensure_task_for_source(
        db,
        company_id=company_id,
        title=title,
        description=description,
        source_type="employee_followup",
        source_id=str(employee_id),
        source_module="employees",
        priority=priority,
        reporter_employee_id=actor_employee_id,
        metadata={"employee_name": employee_name},
        actor_user_id=actor_user_id,
    )


def create_test_failure_remediation_task(
    db: Session,
    *,
    company_id: int,
    test_node_id: str,
    test_name: str,
    title: str,
    description: str,
    priority: str,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    assignee_employee_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceTask | None:
    return ensure_task_for_source(
        db,
        company_id=company_id,
        title=title,
        description=description,
        source_type="test_failure",
        source_id=test_node_id,
        source_module="testing",
        priority=priority,
        assignee_employee_id=assignee_employee_id,
        reporter_employee_id=actor_employee_id,
        metadata={"test_name": test_name, **(metadata or {})},
        actor_user_id=actor_user_id,
    )


def ensure_security_event_task(db: Session, *, event: SecurityEvent) -> GovernanceTask | None:
    if not _task_tables_available(db) or event.company_id is None:
        return None
    event_type = (event.event_type or "").strip()
    severity = (event.severity or "medium").lower()
    if severity not in {"high", "critical"} and event_type not in {"token_abuse", "REFRESH_TOKEN_MISMATCH", "SUSPICIOUS_ACTIVITY"}:
        return None
    metadata = _json_loads(event.event_metadata)
    description = event.description
    if metadata.get("token_issue"):
        description = f"{description}\nRecommended action: review token/session activity and revoke related access."
    return ensure_task_for_source(
        db,
        company_id=event.company_id,
        title=f"Investigate security alert: {_format_security_event_label(event_type)}",
        description=description,
        source_type="security_alert",
        source_id=str(event.id),
        source_module="security",
        priority=_priority_from_severity(severity),
        reporter_employee_id=None,
        metadata={"event_type": event_type, "severity": severity, **metadata},
        actor_user_id=event.user_id,
    )



