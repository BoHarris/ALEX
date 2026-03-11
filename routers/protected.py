from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company import Company
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import get_current_user_context, require_company_admin, require_security_admin
from services.audit_service import record_audit_event
from services.retention_service import apply_retention_state_bulk
from services.security_service import extract_request_security_context
from utils.api_errors import error_payload
from utils.plan_features import get_plan_features
from utils.rbac import normalize_role

router = APIRouter(prefix="/protected", tags=["Secure"])
companies_router = APIRouter(prefix="/companies", tags=["Companies"])


class UserRoleUpdateRequest(BaseModel):
    role: str

@router.get("/me")
def secure_area(
    current_user: dict = Depends(get_current_user_context),
):
    plan = get_plan_features(current_user["tier"])
    return {
        "message": "Secure area",
        "user_id": current_user["user_id"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "email": current_user["email"],
        "tier": current_user["tier"],
        "role": current_user["role"],
        "stored_role": current_user.get("stored_role"),
        "company_id": current_user["company_id"],
        "company_name": current_user["company_name"],
        "permissions": current_user.get("permissions", {}),
        "plan_features": plan,
    }


@router.get("/plan")
def get_my_plan(
    current_user: dict = Depends(get_current_user_context),
):
    plan = get_plan_features(current_user["tier"])
    return {"plan": plan}


@companies_router.get("/me")
def get_my_company(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    if company_id is None:
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="Company not found for user",
                error_code="company_not_found",
            ),
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="Company not found",
                error_code="company_not_found",
            ),
        )

    return {
        "id": company.id,
        "company_name": company.company_name,
        "city": company.city,
        "state": company.state,
        "country": company.country,
        "industry": company.industry,
        "company_size": company.company_size,
        "subscription_tier": company.subscription_tier,
        "is_active": company.is_active,
        "is_verified": company.is_verified,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
    }


@companies_router.get("/me/users")
def get_my_company_users(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    users = (
        db.query(User)
        .filter(User.company_id == company_id)
        .order_by(User.id.asc())
        .all()
    )

    return {
        "company_id": company_id,
        "users": [
            {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "tier": user.tier,
                "role": user.role,
                "company_id": user.company_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            }
            for user in users
        ],
    }


@companies_router.put("/me/users/{target_user_id}/role")
def update_company_user_role(
    target_user_id: int,
    payload: UserRoleUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_security_admin),
    db: Session = Depends(get_db),
):
    target_user = (
        db.query(User)
        .filter(User.id == target_user_id, User.company_id == current_user["company_id"])
        .first()
    )
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="User not found",
                error_code="user_not_found",
            ),
        )

    normalized_role = normalize_role(payload.role)
    previous_role = normalize_role(target_user.role)
    target_user.role = normalized_role
    db.add(target_user)
    record_audit_event(
        db,
        company_id=current_user["company_id"],
        user_id=current_user["user_id"],
        event_type="user_role_changed",
        event_category="administration",
        description=f"Updated role for user {target_user.id}.",
        target_type="user",
        target_id=str(target_user.id),
        request_context=extract_request_security_context(request),
        event_metadata={"previous_role": previous_role, "new_role": normalized_role},
    )
    db.commit()
    return {"detail": "User role updated", "user_id": target_user.id, "role": normalized_role}


@companies_router.get("/me/scans")
def get_my_company_scans(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    scans = (
        db.query(ScanResult)
        .filter(ScanResult.company_id == company_id)
        .order_by(desc(ScanResult.scanned_at))
        .all()
    )
    scans = apply_retention_state_bulk(db, scans)

    return {
        "company_id": company_id,
        "scans": [
            {
                "scan_id": scan.id,
                "filename": scan.filename,
                "file_type": scan.file_type,
                "risk_score": scan.risk_score,
                "total_pii_found": scan.total_pii_found,
                "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
                "status": scan.status,
                "archived_at": scan.archived_at.isoformat() if scan.archived_at else None,
                "retention_expiration": scan.retention_expiration.isoformat() if scan.retention_expiration else None,
                "user_id": scan.user_id,
            }
            for scan in scans
        ],
    }
