from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from database.models.security_event import SecurityEvent
from database.models.security_incident import SecurityIncident
from dependencies.tier_guard import require_company_admin, require_security_admin
from services.audit_service import list_audit_events as query_audit_events, record_audit_event, serialize_audit_event
from services.governance_task_service import list_source_tasks
from services.retention_service import apply_retention_state_bulk
from services.security_service import extract_request_security_context
from utils.api_errors import error_payload
from utils.plan_features import get_plan_features

router = APIRouter(prefix="/admin", tags=["Admin"])


class CompanySettingsUpdateRequest(BaseModel):
    default_policy_label: str | None = None
    default_report_display_name: str | None = None
    allowed_upload_types: list[str] | None = None
    contact_email: str | None = None
    compliance_mode: str | None = None
    branding_primary_color: str | None = None
    retention_days_display: int | None = Field(default=None, ge=1, le=3650)
    retention_days: int | None = Field(default=None, ge=1, le=3650)


def _get_company_or_404(db: Session, company_id: int) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="Company not found",
                error_code="company_not_found",
            ),
        )
    return company


def _parse_type_counts(value: str | None) -> dict[str, int]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    parsed: dict[str, int] = {}
    for key, raw_count in decoded.items():
        try:
            parsed[str(key)] = int(raw_count)
        except (TypeError, ValueError):
            continue
    return parsed


def _ensure_feature_enabled(features: dict, feature_key: str, detail: str) -> None:
    if not features.get(feature_key, False):
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail=detail,
                error_code="feature_locked",
            ),
        )


