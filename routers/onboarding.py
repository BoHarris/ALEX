from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import get_current_user_context
from services.audit_service import record_audit_event
from services.security_service import extract_request_security_context

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/status")
def onboarding_status(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    scan_count = db.query(ScanResult).filter(ScanResult.user_id == current_user["user_id"]).count()
    return {
        "has_completed_onboarding": bool(user.has_completed_onboarding) if user else False,
        "steps": {
            "upload_first_file": scan_count > 0,
            "run_scan": scan_count > 0,
            "view_redaction_report": bool(user.has_completed_onboarding) if user else False,
        },
    }


@router.post("/complete")
def complete_onboarding(
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user:
        user.has_completed_onboarding = True
        db.add(user)
        record_audit_event(
            db,
            company_id=user.company_id,
            user_id=user.id,
            event_type="onboarding_completed",
            event_category="product",
            description="User completed onboarding.",
            target_type="user",
            target_id=str(user.id),
            request_context=extract_request_security_context(request),
        )
        db.commit()
    return {"has_completed_onboarding": True}
