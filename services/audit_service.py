from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from database.models.audit_event import AuditEvent
from services.security_service import RequestSecurityContext, create_audit_log

logger = logging.getLogger(__name__)


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
            description=description,
            target_type=target_type,
            target_id=target_id,
        )
        db.add(event)
    except Exception:
        logger.exception("Failed to persist audit event type=%s target=%s:%s", event_type, target_type, target_id)
