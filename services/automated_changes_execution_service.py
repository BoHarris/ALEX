from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from database.models.governance_task import GovernanceTask
from services.governance_task_service import (
    CLOSED_TASK_STATUSES,
    add_task_activity,
    get_task_detail,
    update_task,
)

logger = logging.getLogger(__name__)


def _trigger_llm_completion_async(
    company_id: int,
    task_id: int,
    actor_user_id: int | None = None,
) -> None:
    """
    Trigger LLM-based task completion asynchronously.
    
    This function spawns a background task to generate and submit LLM completion details.
    It does NOT block the main execution flow.
    
    Args:
        company_id: Company ID for scoping
        task_id: Task ID to complete
        actor_user_id: User ID triggering the action
    """
    try:
        from services.task_llm_completion_service import generate_and_submit_llm_completion
        from database.database import SessionLocal
        
        # Check if LLM is enabled
        from services.llm_config import get_llm_config
        config = get_llm_config()
        
        if not config.enabled:
            logger.debug(f"LLM auto-complete disabled. Skipping for task {task_id}")
            return
        
        # Create new session for background operation
        db = SessionLocal()
        try:
            logger.info(f"Spawning LLM completion for task {task_id}")
            generate_and_submit_llm_completion(
                db,
                company_id=company_id,
                task_id=task_id,
                actor_user_id=actor_user_id,
            )
            db.commit()
        except Exception as e:
            logger.error(f"Error in LLM completion for task {task_id}: {e}")
            db.rollback()
        finally:
            db.close()
    except ImportError:
        logger.debug("LLM services not available")
    except Exception as e:
        logger.warning(f"Failed to trigger LLM completion: {e}")


