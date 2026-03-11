from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.employee import Employee
from database.models.user import User
from services.compliance_service import serialize_employee
from services.security_service import extract_request_security_context, register_token_issue
from utils.api_errors import error_payload
from utils.auth_utils import decode_token_with_error


EMPLOYEE_ADMIN_ROLES = {"security_admin", "compliance_admin", "organization_admin"}


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail="Missing or invalid token", error_code="invalid_token"),
        )
    return header.split(" ", 1)[1]


def require_employee_context(request: Request, db: Session = Depends(get_db)) -> dict:
    token = _extract_bearer_token(request)
    payload, error = decode_token_with_error(token)
    if not payload:
        register_token_issue(
            db,
            organization_id=None,
            user_id=None,
            token_issue=error or "invalid_token",
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail="Invalid authentication token", error_code=error or "invalid_token"),
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail="Invalid authentication token", error_code="invalid_token"),
        )
    user = db.query(User).filter(User.id == user_id).first()
    employee = db.query(Employee).filter(Employee.user_id == user_id, Employee.status == "active").first() if user else None
    if not user or not employee:
        raise HTTPException(
            status_code=403,
            detail=error_payload(detail="Employee access required", error_code="forbidden"),
        )
    request.state.user_id = user.id
    request.state.employee_id = employee.id
    return {
        "user_id": user.id,
        "employee_id": employee.id,
        "employee_role": employee.role,
        "email": employee.email,
        "organization_id": employee.company_id,
        "employee": serialize_employee(employee),
    }


def require_compliance_workspace_access(current_employee: dict = Depends(require_employee_context)) -> dict:
    if current_employee["employee_role"] not in EMPLOYEE_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail=error_payload(detail="Compliance workspace access required", error_code="forbidden"),
        )
    return current_employee


def require_security_or_compliance_admin(current_employee: dict = Depends(require_employee_context)) -> dict:
    if current_employee["employee_role"] not in {"security_admin", "compliance_admin"}:
        raise HTTPException(
            status_code=403,
            detail=error_payload(detail="Security or compliance admin role required", error_code="forbidden"),
        )
    return current_employee
