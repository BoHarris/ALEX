from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from database.models.audit_event import AuditEvent
from services.security_service import RequestSecurityContext, create_audit_log

logger = logging.getLogger(__name__)


def _serialize_event_metadata(event_metadata: dict[str, Any] | None) -> str | None:
    if not event_metadata:
        return None
    try:
        return json.dumps(event_metadata, sort_keys=True, default=str)
    except Exception:
        logger.exception("Failed to serialize audit event metadata")
        return None


def parse_audit_event_metadata(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        data = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def serialize_audit_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "event_category": event.event_category,
        "description": event.description,
        "metadata": parse_audit_event_metadata(event.event_metadata),
        "user_id": event.user_id,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def list_audit_events(
    db: Session,
    *,
    company_id: int,
    limit: int = 50,
    user_id: int | None = None,
    scan_id: int | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AuditEvent]:
    query = db.query(AuditEvent).filter(AuditEvent.company_id == company_id)
    if user_id is not None:
        query = query.filter(AuditEvent.user_id == user_id)
    if scan_id is not None:
        query = query.filter(AuditEvent.target_type == "scan", AuditEvent.target_id == str(scan_id))
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if date_from is not None:
        query = query.filter(AuditEvent.created_at >= date_from)
    if date_to is not None:
        query = query.filter(AuditEvent.created_at <= date_to)
    return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()


def record_audit_event(
    db: Session,
    *,
    company_id: int | None,
    user_id: int | None,
    event_type: str,
    description: str,
    target_type: str | None = None,
    target_id: str | None = None,
    event_category: str = "system",
    request_context: RequestSecurityContext | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> None:
    try:
        create_audit_log(
            db,
            user_id=user_id,
            organization_id=company_id,
            event_type=event_type,
            event_category=event_category,
            resource_type=target_type,
            resource_id=target_id,
            ip_address=request_context.ip_address if request_context else None,
            device_fingerprint=request_context.device_fingerprint if request_context else None,
            event_metadata=event_metadata,
        )
        event = AuditEvent(
            company_id=company_id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            description=description,
            target_type=target_type,
            target_id=target_id,
            event_metadata=_serialize_event_metadata(event_metadata),
        )
        db.add(event)
    except Exception:
        logger.exception("Failed to persist audit event type=%s target=%s:%s", event_type, target_type, target_id)
