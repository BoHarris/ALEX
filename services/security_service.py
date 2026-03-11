from __future__ import annotations

import json
import logging
import os
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.models.audit_log import AuditLog
from database.models.security_incident import SecurityIncident
from services.security_state_store import (
    SecurityStateStoreError,
    increment_counter,
    register_distinct_member,
)
from utils.api_errors import error_payload

logger = logging.getLogger(__name__)

FAILED_LOGIN_ALERT_THRESHOLD = int(os.getenv("FAILED_LOGIN_ALERT_THRESHOLD", "5"))
FAILED_LOGIN_WINDOW_MINUTES = int(os.getenv("FAILED_LOGIN_WINDOW_MINUTES", "15"))
SCAN_ALERT_THRESHOLD = int(os.getenv("SCAN_ALERT_THRESHOLD", "20"))
SCAN_ALERT_WINDOW_MINUTES = int(os.getenv("SCAN_ALERT_WINDOW_MINUTES", "10"))
TOKEN_ALERT_THRESHOLD = int(os.getenv("TOKEN_ALERT_THRESHOLD", "5"))
UNUSUAL_IP_THRESHOLD = int(os.getenv("UNUSUAL_IP_THRESHOLD", "5"))

FAILED_LOGIN_WINDOW_SECONDS = FAILED_LOGIN_WINDOW_MINUTES * 60
SCAN_ALERT_WINDOW_SECONDS = SCAN_ALERT_WINDOW_MINUTES * 60


@dataclass(frozen=True)
class RequestSecurityContext:
    ip_address: str | None = None
    device_fingerprint: str | None = None
    user_agent: str | None = None
    advisory_ip_address: str | None = None
    trusted_proxy: bool = False
    session_binding_hash: str | None = None
    request_id: str | None = None


TRUST_PROXY_HEADERS = (os.getenv("TRUST_PROXY_HEADERS") or "false").strip().lower() == "true"
TRUSTED_PROXY_IPS = {
    value.strip()
    for value in (os.getenv("TRUSTED_PROXY_IPS") or "").split(",")
    if value.strip()
}


def _normalize_header_value(value: str | None, *, max_length: int = 512) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    return normalized[:max_length]


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request_peer_ip(request) -> str | None:
    if getattr(request, "client", None) and getattr(request.client, "host", None):
        return request.client.host
    return None


def _trusted_forwarded_ip(headers, *, peer_ip: str | None) -> tuple[str | None, bool, str | None]:
    forwarded_for = _normalize_header_value(headers.get("x-forwarded-for"), max_length=256)
    if not forwarded_for:
        return peer_ip, False, None

    advisory_ip = forwarded_for.split(",", 1)[0].strip() or None
    if not advisory_ip:
        return peer_ip, False, None

    proxy_trusted = TRUST_PROXY_HEADERS or (peer_ip is not None and peer_ip in TRUSTED_PROXY_IPS)
    if not proxy_trusted:
        return peer_ip, False, advisory_ip

    return advisory_ip, True, advisory_ip


def build_session_binding_hash(
    *,
    user_agent: str | None,
    advisory_device_fingerprint: str | None,
) -> str | None:
    normalized_user_agent = _normalize_header_value(user_agent)
    normalized_device_fingerprint = _normalize_header_value(advisory_device_fingerprint, max_length=256)
    binding_parts = [
        part
        for part in (normalized_user_agent, normalized_device_fingerprint)
        if part
    ]
    if not binding_parts:
        return None
    return _hash_value("|".join(binding_parts))


