from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.models.employee import Employee
from database.models.governance_task import GovernanceTask
from services.automated_changes_execution_service import (
    complete_automation_execution,
    fail_automation_execution,
    start_automation_execution,
    update_automation_execution_metadata,
)
from services.governance_task_service import (
    CLOSED_TASK_STATUSES,
    OPEN_TASK_STATUSES,
    add_task_activity,
    create_task,
    get_task_detail,
    serialize_task,
    update_task,
)

AUTOMATION_ASSIGNEE_TYPE = "automation"
AUTOMATION_ASSIGNEE_LABEL = "Automated Changes"
AUTOMATION_SOURCE_TYPE = "backlog_improvement"
AUTOMATION_SOURCE_MODULE = "automation"
AUTOMATION_ACTIVE_STATUS = "in_progress"
SYNCABLE_BACKLOG_STATUSES = {"open", "in_progress", "blocked"}
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
DEFAULT_BACKLOG_PATH = Path(__file__).resolve().parent.parent / "docs" / "copilot_improvement_backlog.md"


@dataclass(slots=True)
class BacklogItem:
    item_id: str
    title: str
    area: str
    priority: str
    risk: str
    status: str
    description: str | None
    suggested_improvement: str | None
    dependencies: str | None
    suggested_branch: str | None
    notes: str | None
    eligible_for_automation: bool
    eligibility_reason: str


