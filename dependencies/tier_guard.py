from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.organization_membership import OrganizationMembership
from database.models.user import User
from services.security_service import extract_request_security_context, register_token_issue
from utils.auth_utils import decode_token_with_error, ensure_user_is_active
from utils.tier_limiter import has_remaining_scan_quota
from utils.api_errors import error_payload
from utils.rbac import (
    ROLE_ORG_ADMIN,
    ROLE_SECURITY_ADMIN,
    get_role_permissions,
    has_any_role,
    normalize_role,
)


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Missing or invalid token",
                error_code="invalid_token",
            ),
        )
    return auth_header.split(" ", 1)[1]


def _parse_subject_as_int(subject: str | None) -> int:
    try:
        return int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid authentication token",
                error_code="invalid_token",
            ),
        )


def _serialize_user_context(user: User) -> dict:
    effective_role = normalize_role(getattr(user, "role", None))
    permissions = get_role_permissions(effective_role)
    
    company = getattr(user, "company", None)
    
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "tier": getattr(user, "tier", "free"),
        "role": effective_role,
        "stored_role": getattr(user, "role", None),
        "company_id": user.company_id,
        "company_name": company.company_name if company else None,
        "is_superuser": getattr(user, "is_superuser", False),
        "permissions": {
            "can_access_admin": permissions.can_access_admin,
            "can_manage_users": permissions.can_manage_users,
            "can_view_audit_logs": permissions.can_view_audit_logs,
            "can_change_system_config": permissions.can_change_system_config,
            "can_access_security_dashboard": permissions.can_access_security_dashboard,
        },
    }


def _resolve_membership(db: Session, user: User) -> OrganizationMembership | None:
    if user.company_id is None:
        return None
    try:
        return (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.company_id == user.company_id,
                OrganizationMembership.user_id == user.id,
            )
            .first()
        )
    except SQLAlchemyError:
        db.rollback()
        return None


def get_current_user_context(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    api_key_context = getattr(request.state, "api_key_context", None)
    if api_key_context:
        user = db.query(User).filter(User.id == int(api_key_context["user_id"])).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail=error_payload(
                    detail="Invalid API key",
                    error_code="invalid_token",
                ),
            )
        ensure_user_is_active(user)
        membership = _resolve_membership(db, user)
        if membership and membership.status != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail=error_payload(
                    detail="Organization membership is not active",
                    error_code="forbidden",
                ),
            )
        request.state.user_id = user.id
        payload = _serialize_user_context(user)
        if membership:
            payload["role"] = normalize_role(membership.role)
            payload["stored_role"] = membership.role
            payload["membership_status"] = membership.status
        payload["auth_type"] = "api_key"
        payload["api_key_id"] = api_key_context["api_key_id"]
        return payload

    token = _extract_bearer_token(request)
    payload, decode_error = decode_token_with_error(token)
    if not payload:
        register_token_issue(
            db,
            organization_id=None,
            user_id=None,
            token_issue=decode_error or "invalid_token",
            context=extract_request_security_context(request),
        )
        db.commit()
        error_code = "expired_token" if decode_error == "expired_token" else "invalid_token"
        detail = "Token expired" if decode_error == "expired_token" else "Invalid authentication token"
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail=detail, error_code=error_code),
        )

    user_id = _parse_subject_as_int(payload.get("sub"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        register_token_issue(
            db,
            organization_id=None,
            user_id=user_id,
            token_issue="unknown_subject",
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Invalid authentication token",
                error_code="invalid_token",
            ),
        )
    if not user.is_active:
        register_token_issue(
            db,
            organization_id=user.company_id,
            user_id=user.id,
            token_issue="inactive_user",
            context=extract_request_security_context(request),
        )
        db.commit()
        ensure_user_is_active(user)
    membership = _resolve_membership(db, user)
    if membership and membership.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Organization membership is not active",
                error_code="forbidden",
            ),
        )
    request.state.user_id = user.id
    context_payload = _serialize_user_context(user)
    if membership:
        context_payload["role"] = normalize_role(membership.role)
        context_payload["stored_role"] = membership.role
        context_payload["membership_status"] = membership.status
    return context_payload


def enforce_tier_limit(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    allowed = has_remaining_scan_quota(db, current_user["user_id"], current_user["tier"])
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=error_payload(
                detail="Rate limit exceeded",
                error_code="rate_limit_exceeded",
            ),
        )
    return current_user


def require_company_admin(
    current_user: dict = Depends(get_current_user_context),
) -> dict:
    if not has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN):
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Admin role required",
                error_code="forbidden",
            ),
        )
    if current_user["company_id"] is None:
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Company context required",
                error_code="forbidden",
            ),
        )
    return current_user


def require_security_admin(
    current_user: dict = Depends(get_current_user_context),
) -> dict:
    if not has_any_role(current_user["role"], ROLE_SECURITY_ADMIN):
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Security admin role required",
                error_code="forbidden",
            ),
        )
    if current_user["company_id"] is None:
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Company context required",
                error_code="forbidden",
            ),
        )
    return current_user