def extract_request_security_context(request) -> RequestSecurityContext:
    headers = getattr(request, "headers", {}) or {}
    peer_ip = _request_peer_ip(request)
    ip_address, trusted_proxy, advisory_ip = _trusted_forwarded_ip(headers, peer_ip=peer_ip)
    user_agent = _normalize_header_value(headers.get("user-agent"))
    advisory_device_fingerprint = _normalize_header_value(headers.get("x-device-fingerprint"), max_length=256)
    device_fingerprint = _hash_value(advisory_device_fingerprint)
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    return RequestSecurityContext(
        ip_address=ip_address,
        device_fingerprint=device_fingerprint,
        user_agent=user_agent,
        advisory_ip_address=advisory_ip,
        trusted_proxy=trusted_proxy,
        session_binding_hash=build_session_binding_hash(
            user_agent=user_agent,
            advisory_device_fingerprint=advisory_device_fingerprint,
        ),
        request_id=request_id,
    )


def _serialize_metadata(event_metadata: dict | None) -> str | None:
    if not event_metadata:
        return None
    try:
        return json.dumps(event_metadata, sort_keys=True, default=str)
    except Exception:
        logger.exception("Failed to serialize audit metadata")
        return None


def create_audit_log(
    db: Session,
    *,
    user_id: int | None,
    organization_id: int | None,
    event_type: str,
    event_category: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    device_fingerprint: str | None = None,
    event_metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            event_type=event_type,
            event_category=event_category,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            event_metadata=_serialize_metadata(event_metadata),
        )
    )


def create_security_incident(
    db: Session,
    *,
    severity: str,
    description: str,
    status: str = "open",
    resolution_notes: str | None = None,
) -> SecurityIncident:
    incident = SecurityIncident(
        severity=severity,
        description=description,
        status=status,
        resolution_notes=resolution_notes,
    )
    db.add(incident)
    return incident


def _hash_state_identifier(value: str | None) -> str | None:
    normalized = _normalize_header_value(value, max_length=256)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _increment_threshold_counter(
    db: Session,
    *,
    namespace: str,
    state_key: str,
    threshold: int,
    window_seconds: int,
) -> bool:
    count = increment_counter(
        db,
        namespace=namespace,
        state_key=state_key,
        window_seconds=window_seconds,
    )
    return count >= threshold


def _track_ip_identity(
    db: Session,
    *,
    ip_address: str | None,
    identity: str | None,
) -> bool:
    if not ip_address or not identity:
        return False
    ip_key = _hash_state_identifier(ip_address)
    identity_key = _hash_state_identifier(identity)
    if not ip_key or not identity_key:
        return False
    distinct_count = register_distinct_member(
        db,
        namespace="security:ip_identity",
        owner_key=ip_key,
        member_key=identity_key,
        window_seconds=FAILED_LOGIN_WINDOW_SECONDS,
    )
    return distinct_count >= UNUSUAL_IP_THRESHOLD


def raise_security_alert(
    db: Session,
    *,
    organization_id: int | None,
    user_id: int | None,
    alert_type: str,
    description: str,
    context: RequestSecurityContext | None = None,
    metadata: dict | None = None,
    severity: str | None = None,
    escalate_to_incident: bool = False,
) -> None:
    payload = {"severity": severity or "medium", **(metadata or {})}
    create_audit_log(
        db,
        user_id=user_id,
        organization_id=organization_id,
        event_type=alert_type,
        event_category="security_alert",
        resource_type="security_alert",
        resource_id=None,
        ip_address=context.ip_address if context else None,
        device_fingerprint=context.device_fingerprint if context else None,
        event_metadata=payload,
    )
    if escalate_to_incident:
        create_security_incident(
            db,
            severity=severity or "medium",
            description=description,
        )