def _read_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _relative_backlog_path(path: Path) -> str:
    root = Path(__file__).resolve().parent.parent
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _normalize_field_name(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")


def _normalize_priority(value: str | None) -> str:
    normalized = (value or "medium").strip().lower().replace(" ", "_")
    return normalized if normalized in PRIORITY_ORDER else "medium"


def _normalize_risk(value: str | None) -> str:
    normalized = (value or "medium").strip().lower().replace(" ", "_")
    return normalized if normalized in {"low", "medium", "high", "critical"} else "medium"


def _normalize_backlog_status(value: str | None) -> str:
    normalized = (value or "open").strip().lower()
    normalized = normalized.replace("ready for review", "ready_for_review")
    normalized = normalized.replace("in progress", "in_progress")
    normalized = normalized.replace("won't do", "wont_do")
    normalized = normalized.replace("won?t do", "wont_do")
    normalized = normalized.replace(" ", "_")
    if normalized in {"open", "in_progress", "blocked", "deferred", "completed", "wont_do"}:
        return normalized
    return "open"


def _normalize_bool(value: str | None) -> bool | None:
    normalized = (value or "").strip().lower()
    if normalized in {"yes", "true", "y"}:
        return True
    if normalized in {"no", "false", "n"}:
        return False
    return None


def _priority_rank(priority: str | None) -> int:
    return PRIORITY_ORDER.get((priority or "").lower(), 0)


def _derive_eligibility(item_fields: dict[str, str]) -> tuple[bool, str]:
    explicit = _normalize_bool(item_fields.get("eligible_for_automation"))
    risk = _normalize_risk(item_fields.get("risk"))
    status = _normalize_backlog_status(item_fields.get("status"))
    dependencies = (item_fields.get("dependencies") or "").strip()
    dependency_blocked = bool(dependencies and dependencies.lower() not in {"none", "n/a"})

    if explicit is False:
        return False, "Marked as not eligible in the backlog."
    if status in {"deferred", "completed", "wont_do"}:
        return False, f"Backlog item is {status.replace('_', ' ')}."
    if risk in {"high", "critical"}:
        return False, "Risk is too high for automated execution without explicit approval."
    if dependency_blocked:
        return False, "Dependencies must be cleared before automation can start this item."
    if explicit is True:
        return True, "Explicitly marked as automation-eligible in the backlog."
    return True, "Low-risk contained improvement eligible for governed automation."


def parse_backlog_file(backlog_path: str | Path | None = None) -> list[BacklogItem]:
    path = Path(backlog_path or DEFAULT_BACKLOG_PATH)
    if not path.exists():
        return []

    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_field: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            if current is not None:
                items.append(current)
            current = {"id": line[3:].strip()}
            current_field = None
            continue
        if current is None:
            continue
        if line.startswith("- ") and ":" in line[2:]:
            key, value = line[2:].split(":", 1)
            current_field = _normalize_field_name(key)
            current[current_field] = value.strip()
            continue
        if line.startswith("  ") and current_field:
            current[current_field] = f"{current.get(current_field, '')} {line.strip()}".strip()
    if current is not None:
        items.append(current)

    parsed: list[BacklogItem] = []
    for fields in items:
        eligible, reason = _derive_eligibility(fields)
        parsed.append(
            BacklogItem(
                item_id=fields.get("id") or "",
                title=(fields.get("title") or fields.get("id") or "Untitled backlog item").strip(),
                area=(fields.get("area") or "Platform").strip(),
                priority=_normalize_priority(fields.get("priority")),
                risk=_normalize_risk(fields.get("risk")),
                status=_normalize_backlog_status(fields.get("status")),
                description=(fields.get("description") or "").strip() or None,
                suggested_improvement=(fields.get("suggested_improvement") or "").strip() or None,
                dependencies=(fields.get("dependencies") or "").strip() or None,
                suggested_branch=(fields.get("suggested_branch") or "").strip() or None,
                notes=(fields.get("notes") or "").strip() or None,
                eligible_for_automation=eligible,
                eligibility_reason=reason,
            )
        )
    return parsed


def _task_metadata(task: GovernanceTask) -> dict[str, Any]:
    return _read_json(task.metadata_json)


def _task_eligible_for_automation(task: GovernanceTask) -> bool:
    return bool(_task_metadata(task).get("eligible_for_automation"))


def _build_metadata(item: BacklogItem, *, backlog_path: Path, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    return {
        **existing,
        "backlog_item_id": item.item_id,
        "backlog_file_path": _relative_backlog_path(backlog_path),
        "backlog_status": item.status,
        "area": item.area,
        "risk": item.risk,
        "eligible_for_automation": item.eligible_for_automation,
        "automation_eligibility_reason": item.eligibility_reason,
        "dependencies": item.dependencies,
        "suggested_branch": item.suggested_branch,
        "suggested_improvement": item.suggested_improvement,
        "notes": item.notes,
        "automation_source": "backlog",
        "owner_type": existing.get("owner_type") or "unassigned",
        "execution_mode": existing.get("execution_mode") or "manual",
        "review_state": existing.get("review_state") or "none",
        "review_expectation": existing.get("review_expectation") or "Human review is required before the task can be completed.",
        "branch_name": existing.get("branch_name"),
        "commit_message": existing.get("commit_message"),
        "implementation_summary": existing.get("implementation_summary"),
        "review_notes": existing.get("review_notes"),
    }


def _serialize_task_list(db: Session, company_id: int, tasks: list[GovernanceTask]) -> list[dict[str, Any]]:
    employee_ids = {
        task.assignee_employee_id
        for task in tasks
        if task.assignee_employee_id is not None
    } | {
        task.reporter_employee_id
        for task in tasks
        if task.reporter_employee_id is not None
    }
    employees = {}
    if employee_ids:
        employees = {
            employee.id: employee
            for employee in db.query(Employee)
            .filter(Employee.company_id == company_id, Employee.id.in_(employee_ids))
            .all()
        }
    return [
        serialize_task(
            db,
            task,
            assignee=employees.get(task.assignee_employee_id),
            reporter=employees.get(task.reporter_employee_id),
        )
        for task in tasks
    ]


def _automation_tasks_query(db: Session, company_id: int):
    return db.query(GovernanceTask).filter(
        GovernanceTask.company_id == company_id,
        GovernanceTask.source_type == AUTOMATION_SOURCE_TYPE,
    )


def _get_active_automation_task(db: Session, company_id: int) -> GovernanceTask | None:
    return (
        _automation_tasks_query(db, company_id)
        .filter(
            GovernanceTask.assignee_type == AUTOMATION_ASSIGNEE_TYPE,
            GovernanceTask.status == AUTOMATION_ACTIVE_STATUS,
        )
        .order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc())
        .first()
    )


def _get_task(db: Session, company_id: int, task_id: int) -> GovernanceTask | None:
    return (
        db.query(GovernanceTask)
        .filter(GovernanceTask.company_id == company_id, GovernanceTask.id == task_id)
        .first()
    )


def _require_automation_backlog_task(db: Session, company_id: int, task_id: int) -> GovernanceTask:
    task = _get_task(db, company_id, task_id)
    if task is None:
        raise ValueError("Task not found.")
    if task.source_type != AUTOMATION_SOURCE_TYPE:
        raise ValueError("Only backlog-synced automation tasks can use the automated changes workflow.")
    return task


def _ensure_automation_can_start(db: Session, company_id: int, task_id: int | None = None) -> None:
    active = _get_active_automation_task(db, company_id)
    if active is not None and active.id != task_id:
        raise ValueError(f"{AUTOMATION_ASSIGNEE_LABEL} already has an active task in progress.")


def _ensure_eligible(task: GovernanceTask) -> None:
    metadata = _task_metadata(task)
    if metadata.get("eligible_for_automation"):
        return
    reason = metadata.get("automation_eligibility_reason") or "This backlog item is not eligible for automated execution."
    raise ValueError(str(reason))


def _sort_tasks(tasks: list[GovernanceTask]) -> list[GovernanceTask]:
    return sorted(
        tasks,
        key=lambda task: (
            -_priority_rank(task.priority),
            task.due_date.isoformat() if task.due_date else "9999-12-31T00:00:00+00:00",
            -(task.id or 0),
        ),
    )


def list_automation_tasks(db: Session, *, company_id: int, backlog_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(backlog_path or DEFAULT_BACKLOG_PATH)
    backlog_items = parse_backlog_file(path)
    tasks = _automation_tasks_query(db, company_id).order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc()).all()
    serialized_tasks = _serialize_task_list(db, company_id, tasks)
    tasks_by_source = {task["source_id"]: task for task in serialized_tasks if task.get("source_id")}

    active_task = next((task for task in serialized_tasks if task.get("assignee_type") == AUTOMATION_ASSIGNEE_TYPE and task.get("status") == AUTOMATION_ACTIVE_STATUS), None)
    queued_tasks = [
        task
        for task in serialized_tasks
        if task.get("status") in OPEN_TASK_STATUSES
        and task.get("status") != "ready_for_review"
        and (not active_task or task.get("id") != active_task.get("id"))
    ]
    ready_for_review_tasks = [task for task in serialized_tasks if task.get("status") == "ready_for_review"]
    completed_tasks = [task for task in serialized_tasks if task.get("status") in CLOSED_TASK_STATUSES]
    eligible_tasks = [task for task in queued_tasks if task.get("metadata", {}).get("eligible_for_automation")]

    backlog_payload = []
    for item in backlog_items:
        linked_task = tasks_by_source.get(item.item_id)
        backlog_payload.append(
            {
                "id": item.item_id,
                "title": item.title,
                "area": item.area,
                "priority": item.priority,
                "risk": item.risk,
                "status": item.status,
                "description": item.description,
                "suggested_improvement": item.suggested_improvement,
                "dependencies": item.dependencies,
                "suggested_branch": item.suggested_branch,
                "notes": item.notes,
                "eligible_for_automation": item.eligible_for_automation,
                "eligibility_reason": item.eligibility_reason,
                "task_id": linked_task.get("id") if linked_task else None,
                "task_key": linked_task.get("task_key") if linked_task else None,
                "task_status": linked_task.get("status") if linked_task else None,
            }
        )

    return {
        "backlog_path": _relative_backlog_path(path),
        "summary": {
            "backlog_items": len(backlog_items),
            "synced_tasks": len(serialized_tasks),
            "eligible_tasks": len(eligible_tasks),
            "active_tasks": 1 if active_task else 0,
            "ready_for_review": len(ready_for_review_tasks),
            "completed": len(completed_tasks),
        },
        "active_task": active_task,
        "eligible_tasks": eligible_tasks,
        "queued_tasks": queued_tasks,
        "ready_for_review_tasks": ready_for_review_tasks,
        "completed_tasks": completed_tasks,
        "backlog_items": backlog_payload,
    }


def sync_backlog_tasks(
    db: Session,
    *,
    company_id: int,
    actor_user_id: int | None,
    backlog_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(backlog_path or DEFAULT_BACKLOG_PATH)
    items = parse_backlog_file(path)
    existing_tasks = {
        task.source_id: task
        for task in _automation_tasks_query(db, company_id).all()
        if task.source_id
    }

    created = 0
    updated = 0
    skipped = 0
    for item in items:
        existing = existing_tasks.get(item.item_id)
        if existing is None and item.status not in SYNCABLE_BACKLOG_STATUSES:
            skipped += 1
            continue

        existing_metadata = _task_metadata(existing) if existing is not None else {}
        metadata = _build_metadata(item, backlog_path=path, existing=existing_metadata)
        description = item.description or item.suggested_improvement or f"Backlog item {item.item_id}"
        title_changed = existing is not None and existing.title != item.title
        description_changed = existing is not None and existing.description != description
        metadata_changed = existing is not None and metadata != existing_metadata
        priority_changed = existing is not None and _priority_rank(item.priority) > _priority_rank(existing.priority)

        if existing is None:
            task = create_task(
                db,
                company_id=company_id,
                title=item.title,
                description=description,
                status="blocked" if item.status == "blocked" else "todo",
                priority=item.priority,
                source_type=AUTOMATION_SOURCE_TYPE,
                source_id=item.item_id,
                source_module=AUTOMATION_SOURCE_MODULE,
                metadata=metadata,
                actor_user_id=actor_user_id,
                activity_actor_type=AUTOMATION_ASSIGNEE_TYPE,
                activity_actor_label=AUTOMATION_ASSIGNEE_LABEL,
            )
            if task is not None:
                add_task_activity(
                    db,
                    task_id=task.id,
                    company_id=company_id,
                    actor_employee_id=None,
                    actor_type=AUTOMATION_ASSIGNEE_TYPE,
                    actor_label=AUTOMATION_ASSIGNEE_LABEL,
                    action="backlog_synced",
                    details=f"Created from backlog item {item.item_id}.",
                )
                created += 1
            continue

        update_kwargs: dict[str, Any] = {
            "title": item.title,
            "description": description,
            "metadata": metadata,
            "source_type": AUTOMATION_SOURCE_TYPE,
            "source_id": item.item_id,
            "source_module": AUTOMATION_SOURCE_MODULE,
        }
        if priority_changed:
            update_kwargs["priority"] = item.priority
        detail = update_task(
            db,
            company_id=company_id,
            task_id=existing.id,
            actor_employee_id=None,
            actor_user_id=actor_user_id,
            activity_actor_type=AUTOMATION_ASSIGNEE_TYPE,
            activity_actor_label=AUTOMATION_ASSIGNEE_LABEL,
            **update_kwargs,
        )
        if detail is not None and (title_changed or description_changed or metadata_changed or priority_changed):
            add_task_activity(
                db,
                task_id=existing.id,
                company_id=company_id,
                actor_employee_id=None,
                actor_type=AUTOMATION_ASSIGNEE_TYPE,
                actor_label=AUTOMATION_ASSIGNEE_LABEL,
                action="backlog_synced",
                details=f"Resynced backlog item {item.item_id}.",
            )
            updated += 1

    queue = list_automation_tasks(db, company_id=company_id, backlog_path=path)
    queue["sync"] = {"created": created, "updated": updated, "skipped": skipped}
    return queue


def assign_task_to_automation(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_employee_id: int | None,
    actor_user_id: int | None,
) -> dict[str, Any]:
    task = _require_automation_backlog_task(db, company_id, task_id)
    _ensure_eligible(task)
    return update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        assignee_employee_id=None,
        assignee_type=AUTOMATION_ASSIGNEE_TYPE,
        assignee_label=AUTOMATION_ASSIGNEE_LABEL,
        metadata={
            "owner_type": AUTOMATION_ASSIGNEE_TYPE,
            "execution_mode": "governed_automation",
            "automation_source": "backlog",
            "review_state": "queued",
        },
    )


def start_automation_task(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
) -> dict[str, Any]:
    return start_automation_execution(
        db,
        company_id=company_id,
        task_id=task_id,
        actor_user_id=actor_user_id,
    )


def start_next_automation_task(
    db: Session,
    *,
    company_id: int,
    actor_user_id: int | None,
) -> dict[str, Any] | None:
    _ensure_automation_can_start(db, company_id)
    candidates = _sort_tasks(
        _automation_tasks_query(db, company_id)
        .filter(
            GovernanceTask.status == "todo",
            or_(
                GovernanceTask.assignee_employee_id.is_(None),
                GovernanceTask.assignee_type == AUTOMATION_ASSIGNEE_TYPE,
            ),
        )
        .all()
    )
    for task in candidates:
        if _task_eligible_for_automation(task):
            return start_automation_task(
                db,
                company_id=company_id,
                task_id=task.id,
                actor_user_id=actor_user_id,
            )
    return None


def block_automation_task(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
    reason: str | None = None,
) -> dict[str, Any]:
    return fail_automation_execution(
        db,
        company_id=company_id,
        task_id=task_id,
        actor_user_id=actor_user_id,
        next_status="blocked",
        error_summary=reason,
    )


def mark_task_ready_for_review(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
    branch_name: str | None = None,
    commit_message: str | None = None,
    implementation_summary: str | None = None,
    review_notes: str | None = None,
    execution_notes: str | None = None,
) -> dict[str, Any]:
    return complete_automation_execution(
        db,
        company_id=company_id,
        task_id=task_id,
        actor_user_id=actor_user_id,
        target_status="ready_for_review",
        branch_name=branch_name,
        commit_message=commit_message,
        implementation_summary=implementation_summary,
        review_notes=review_notes,
        execution_notes=execution_notes,
    )


def return_task_to_backlog(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    review_notes: str | None = None,
) -> dict[str, Any]:
    task = _require_automation_backlog_task(db, company_id, task_id)
    detail = update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        status="todo",
        assignee_employee_id=None,
        assignee_type=None,
        assignee_label=None,
        metadata={
            "owner_type": "unassigned",
            "execution_mode": "manual",
            "review_state": "reopened",
            "review_notes": review_notes,
        },
    )
    add_task_activity(
        db,
        task_id=task.id,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        action="returned_to_backlog",
        details=review_notes or "Returned to backlog for another iteration.",
    )
    db.flush()
    return get_task_detail(db, company_id=company_id, task_id=task.id) if detail is not None else None


def update_automation_task_metadata(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_employee_id: int | None,
    actor_user_id: int | None,
    branch_name: str | None = None,
    commit_message: str | None = None,
    implementation_summary: str | None = None,
    review_notes: str | None = None,
    execution_notes: str | None = None,
    error_summary: str | None = None,
) -> dict[str, Any]:
    return update_automation_execution_metadata(
        db,
        company_id=company_id,
        task_id=task_id,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        branch_name=branch_name,
        commit_message=commit_message,
        implementation_summary=implementation_summary,
        review_notes=review_notes,
        execution_notes=execution_notes,
        error_summary=error_summary,
    )