AUTOMATION_ASSIGNEE_TYPE = "automation"
AUTOMATION_ASSIGNEE_LABEL = "Automated Changes"
AUTOMATION_ACTIVE_STATUS = "in_progress"
AUTOMATION_EXECUTABLE_SOURCE_TYPES = {
    "backlog_improvement",
    "automated_change",
    "system_improvement",
    "repo_audit",
}
AUTOMATION_SUCCESS_STATUSES = {"done", "ready_for_review"}
AUTOMATION_FAILURE_STATUSES = {"blocked", "todo"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _read_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _get_task(db: Session, company_id: int, task_id: int) -> GovernanceTask | None:
    return (
        db.query(GovernanceTask)
        .filter(GovernanceTask.company_id == company_id, GovernanceTask.id == task_id)
        .first()
    )


def _get_active_task_record(db: Session, company_id: int) -> GovernanceTask | None:
    return (
        db.query(GovernanceTask)
        .filter(
            GovernanceTask.company_id == company_id,
            GovernanceTask.assignee_type == AUTOMATION_ASSIGNEE_TYPE,
            GovernanceTask.status == AUTOMATION_ACTIVE_STATUS,
        )
        .order_by(GovernanceTask.updated_at.desc(), GovernanceTask.id.desc())
        .first()
    )


def get_active_automation_task(db: Session, *, company_id: int) -> dict[str, Any] | None:
    active = _get_active_task_record(db, company_id)
    if active is None:
        return None
    return get_task_detail(db, company_id=company_id, task_id=active.id)


def _task_metadata(task: GovernanceTask) -> dict[str, Any]:
    return _read_json(task.metadata_json)


def _supports_automation(task: GovernanceTask) -> bool:
    metadata = _task_metadata(task)
    return bool(
        task.source_type in AUTOMATION_EXECUTABLE_SOURCE_TYPES
        or task.assignee_type == AUTOMATION_ASSIGNEE_TYPE
        or metadata.get("automation_source")
        or metadata.get("eligible_for_automation")
    )


def _require_automation_task(db: Session, company_id: int, task_id: int) -> GovernanceTask:
    task = _get_task(db, company_id, task_id)
    if task is None:
        raise ValueError("Task not found.")
    if not _supports_automation(task):
        raise ValueError("This task is not configured for the Automated Changes workflow.")
    return task


def _ensure_eligible(task: GovernanceTask) -> None:
    metadata = _task_metadata(task)
    if metadata.get("eligible_for_automation"):
        return
    reason = metadata.get("automation_eligibility_reason") or "This task is not eligible for automated execution."
    raise ValueError(str(reason))


def _require_running_automation_task(db: Session, company_id: int, task_id: int) -> GovernanceTask:
    task = _require_automation_task(db, company_id, task_id)
    if task.status != AUTOMATION_ACTIVE_STATUS or task.assignee_type != AUTOMATION_ASSIGNEE_TYPE:
        raise ValueError("Only running automation tasks can use this execution action.")
    active = _get_active_task_record(db, company_id)
    if active is None or active.id != task.id:
        raise ValueError("This automation task is not the active execution slot.")
    return task


def _ensure_automation_can_start(db: Session, company_id: int, task_id: int) -> None:
    active = _get_active_task_record(db, company_id)
    if active is not None:
        if active.id == task_id:
            raise ValueError("This automation task is already in progress.")
        raise ValueError(f"{AUTOMATION_ASSIGNEE_LABEL} already has an active task in progress.")


def _build_execution_metadata(
    task: GovernanceTask,
    *,
    review_state: str,
    automation_status: str,
    automation_result: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    branch_name: str | None | object = None,
    commit_message: str | None | object = None,
    implementation_summary: str | None | object = None,
    review_notes: str | None | object = None,
    execution_notes: str | None | object = None,
    error_summary: str | None | object = None,
    blocked_reason: str | None | object = None,
    owner_type: str = AUTOMATION_ASSIGNEE_TYPE,
    execution_mode: str = "governed_automation",
) -> dict[str, Any]:
    current = _task_metadata(task)
    metadata = {
        "owner_type": owner_type,
        "execution_mode": execution_mode,
        "automation_source": current.get("automation_source") or ("backlog" if task.source_type == "backlog_improvement" else task.source_type),
        "review_state": review_state,
        "automation_status": automation_status,
        "automation_result": automation_result,
        "automation_started_at": started_at or current.get("automation_started_at"),
        "automation_completed_at": completed_at,
    }
    for key, value in (
        ("branch_name", branch_name),
        ("commit_message", commit_message),
        ("implementation_summary", implementation_summary),
        ("review_notes", review_notes),
        ("execution_notes", execution_notes),
        ("error_summary", error_summary),
        ("blocked_reason", blocked_reason),
    ):
        if value is not None:
            metadata[key] = value
    return metadata


def start_automation_execution(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
) -> dict[str, Any]:
    task = _require_automation_task(db, company_id, task_id)
    _ensure_eligible(task)
    if task.status in CLOSED_TASK_STATUSES:
        raise ValueError("Completed automation tasks cannot be restarted without explicit reopen logic.")
    if task.status != "todo":
        raise ValueError("Automation can only start from a queued task.")
    _ensure_automation_can_start(db, company_id, task.id)
    detail = update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=None,
        actor_user_id=actor_user_id,
        assignee_employee_id=None,
        assignee_type=AUTOMATION_ASSIGNEE_TYPE,
        assignee_label=AUTOMATION_ASSIGNEE_LABEL,
        status=AUTOMATION_ACTIVE_STATUS,
        metadata=_build_execution_metadata(
            task,
            review_state="in_progress",
            automation_status="running",
            automation_result="in_progress",
            started_at=_now_iso(),
            completed_at=None,
            error_summary=None,
            blocked_reason=None,
        ),
        activity_actor_type=AUTOMATION_ASSIGNEE_TYPE,
        activity_actor_label=AUTOMATION_ASSIGNEE_LABEL,
    )
    add_task_activity(
        db,
        task_id=task.id,
        company_id=company_id,
        actor_employee_id=None,
        actor_type=AUTOMATION_ASSIGNEE_TYPE,
        actor_label=AUTOMATION_ASSIGNEE_LABEL,
        action="automation_started",
        details="Automated Changes started implementation work.",
    )
    db.flush()
    
    # Trigger LLM-based completion (non-blocking, async)
    _trigger_llm_completion_async(
        company_id=company_id,
        task_id=task.id,
        actor_user_id=actor_user_id,
    )
    
    return get_task_detail(db, company_id=company_id, task_id=task.id) if detail is not None else None


