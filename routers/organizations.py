from __future__ import annotations

import io
import json
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.organization_membership import OrganizationMembership
from database.models.scan_results import ScanResult
from database.models.security_event import SecurityEvent
from database.models.user import User
from dependencies.tier_guard import get_current_user_context, require_company_admin
from services.audit_service import parse_audit_event_metadata, record_audit_event
from services.refresh_session_service import revoke_all_user_sessions
from services.security_service import extract_request_security_context
from utils.api_errors import error_payload
from utils.report_cache import cache_html_report, cache_pdf_report

router = APIRouter(prefix="/organizations", tags=["Organizations"])


class InviteUserRequest(BaseModel):
    email: str
    role: str


class OrganizationUserActionRequest(BaseModel):
    user_id: int


def _require_matching_company(organization_id: int, current_user: dict) -> None:
    if current_user["company_id"] != organization_id:
        raise HTTPException(
            status_code=403,
            detail=error_payload(detail="Not authorized for this organization", error_code="forbidden"),
        )


@router.post("/{organization_id}/invite")
def invite_user_to_organization(
    organization_id: int,
    payload: InviteUserRequest,
    request: Request,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    _require_matching_company(organization_id, current_user)
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="User account not found", error_code="user_not_found"),
        )
    if user.company_id not in {None, organization_id}:
        raise HTTPException(
            status_code=409,
            detail=error_payload(detail="User already belongs to another organization", error_code="conflict"),
        )

    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.company_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
        .first()
    )
    if membership is None:
        membership = OrganizationMembership(
            company_id=organization_id,
            user_id=user.id,
            role=payload.role,
            status="INVITED",
            invited_by=current_user["user_id"],
        )
    else:
        membership.role = payload.role
        membership.status = "INVITED"
        membership.invited_by = current_user["user_id"]
    db.add(membership)
    record_audit_event(
        db,
        company_id=organization_id,
        user_id=current_user["user_id"],
        event_type="organization_invite_created",
        event_category="administration",
        description=f"Invited user {user.id} to organization {organization_id}.",
        target_type="organization_membership",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
        event_metadata={"role": payload.role, "email": user.email},
    )
    db.commit()
    db.refresh(membership)
    return {
        "membership_id": membership.id,
        "user_id": user.id,
        "email": user.email,
        "role": membership.role,
        "status": membership.status,
    }


@router.post("/{organization_id}/accept-invite")
def accept_organization_invite(
    organization_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.company_id == organization_id,
            OrganizationMembership.user_id == current_user["user_id"],
        )
        .first()
    )
    if not membership or membership.status != "INVITED":
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Invite not found", error_code="not_found"),
        )

    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="User not found", error_code="user_not_found"),
        )
    if user.company_id not in {None, organization_id}:
        raise HTTPException(
            status_code=409,
            detail=error_payload(detail="User already belongs to another organization", error_code="conflict"),
        )

    membership.status = "ACTIVE"
    user.company_id = organization_id
    user.role = membership.role
    user.is_active = True
    db.add(membership)
    db.add(user)
    record_audit_event(
        db,
        company_id=organization_id,
        user_id=user.id,
        event_type="organization_invite_accepted",
        event_category="administration",
        description=f"User {user.id} accepted an organization invite.",
        target_type="organization_membership",
        target_id=str(membership.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"organization_id": organization_id, "status": membership.status, "role": membership.role}


@router.post("/{organization_id}/suspend-user")
def suspend_organization_user(
    organization_id: int,
    payload: OrganizationUserActionRequest,
    request: Request,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    _require_matching_company(organization_id, current_user)
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.company_id == organization_id,
            OrganizationMembership.user_id == payload.user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Membership not found", error_code="not_found"),
        )
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="User not found", error_code="user_not_found"),
        )

    membership.status = "SUSPENDED"
    user.is_active = False
    db.add(membership)
    db.add(user)
    revoke_all_user_sessions(db, user_id=user.id)
    record_audit_event(
        db,
        company_id=organization_id,
        user_id=current_user["user_id"],
        event_type="organization_user_suspended",
        event_category="administration",
        description=f"Suspended user {user.id} from organization {organization_id}.",
        target_type="user",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"user_id": user.id, "status": membership.status}


@router.post("/{organization_id}/remove-user")
def remove_organization_user(
    organization_id: int,
    payload: OrganizationUserActionRequest,
    request: Request,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    _require_matching_company(organization_id, current_user)
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.company_id == organization_id,
            OrganizationMembership.user_id == payload.user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Membership not found", error_code="not_found"),
        )
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="User not found", error_code="user_not_found"),
        )

    membership.status = "REMOVED"
    user.company_id = None
    user.role = "member"
    user.is_active = True
    db.add(membership)
    db.add(user)
    revoke_all_user_sessions(db, user_id=user.id)
    record_audit_event(
        db,
        company_id=organization_id,
        user_id=current_user["user_id"],
        event_type="organization_user_removed",
        event_category="administration",
        description=f"Removed user {user.id} from organization {organization_id}.",
        target_type="user",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"user_id": user.id, "status": membership.status}


@router.get("/{organization_id}/audit-export")
def download_audit_export(
    organization_id: int,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    _require_matching_company(organization_id, current_user)
    company = db.query(Company).filter(Company.id == organization_id).first()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Organization not found", error_code="not_found"),
        )

    scans = db.query(ScanResult).filter(ScanResult.company_id == organization_id).order_by(ScanResult.scanned_at.desc()).all()
    audit_events = db.query(AuditEvent).filter(AuditEvent.company_id == organization_id).order_by(AuditEvent.created_at.desc()).all()
    audit_logs = db.query(AuditLog).filter(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc()).all()
    security_events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.company_id == organization_id)
        .order_by(SecurityEvent.created_at.desc())
        .all()
    )

    scan_summary = [
        {
            "scan_id": scan.id,
            "filename": scan.filename,
            "file_type": scan.file_type,
            "risk_score": scan.risk_score,
            "total_pii_found": scan.total_pii_found,
            "status": scan.status,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            "report_html_path": scan.report_html_path,
            "report_pdf_path": scan.report_pdf_path,
        }
        for scan in scans
    ]
    audit_payload = {
        "organization": {"id": company.id, "name": company.company_name},
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_category": event.event_category,
                "description": event.description,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "metadata": parse_audit_event_metadata(event.event_metadata),
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in audit_events
        ],
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in audit_logs
        ],
        "security_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "description": event.description,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in security_events
        ],
    }

    report_metadata = []
    export_buffer = io.BytesIO()
    with zipfile.ZipFile(export_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scan_summary.json", json.dumps(scan_summary, indent=2))
        archive.writestr("audit_events.json", json.dumps(audit_payload, indent=2))

        for scan in scans:
            html_path = cache_html_report(db, scan)
            report_metadata.append(
                {
                    "scan_id": scan.id,
                    "html_report": html_path.name,
                    "pdf_report": None,
                }
            )
            archive.write(html_path, arcname=f"reports/{html_path.name}")
            try:
                pdf_path = cache_pdf_report(db, scan)
            except RuntimeError:
                continue
            report_metadata[-1]["pdf_report"] = pdf_path.name
            archive.write(pdf_path, arcname=f"reports/{pdf_path.name}")

        archive.writestr("report_metadata.json", json.dumps(report_metadata, indent=2))

    export_buffer.seek(0)
    return Response(
        content=export_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="organization-{organization_id}-audit-export.zip"'},
    )