@router.get("/overview")
def get_admin_overview(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    features = get_plan_features(current_user.get("tier"))

    now_utc = datetime.utcnow()
    week_start = now_utc - timedelta(days=7)
    trend_start = now_utc - timedelta(days=30)

    total_scans = db.query(func.count(ScanResult.id)).filter(ScanResult.company_id == company_id).scalar() or 0
    scans_this_week = (
        db.query(func.count(ScanResult.id))
        .filter(ScanResult.company_id == company_id, ScanResult.scanned_at >= week_start)
        .scalar()
        or 0
    )
    high_risk_scans = (
        db.query(func.count(ScanResult.id))
        .filter(ScanResult.company_id == company_id, ScanResult.risk_score >= 70)
        .scalar()
        or 0
    )
    recent_scans = (
        db.query(ScanResult)
        .filter(ScanResult.company_id == company_id)
        .order_by(ScanResult.scanned_at.desc())
        .limit(10)
        .all()
    )
    recent_scans = apply_retention_state_bulk(db, recent_scans)

    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    file_type_distribution: dict[str, int] = {}
    redaction_type_totals: dict[str, int] = {}
    scans_over_time: dict[str, int] = {}

    if features.get("admin_analytics"):
        analytic_scans = (
            db.query(ScanResult)
            .filter(ScanResult.company_id == company_id, ScanResult.scanned_at >= trend_start)
            .all()
        )
        for scan in analytic_scans:
            risk = scan.risk_score or 0
            if risk >= 70:
                risk_distribution["high"] += 1
            elif risk >= 40:
                risk_distribution["medium"] += 1
            else:
                risk_distribution["low"] += 1

            file_type = (scan.file_type or "unknown").lower()
            file_type_distribution[file_type] = file_type_distribution.get(file_type, 0) + 1

            for label, count in _parse_type_counts(scan.redacted_type_counts).items():
                redaction_type_totals[label] = redaction_type_totals.get(label, 0) + count

            if scan.scanned_at:
                day_key = scan.scanned_at.date().isoformat()
                scans_over_time[day_key] = scans_over_time.get(day_key, 0) + 1

    report_activity = {
        "html_reports_downloaded": (
            db.query(func.count(AuditLog.id))
            .filter(AuditLog.organization_id == company_id, AuditLog.event_type == "report_html_downloaded")
            .scalar()
            or 0
        ),
        "pdf_reports_downloaded": (
            db.query(func.count(AuditLog.id))
            .filter(AuditLog.organization_id == company_id, AuditLog.event_type == "report_pdf_downloaded")
            .scalar()
            or 0
        ),
        "redacted_files_downloaded": (
            db.query(func.count(AuditLog.id))
            .filter(AuditLog.organization_id == company_id, AuditLog.event_type == "redacted_file_downloaded")
            .scalar()
            or 0
        ),
    }

    recent_activity = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == company_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    record_audit_event(
        db,
        company_id=company_id,
        user_id=current_user["user_id"],
        event_type="admin_overview_accessed",
        event_category="administration",
        description="Admin overview was accessed.",
        target_type="admin",
        target_id=str(current_user["user_id"]),
    )
    db.commit()

    return {
        "summary": {
            "total_scans": total_scans,
            "scans_this_week": scans_this_week,
            "high_risk_scans": high_risk_scans,
            "report_activity": report_activity,
        },
        "analytics_enabled": features.get("admin_analytics", False),
        "plan": features["tier"],
        "risk_distribution": risk_distribution,
        "file_type_distribution": file_type_distribution,
        "top_redacted_types": sorted(
            [{"type": label, "count": count} for label, count in redaction_type_totals.items()],
            key=lambda item: item["count"],
            reverse=True,
        )[:8],
        "scans_over_time": [
            {"date": day, "count": scans_over_time[day]}
            for day in sorted(scans_over_time.keys())
        ],
        "recent_scans": [
            {
                "scan_id": scan.id,
                "filename": scan.filename,
                "risk_score": scan.risk_score,
                "file_type": scan.file_type,
                "total_pii_found": scan.total_pii_found,
                "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            }
            for scan in recent_scans
        ],
        "recent_activity": [
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "description": event.event_metadata or event.event_category,
                "target_type": event.resource_type,
                "target_id": event.resource_id,
                "user_id": event.user_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in recent_activity
        ],
    }


@router.get("/audit-events")
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    user_id: int | None = Query(default=None),
    scan_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    features = get_plan_features(current_user.get("tier"))
    _ensure_feature_enabled(
        features,
        "audit_visibility",
        "Audit trail visibility is available on Pro and Business plans.",
    )

    events = query_audit_events(
        db,
        company_id=company_id,
        limit=limit,
        user_id=user_id,
        scan_id=scan_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "events": [serialize_audit_event(event) for event in events]
    }


@router.get("/company-settings")
def get_company_settings(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    _get_company_or_404(db, company_id)
    features = get_plan_features(current_user.get("tier"))
    _ensure_feature_enabled(
        features,
        "company_settings",
        "Company settings are available on Pro and Business plans.",
    )

    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        return {
            "company_id": company_id,
            "default_policy_label": None,
            "default_report_display_name": None,
            "allowed_upload_types": [],
            "contact_email": None,
            "compliance_mode": None,
            "branding_primary_color": None,
            "retention_days_display": None,
            "retention_days": None,
        }

    return {
        "company_id": settings.company_id,
        "default_policy_label": settings.default_policy_label,
        "default_report_display_name": settings.default_report_display_name,
        "allowed_upload_types": json.loads(settings.allowed_upload_types) if settings.allowed_upload_types else [],
        "contact_email": settings.contact_email,
        "compliance_mode": settings.compliance_mode,
        "branding_primary_color": settings.branding_primary_color,
        "retention_days_display": settings.retention_days_display,
        "retention_days": settings.retention_days,
    }


@router.put("/company-settings")
def update_company_settings(
    payload: CompanySettingsUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    _get_company_or_404(db, company_id)
    features = get_plan_features(current_user.get("tier"))
    _ensure_feature_enabled(
        features,
        "company_settings",
        "Company settings are available on Pro and Business plans.",
    )

    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        settings = CompanySettings(company_id=company_id)
        db.add(settings)

    settings.default_policy_label = payload.default_policy_label
    settings.default_report_display_name = payload.default_report_display_name
    settings.allowed_upload_types = json.dumps(payload.allowed_upload_types or [])
    settings.contact_email = payload.contact_email
    settings.compliance_mode = payload.compliance_mode
    settings.branding_primary_color = payload.branding_primary_color
    settings.retention_days_display = payload.retention_days_display
    settings.retention_days = payload.retention_days
    settings.require_storage_encryption = "true"
    settings.secure_cookie_enforced = "true"
    db.commit()
    db.refresh(settings)

    record_audit_event(
        db,
        company_id=company_id,
        user_id=current_user["user_id"],
        event_type="company_settings_updated",
        event_category="administration",
        description="Company settings were updated.",
        target_type="company_settings",
        target_id=str(settings.id),
        request_context=extract_request_security_context(request),
        event_metadata={
            "retention_days": settings.retention_days,
            "retention_days_display": settings.retention_days_display,
        },
    )
    db.commit()

    return {
        "detail": "Company settings updated",
        "company_id": settings.company_id,
    }


@router.get("/security-dashboard")
def get_security_dashboard(
    current_user: dict = Depends(require_security_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    recent_audit_events = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == company_id)
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    recent_alerts = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.company_id == company_id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(25)
        .all()
    )
    recent_scans = apply_retention_state_bulk(
        db,
        db.query(ScanResult).filter(ScanResult.company_id == company_id).order_by(ScanResult.scanned_at.desc()).limit(100).all(),
    )
    incidents = (
        db.query(SecurityIncident)
        .order_by(SecurityIncident.detected_at.desc())
        .limit(25)
        .all()
    )
    failed_login_attempts = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.organization_id == company_id, AuditLog.event_type == "login_failure")
        .scalar()
        or 0
    )
    retention_overview = {
        "active": sum(1 for scan in recent_scans if scan.status == "active"),
        "archived": sum(1 for scan in recent_scans if scan.status == "archived"),
        "expired": sum(1 for scan in recent_scans if scan.status == "expired"),
    }
    scan_activity_trend: dict[str, int] = {}
    for scan in recent_scans:
        if scan.scanned_at:
            key = scan.scanned_at.date().isoformat()
            scan_activity_trend[key] = scan_activity_trend.get(key, 0) + 1

    return {
        "recent_audit_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_category": event.event_category,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in recent_audit_events
        ],
        "recent_security_alerts": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_label": event.event_type.replace("_", " ").title(),
                "description": event.description,
                "metadata": event.event_metadata,
                "ip_address": event.ip_address,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "linked_tasks": list_source_tasks(db, company_id=company_id, source_type="security_alert", source_id=str(event.id)),
            }
            for event in recent_alerts
        ],
        "failed_login_attempts": failed_login_attempts,
        "scan_activity_trend": [
            {"date": day, "count": scan_activity_trend[day]}
            for day in sorted(scan_activity_trend.keys())
        ],
        "retention_overview": retention_overview,
        "incidents": [
            {
                "id": incident.id,
                "severity": incident.severity,
                "status": incident.status,
                "description": incident.description,
                "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "resolution_notes": incident.resolution_notes,
            }
            for incident in incidents
        ],
    }


@router.get("/incidents")
def list_security_incidents(
    current_user: dict = Depends(require_security_admin),
    db: Session = Depends(get_db),
):
    incidents = db.query(SecurityIncident).order_by(SecurityIncident.detected_at.desc()).all()
    return {
        "incidents": [
            {
                "id": incident.id,
                "severity": incident.severity,
                "status": incident.status,
                "description": incident.description,
                "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "resolution_notes": incident.resolution_notes,
            }
            for incident in incidents
        ]
    }