def complete_automation_execution(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
    target_status: str = "done",
    branch_name: str | None = None,
    commit_message: str | None = None,
    implementation_summary: str | None = None,
    review_notes: str | None = None,
    execution_notes: str | None = None,
) -> dict[str, Any]:
    if target_status not in AUTOMATION_SUCCESS_STATUSES:
        raise ValueError("Automation completion must target done or ready_for_review.")
    task = _require_running_automation_task(db, company_id, task_id)
    review_state = "completed" if target_status == "done" else "pending_review"
    result_label = "done" if target_status == "done" else "ready_for_review"
    detail = update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=None,
        actor_user_id=actor_user_id,
        assignee_employee_id=None,
        assignee_type=AUTOMATION_ASSIGNEE_TYPE,
        assignee_label=AUTOMATION_ASSIGNEE_LABEL,
        status=target_status,
        metadata=_build_execution_metadata(
            task,
            review_state=review_state,
            automation_status="succeeded",
            automation_result=result_label,
            started_at=_task_metadata(task).get("automation_started_at") or _now_iso(),
            completed_at=_now_iso(),
            branch_name=branch_name,
            commit_message=commit_message,
            implementation_summary=implementation_summary,
            review_notes=review_notes,
            execution_notes=execution_notes,
            error_summary=None,
            blocked_reason=None,
        ),
        activity_actor_type=AUTOMATION_ASSIGNEE_TYPE,
        activity_actor_label=AUTOMATION_ASSIGNEE_LABEL,
    )
    add_task_activity(
        db,
        task_id=task.id,
        company_id=company_id,
        actor_employee_id=None,
        actor_type=AUTOMATION_ASSIGNEE_TYPE,
        actor_label=AUTOMATION_ASSIGNEE_LABEL,
        action="automation_completed" if target_status == "done" else "automation_ready_for_review",
        details=implementation_summary
        or (
            "Automated Changes completed this task and moved it to done."
            if target_status == "done"
            else "Implementation completed and moved to ready for review."
        ),
    )
    db.flush()
    return get_task_detail(db, company_id=company_id, task_id=task.id) if detail is not None else None


def fail_automation_execution(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: int | None,
    next_status: str = "blocked",
    branch_name: str | None = None,
    commit_message: str | None = None,
    implementation_summary: str | None = None,
    review_notes: str | None = None,
    execution_notes: str | None = None,
    error_summary: str | None = None,
) -> dict[str, Any]:
    if next_status not in AUTOMATION_FAILURE_STATUSES:
        raise ValueError("Automation failure must transition to blocked or todo.")
    task = _require_running_automation_task(db, company_id, task_id)
    reopening = next_status == "todo"
    detail = update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=None,
        actor_user_id=actor_user_id,
        assignee_employee_id=None,
        assignee_type=AUTOMATION_ASSIGNEE_TYPE if not reopening else None,
        assignee_label=AUTOMATION_ASSIGNEE_LABEL if not reopening else None,
        status=next_status,
        metadata=_build_execution_metadata(
            task,
            review_state="reopened" if reopening else "blocked",
            automation_status="failed",
            automation_result="reopened" if reopening else "blocked",
            started_at=_task_metadata(task).get("automation_started_at") or _now_iso(),
            completed_at=_now_iso(),
            branch_name=branch_name,
            commit_message=commit_message,
            implementation_summary=implementation_summary,
            review_notes=review_notes,
            execution_notes=execution_notes,
            error_summary=error_summary,
            blocked_reason=error_summary or review_notes,
            owner_type="unassigned" if reopening else AUTOMATION_ASSIGNEE_TYPE,
            execution_mode="manual" if reopening else "governed_automation",
        ),
        activity_actor_type=AUTOMATION_ASSIGNEE_TYPE,
        activity_actor_label=AUTOMATION_ASSIGNEE_LABEL,
    )
    add_task_activity(
        db,
        task_id=task.id,
        company_id=company_id,
        actor_employee_id=None,
        actor_type=AUTOMATION_ASSIGNEE_TYPE,
        actor_label=AUTOMATION_ASSIGNEE_LABEL,
        action="automation_failed",
        details=error_summary
        or (
            "Automated Changes failed and returned the task to backlog."
            if reopening
            else "Automated Changes failed and marked the task as blocked."
        ),
    )
    db.flush()
    return get_task_detail(db, company_id=company_id, task_id=task.id) if detail is not None else None


def update_automation_execution_metadata(
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
    task = _require_automation_task(db, company_id, task_id)
    metadata = {
        key: value
        for key, value in (
            ("branch_name", branch_name),
            ("commit_message", commit_message),
            ("implementation_summary", implementation_summary),
            ("review_notes", review_notes),
            ("execution_notes", execution_notes),
            ("error_summary", error_summary),
        )
        if value is not None
    }
    detail = update_task(
        db,
        company_id=company_id,
        task_id=task.id,
        actor_employee_id=actor_employee_id,
        actor_user_id=actor_user_id,
        metadata=metadata,
    )
    changed_fields = [
        label
        for label, value in (
            ("branch", branch_name),
            ("commit message", commit_message),
            ("implementation summary", implementation_summary),
            ("review notes", review_notes),
            ("execution notes", execution_notes),
            ("error summary", error_summary),
        )
        if value is not None
    ]
    if changed_fields:
        add_task_activity(
            db,
            task_id=task.id,
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            action="automation_metadata_updated",
            details="Updated " + ", ".join(changed_fields) + ".",
        )
    db.flush()
    return get_task_detail(db, company_id=company_id, task_id=task.id) if detail is not None else None
