from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company import Company
from database.models.scan_results import ScanResult
from database.models.user import User
from dependencies.tier_guard import get_current_user_context, require_company_admin

router = APIRouter(prefix="/protected", tags=["Secure"])
companies_router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("/me")
def secure_area(
    current_user: dict = Depends(get_current_user_context),
):
    return {
        "message": "Secure area",
        "user_id": current_user["user_id"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "email": current_user["email"],
        "tier": current_user["tier"],
        "role": current_user["role"],
        "company_id": current_user["company_id"],
        "company_name": current_user["company_name"],
    }


@companies_router.get("/me")
def get_my_company(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    company_id = current_user["company_id"]
    if company_id is None:
        raise HTTPException(status_code=404, detail="Company not found for user")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

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
            }
            for user in users
        ],
    }


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
                "user_id": scan.user_id,
            }
            for scan in scans
        ],
    }
