from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from database.models.security_event import SecurityEvent
from services.governance_task_service import ensure_security_event_task


def _serialize_metadata(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    try:
        return json.dumps(metadata, sort_keys=True, default=str)
    except Exception:
        return None


def parse_security_event_metadata(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        data = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def record_security_event(
    db: Session,
    *,
    company_id: int | None,
    user_id: int | None,
    event_type: str,
    severity: str,
    description: str,
    ip_address: str | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        company_id=company_id,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        description=description,
        ip_address=ip_address,
        event_metadata=_serialize_metadata(event_metadata),
    )
    db.add(event)
    db.flush()
    ensure_security_event_task(db, event=event)
    return event


def serialize_security_event(event: SecurityEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "company_id": event.company_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "description": event.description,
        "ip_address": event.ip_address,
        "metadata": parse_security_event_metadata(event.event_metadata),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
