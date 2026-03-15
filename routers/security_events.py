from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.security_event import SecurityEvent
from dependencies.tier_guard import require_company_admin
from pydantic import BaseModel
from services.governance_task_service import get_task_detail, list_source_tasks, update_task
from utils.security_events import serialize_security_event

router = APIRouter(prefix="/security", tags=["Security"])


class SecurityEventTaskRequest(BaseModel):
    assignee_employee_id: int | None = None
    due_date: str | None = None


@router.get("/events")
def list_security_events(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.company_id == current_user["company_id"])
        .order_by(desc(SecurityEvent.created_at))
        .limit(200)
        .all()
    )
    return {
        "events": [
            {
                **serialize_security_event(event),
                "linked_tasks": list_source_tasks(
                    db,
                    company_id=current_user["company_id"],
                    source_type="security_alert",
                    source_id=str(event.id),
                ),
            }
            for event in events
        ]
    }


@router.post("/events/{event_id}/task")
def create_or_update_security_event_task(
    event_id: int,
    payload: SecurityEventTaskRequest,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    event = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.id == event_id, SecurityEvent.company_id == current_user["company_id"])
        .first()
    )
    if event is None:
        return {"task": None}
    linked_tasks = list_source_tasks(db, company_id=current_user["company_id"], source_type="security_alert", source_id=str(event.id))
    if not linked_tasks:
        return {"task": None}
    task_id = linked_tasks[0]["id"]
    if payload.assignee_employee_id is not None or payload.due_date is not None:
        update_task(
            db,
            company_id=current_user["company_id"],
            task_id=task_id,
            actor_employee_id=None,
            actor_user_id=current_user["user_id"],
            assignee_employee_id=payload.assignee_employee_id,
        )
        db.commit()
    return {"task": get_task_detail(db, company_id=current_user["company_id"], task_id=task_id)}
