from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from utils.auth_utils import decode_token


VALID_TENANT_ROLES = {"admin", "member"}


def _normalize_tenant_role(role_value: str | None) -> str:
    role = (role_value or "").strip().lower()
    if role not in VALID_TENANT_ROLES:
        return "member"
    return role


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return auth_header.split(" ", 1)[1]


def _serialize_user_context(user: User) -> dict:
    role = _normalize_tenant_role(getattr(user, "role", None))
    
    company = getattr(user, "company", None)
    
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "tier": getattr(user, "tier", "free"),
        "role": role,
        "company_id": user.company_id,
        "company_name": company.company_name if company else None,
        "is_superuser": getattr(user, "is_superuser", False)
    }


def get_current_user_context(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    token = _extract_bearer_token(request)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _serialize_user_context(user)


def enforce_tier_limit(
    current_user: dict = Depends(get_current_user_context),
):
    # allowed = check_scan_allowed(current_user["user_id"], current_user["tier"])
    # if not allowed:
    #     raise HTTPException(status_code=403, detail="Daily scan limit reached")
    return current_user


def require_company_admin(
    current_user: dict = Depends(get_current_user_context),
) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if current_user["company_id"] is None:
        raise HTTPException(status_code=403, detail="Company context required")
    return current_user