def register_failed_login(
    db: Session,
    *,
    email: str,
    organization_id: int | None,
    user_id: int | None,
    context: RequestSecurityContext,
) -> bool:
    key = email.strip().lower() or (context.ip_address or "unknown")
    try:
        threshold_hit = _increment_threshold_counter(
            db,
            namespace="security:failed_login",
            state_key=_hash_state_identifier(key) or "unknown",
            threshold=FAILED_LOGIN_ALERT_THRESHOLD,
            window_seconds=FAILED_LOGIN_WINDOW_SECONDS,
        )
        unusual_ip = _track_ip_identity(
            db,
            ip_address=context.ip_address,
            identity=key,
        )
    except SecurityStateStoreError:
        logger.exception("Shared security state store unavailable during failed-login tracking.")
        raise
    if threshold_hit or unusual_ip:
        raise_security_alert(
            db,
            organization_id=organization_id,
            user_id=user_id,
            alert_type="suspicious_login",
            description="Repeated failed login attempts detected.",
            context=context,
            metadata={"identifier": key, "alert_reason": "failed_login_threshold"},
            severity="high" if threshold_hit else "medium",
            escalate_to_incident=threshold_hit,
        )
        return True
    return False


def enforce_auth_rate_limit(
    db: Session,
    *,
    request,
    identifier: str | None = None,
    per_ip_limit: int,
    per_identifier_limit: int,
    window_seconds: int,
) -> None:
    context = extract_request_security_context(request)
    key_values = [("ip", context.ip_address or "unknown", per_ip_limit)]
    if identifier:
        key_values.append(("id", identifier.strip().lower(), per_identifier_limit))

    try:
        for scope, raw_key, threshold in key_values:
            threshold_hit = _increment_threshold_counter(
                db,
                namespace=f"security:auth_ratelimit:{scope}",
                state_key=_hash_state_identifier(raw_key) or "unknown",
                threshold=threshold,
                window_seconds=window_seconds,
            )
            if threshold_hit:
                raise HTTPException(
                    status_code=429,
                    detail=error_payload(
                        detail="Rate limit exceeded",
                        error_code="rate_limit_exceeded",
                    ),
                )
    except SecurityStateStoreError as exc:
        logger.exception("Shared security state store unavailable during auth rate limiting.")
        raise HTTPException(
            status_code=503,
            detail=error_payload(
                detail="Authentication security controls are temporarily unavailable.",
                error_code="security_state_unavailable",
            ),
        ) from exc


def register_scan_activity(
    db: Session,
    *,
    organization_id: int | None,
    user_id: int | None,
    context: RequestSecurityContext,
) -> bool:
    key = str(user_id or context.ip_address or "anonymous")
    try:
        threshold_hit = _increment_threshold_counter(
            db,
            namespace="security:scan_activity",
            state_key=_hash_state_identifier(key) or "anonymous",
            threshold=SCAN_ALERT_THRESHOLD,
            window_seconds=SCAN_ALERT_WINDOW_SECONDS,
        )
    except SecurityStateStoreError:
        logger.exception("Shared security state store unavailable during scan-activity tracking.")
        raise
    if threshold_hit:
        raise_security_alert(
            db,
            organization_id=organization_id,
            user_id=user_id,
            alert_type="excessive_scan_attempts",
            description="High-frequency scanning detected.",
            context=context,
            metadata={"identifier": key},
            severity="medium",
        )
        return True
    return False


def register_token_issue(
    db: Session,
    *,
    organization_id: int | None,
    user_id: int | None,
    token_issue: str,
    context: RequestSecurityContext,
) -> bool:
    key = f"{user_id or 'anonymous'}:{token_issue}"
    try:
        threshold_hit = _increment_threshold_counter(
            db,
            namespace="security:token_issue",
            state_key=_hash_state_identifier(key) or "anonymous",
            threshold=TOKEN_ALERT_THRESHOLD,
            window_seconds=FAILED_LOGIN_WINDOW_SECONDS,
        )
    except SecurityStateStoreError:
        logger.exception("Shared security state store unavailable during token-issue tracking.")
        raise
    if threshold_hit:
        raise_security_alert(
            db,
            organization_id=organization_id,
            user_id=user_id,
            alert_type="token_abuse",
            description="Repeated invalid or revoked token activity detected.",
            context=context,
            metadata={"token_issue": token_issue},
            severity="high",
            escalate_to_incident=True,
        )
        return True
    return False
