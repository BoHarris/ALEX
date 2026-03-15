import os
import secrets
import dataclasses
from datetime import timedelta, datetime, timezone
from enum import Enum

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company import Company
from database.models.employee import Employee
from database.models.pending_registration import PendingRegistration
from database.models.user import User
from database.models.webauthn_challenge import WebAuthnChallenge
from services.audit_service import record_audit_event
from services.compliance_service import ensure_default_company_and_employee
from services.refresh_session_service import issue_bound_refresh_token
from services.security_service import enforce_auth_rate_limit, extract_request_security_context, register_failed_login
from utils.auth_utils import create_access_token, ensure_user_is_active
from utils.api_errors import error_payload
from utils.rbac import ROLE_ORG_ADMIN, ROLE_USER, normalize_role

from webauthn import (
    generate_registration_options,
    generate_authentication_options,
    verify_registration_response,
    verify_authentication_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_TTL = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
CHALLENGE_TTL_MINUTES = int(os.getenv("CHALLENGE_TTL_MINUTES", "5"))

RP_ID = os.getenv("RP_ID", "localhost")
RP_NAME = os.getenv("RP_NAME", "ALEX")
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")
IS_PROD = os.getenv("ENV", "development").lower() == "production"
AUTH_RATE_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_WINDOW_SECONDS", "60"))
AUTH_RATE_LIMIT_PER_IP = int(os.getenv("AUTH_RATE_LIMIT_PER_IP", "30"))
AUTH_RATE_LIMIT_PER_IDENTIFIER = int(os.getenv("AUTH_RATE_LIMIT_PER_IDENTIFIER", "10"))



class WebAuthnRegisterOptionsRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    company_name: str | None = None
    create_company: bool = False


class WebAuthnLoginOptionsRequest(BaseModel):
    email: str


class WebAuthnRegisterVerifyRequest(BaseModel):
    user_id: int
    credential: dict


class WebAuthnLoginVerifyRequest(BaseModel):
    email: str
    credential: dict


class EmployeeWebAuthnRegisterOptionsRequest(BaseModel):
    email: str


class EmployeeWebAuthnStatusRequest(BaseModel):
    email: str


class EmployeeWebAuthnRegisterVerifyRequest(BaseModel):
    email: str
    credential: dict


def _enforce_auth_rate_limit(
    *,
    db: Session,
    request: Request,
    identifier: str | None = None,
) -> None:
    enforce_auth_rate_limit(
        db,
        request=request,
        identifier=identifier,
        per_ip_limit=AUTH_RATE_LIMIT_PER_IP,
        per_identifier_limit=AUTH_RATE_LIMIT_PER_IDENTIFIER,
        window_seconds=AUTH_RATE_WINDOW_SECONDS,
    )


def _new_user_handle() -> str:
    return bytes_to_base64url(secrets.token_bytes(32))


def _camelize_key(key: str) -> str:
    parts = key.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _serialize_webauthn_value(value):
    if isinstance(value, bytes):
        return bytes_to_base64url(value)
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value):
        return _serialize_webauthn_value(dataclasses.asdict(value))
    if isinstance(value, list):
        return [_serialize_webauthn_value(item) for item in value]
    if isinstance(value, dict):
        return {
            _camelize_key(key): _serialize_webauthn_value(item)
            for key, item in value.items()
            if item is not None
        }
    if hasattr(value, "model_dump"):
        return _serialize_webauthn_value(value.model_dump())
    return value

def _store_challenge(db: Session, user_id: int, challenge: str, challenge_type: str) -> None:
    _cleanup_expired_challenges(db)
    db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.user_id == user_id,
        WebAuthnChallenge.challenge_type == challenge_type,
    ).delete()
    
    record = WebAuthnChallenge(
        user_id=user_id,
        challenge=challenge,
        challenge_type=challenge_type,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=CHALLENGE_TTL_MINUTES),
    )
    db.add(record)
    db.commit()


def _cleanup_expired_pending_registrations(db: Session, limit: int = 200) -> int:
    now_utc = datetime.now(timezone.utc)
    expired_candidates = (
        db.query(PendingRegistration)
        .order_by(PendingRegistration.expires_at.asc())
        .limit(limit)
        .all()
    )
    deleted = 0
    for record in expired_candidates:
        expires_at = record.expires_at
        now = now_utc.replace(tzinfo=None) if expires_at.tzinfo is None else now_utc
        if expires_at <= now:
            db.delete(record)
            deleted += 1
    if deleted:
        db.commit()
    return deleted


def _cleanup_expired_challenges(db: Session, limit: int = 200) -> int:
    now_utc = datetime.now(timezone.utc)
    expired_candidates = (
        db.query(WebAuthnChallenge)
        .order_by(WebAuthnChallenge.expires_at.asc())
        .limit(limit)
        .all()
    )
    deleted = 0
    for record in expired_candidates:
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            now = now_utc.replace(tzinfo=None)
        else:
            now = now_utc
        if expires_at <= now:
            db.delete(record)
            deleted += 1
    if deleted:
        db.commit()
    return deleted
    
def _get_valid_challenge(db: Session, user_id: int, challenge_type: str)-> str:
    record = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.user_id == user_id,
        WebAuthnChallenge.challenge_type == challenge_type,
    ).first()
    
    if not record:
        return None
    
    expires_at = record.expires_at
    now_utc = datetime.now(timezone.utc)
    # SQLite often returns naive datetime objects even for timezone-aware columns.
    # Normalize both operands to avoid naive/aware comparison errors.
    if expires_at.tzinfo is None:
        now = now_utc.replace(tzinfo=None)
    else:
        now = now_utc

    if expires_at <= now:
        db.delete(record)
        db.commit()
        return None
    return record.challenge

def _delete_challenge(db: Session, user_id: int, challenge_type: str) -> None:
    db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.user_id == user_id,
        WebAuthnChallenge.challenge_type == challenge_type,
    ).delete()
    db.commit()


def _delete_pending_registration(db: Session, registration_id: int) -> None:
    db.query(PendingRegistration).filter(PendingRegistration.id == registration_id).delete()
    db.commit()


def _clean_required(value: str | None, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail=error_payload(
                detail=f"{field} is required",
                error_code="validation_error",
            ),
        )
    return text


def _clean_optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text if text else None


def _ensure_authenticating_user_is_active(user: User) -> None:
    # Authentication must stop immediately for deactivated accounts.
    ensure_user_is_active(user)


def _issue_refresh_cookie(
    *,
    db: Session,
    request: Request,
    response: Response,
    user: User,
) -> None:
    request_context = extract_request_security_context(request)
    refresh_token = issue_bound_refresh_token(
        db,
        user_id=user.id,
        refresh_version=int(getattr(user, "refresh_version", 0)),
        context=request_context,
    )
    db.commit()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL * 60,
        secure=IS_PROD,
    )


def _resolve_company_membership(
    *,
    db: Session,
    create_company: bool,
    company_name: str | None,
) -> tuple[int | None, str]:
    company_name_clean = _clean_optional(company_name)

    if create_company:
        if not company_name_clean:
            raise HTTPException(
                status_code=422,
                detail=error_payload(
                    detail="company_name is required when create_company is true",
                    error_code="validation_error",
                ),
            )
        existing = db.query(Company).filter(Company.company_name == company_name_clean).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=error_payload(
                    detail="Company already exists",
                    error_code="validation_error",
                ),
            )
        return None, ROLE_ORG_ADMIN

    if company_name_clean:
        existing = db.query(Company).filter(Company.company_name == company_name_clean).first()
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=error_payload(
                    detail="Company not found",
                    error_code="validation_error",
                ),
            )
        return existing.id, ROLE_USER

    return None, ROLE_USER


def _create_pending_registration(
    *,
    db: Session,
    email: str,
    first_name: str,
    last_name: str,
    company_name: str | None,
    create_company: bool,
    company_id: int | None,
    role: str,
    challenge: str,
) -> PendingRegistration:
    _cleanup_expired_pending_registrations(db)
    db.query(PendingRegistration).filter(PendingRegistration.email == email).delete()
    registration = PendingRegistration(
        email=email,
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        create_company=create_company,
        company_id=company_id,
        role=normalize_role(role),
        webauthn_user_handle=_new_user_handle(),
        challenge=challenge,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=CHALLENGE_TTL_MINUTES),
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


def _get_valid_pending_registration(db: Session, registration_id: int) -> PendingRegistration | None:
    _cleanup_expired_pending_registrations(db)
    registration = db.query(PendingRegistration).filter(PendingRegistration.id == registration_id).first()
    if not registration:
        return None
    expires_at = registration.expires_at
    now_utc = datetime.now(timezone.utc)
    now = now_utc.replace(tzinfo=None) if expires_at.tzinfo is None else now_utc
    if expires_at <= now:
        db.delete(registration)
        db.commit()
        return None
    return registration


def _create_user_from_pending_registration(
    *,
    db: Session,
    registration: PendingRegistration,
):
    existing_user = db.query(User).filter(User.email == registration.email).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=error_payload(
                detail="Account already exists",
                error_code="validation_error",
            ),
        )
    company_id = registration.company_id
    if registration.create_company:
        existing = db.query(Company).filter(Company.company_name == registration.company_name).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=error_payload(
                    detail="Company already exists",
                    error_code="validation_error",
                ),
            )
        company = Company(company_name=registration.company_name, is_active=True)
        db.add(company)
        db.flush()
        company_id = company.id

    user = User(
        email=registration.email,
        first_name=registration.first_name,
        last_name=registration.last_name,
        company_id=company_id,
        role=normalize_role(registration.role),
        webauthn_user_handle=registration.webauthn_user_handle,
    )
    db.add(user)
    db.flush()
    return user


def _load_employee_by_email(db: Session, email: str) -> Employee:
    employee = db.query(Employee).filter(Employee.email == email.strip().lower(), Employee.status == "active").first()
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Employee not found", error_code="employee_not_found"),
        )
    return employee


@router.post("/webauthn/register/options")
def webauthn_register_options(
    request: Request,
    payload: WebAuthnRegisterOptionsRequest = Body(...),
    db: Session = Depends(get_db),
):
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    safe_email = _clean_required(payload.email, "email").lower()
    safe_first_name = _clean_required(payload.first_name, "first_name")
    safe_last_name = _clean_required(payload.last_name, "last_name")
    requested_company_name = _clean_optional(payload.company_name)
    should_create_company = bool(payload.create_company)

    user = db.query(User).filter(User.email == safe_email).first()

    if user:
        record_audit_event(
            db,
            company_id=user.company_id if user else None,
            user_id=user.id if user else None,
            event_type="passkey_registration_denied",
            event_category="authentication",
            description="Passkey registration was denied because an account already exists.",
            target_type="user",
            target_id=str(user.id) if user else None,
            request_context=extract_request_security_context(request),
            event_metadata={"email": safe_email},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Account already exists",
                error_code="validation_error",
            ),
        )

    company_id: int | None
    role: str
    company_id, role = _resolve_company_membership(
        db=db,
        create_company=should_create_company,
        company_name=requested_company_name,
    )

    challenge_b64 = bytes_to_base64url(secrets.token_bytes(32))
    registration = _create_pending_registration(
        db=db,
        email=safe_email,
        first_name=safe_first_name,
        last_name=safe_last_name,
        company_name=requested_company_name,
        create_company=should_create_company,
        company_id=company_id,
        role=role,
        challenge=challenge_b64,
    )

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        challenge=base64url_to_bytes(challenge_b64),
        user_id=base64url_to_bytes(registration.webauthn_user_handle),
        user_name=registration.email,
        user_display_name=f"{registration.first_name} {registration.last_name}",
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    record_audit_event(
        db,
        company_id=registration.company_id,
        user_id=None,
        event_type="passkey_registration_started",
        event_category="authentication",
        description="Passkey registration challenge issued.",
        target_type="pending_registration",
        target_id=str(registration.id),
        request_context=extract_request_security_context(request),
        event_metadata={"create_company": should_create_company},
    )
    db.commit()
    return {"user_id": registration.id, "options": _serialize_webauthn_value(options)}


@router.post("/employee/webauthn/register/options")
def employee_webauthn_register_options(
    request: Request,
    payload: EmployeeWebAuthnRegisterOptionsRequest = Body(...),
    db: Session = Depends(get_db),
):
    ensure_default_company_and_employee(db)
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    safe_email = _clean_required(payload.email, "email").lower()
    employee = _load_employee_by_email(db, safe_email)
    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else db.query(User).filter(User.email == safe_email).first()
    if not user:
        user = User(
            first_name=employee.first_name,
            last_name=employee.last_name,
            email=employee.email,
            company_id=employee.company_id,
            role=normalize_role(employee.role),
            tier="business",
            webauthn_user_handle=_new_user_handle(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        employee.user_id = user.id
        db.add(employee)
        db.commit()
    elif not user.webauthn_user_handle:
        user.webauthn_user_handle = _new_user_handle()
        db.add(user)
        db.commit()
        db.refresh(user)

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=f"{RP_NAME} Employee",
        user_id=base64url_to_bytes(user.webauthn_user_handle),
        user_name=user.email,
        user_display_name=f"{user.first_name} {user.last_name}",
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    _store_challenge(db, user.id, challenge_b64, "employee_register")
    record_audit_event(
        db,
        company_id=employee.company_id,
        user_id=user.id,
        event_type="employee_registration_started",
        event_category="authentication",
        description="Employee passkey enrollment initiated.",
        target_type="employee",
        target_id=str(employee.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"user_id": user.id, "options": _serialize_webauthn_value(options)}


@router.post("/employee/webauthn/status")
def employee_webauthn_status(
    payload: EmployeeWebAuthnStatusRequest = Body(...),
    db: Session = Depends(get_db),
):
    ensure_default_company_and_employee(db)
    safe_email = _clean_required(payload.email, "email").lower()
    employee = db.query(Employee).filter(Employee.email == safe_email).first()
    if not employee:
        return {
            "employee_found": False,
            "passkey_enrolled": False,
            "is_active": False,
        }

    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else None
    return {
        "employee_found": True,
        "passkey_enrolled": bool(user and user.webauthn_credential_id),
        "is_active": employee.status == "active" and bool(user and user.is_active),
    }


@router.post("/employee/webauthn/register/verify")
def employee_webauthn_register_verify(
    request: Request,
    payload: EmployeeWebAuthnRegisterVerifyRequest,
    db: Session = Depends(get_db),
):
    safe_email = _clean_required(payload.email, "email").lower()
    employee = _load_employee_by_email(db, safe_email)
    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else None
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Employee account not found", error_code="employee_not_found"),
        )
    expected_challenge_b64 = _get_valid_challenge(db, user.id, "employee_register")
    if not expected_challenge_b64:
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Missing registration challenge", error_code="session_expired"),
        )
    try:
        verification = verify_registration_response(
            credential=payload.credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=True,
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Registration verification failed", error_code="validation_error"),
        )
    user.webauthn_credential_id = bytes_to_base64url(verification.credential_id)
    user.webauthn_public_key = bytes_to_base64url(verification.credential_public_key)
    user.webauthn_sign_count = verification.sign_count or 0
    db.add(user)
    db.commit()
    _delete_challenge(db, user.id, "employee_register")
    record_audit_event(
        db,
        company_id=employee.company_id,
        user_id=user.id,
        event_type="employee_registration_completed",
        event_category="authentication",
        description="Employee passkey enrollment completed.",
        target_type="employee",
        target_id=str(employee.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"status": "ok", "message": "Employee passkey enrolled"}


@router.post("/webauthn/register/verify")
def webauthn_register_verify(
    request: Request,
    payload: WebAuthnRegisterVerifyRequest,
    db: Session = Depends(get_db),
):
    _enforce_auth_rate_limit(db=db, request=request, identifier=str(payload.user_id))
    registration_id = payload.user_id
    request_credential = payload.credential

    _cleanup_expired_pending_registrations(db)

    registration = _get_valid_pending_registration(db, registration_id)
    if not registration:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Missing registration challenge",
                error_code="session_expired",
            ),
        )

    try:
        verification = verify_registration_response(
            credential=request_credential,
            expected_challenge=base64url_to_bytes(registration.challenge),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=True,
        )
    except Exception:
        request_context = extract_request_security_context(request)
        try:
            register_failed_login(
                db,
                email=registration.email,
                organization_id=registration.company_id,
                user_id=None,
                context=request_context,
            )
        except Exception:
            db.rollback()
        record_audit_event(
            db,
            company_id=registration.company_id,
            user_id=None,
            event_type="passkey_registration_failed",
            event_category="authentication",
            description="Registration verification failed.",
            target_type="pending_registration",
            target_id=str(registration.id),
            request_context=request_context,
        )
        db.commit()
        _delete_pending_registration(db, registration.id)
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Registration verification failed",
                error_code="validation_error",
            ),
        )

    user = _create_user_from_pending_registration(
        db=db,
        registration=registration,
    )
    user.webauthn_credential_id = bytes_to_base64url(verification.credential_id)
    user.webauthn_public_key = bytes_to_base64url(verification.credential_public_key)
    user.webauthn_sign_count = verification.sign_count or 0

    db.add(user)
    db.commit()
    db.refresh(user)

    _delete_pending_registration(db, registration.id)
    record_audit_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type="passkey_registered",
        event_category="authentication",
        description="Passkey registration completed.",
        target_type="user",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"status": "ok", "message": "Passkey enrolled"}


@router.post("/webauthn/login/options")
def webauthn_login_options(
    request: Request,
    payload: WebAuthnLoginOptionsRequest,
    db: Session = Depends(get_db),
):
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    request_email = payload.email or ""
    safe_email = request_email.strip().lower()
    if not safe_email:
        raise HTTPException(
            status_code=422,
            detail=error_payload(
                detail="email is required",
                error_code="validation_error",
            ),
        )

    _cleanup_expired_challenges(db)
    user = db.query(User).filter(User.email == safe_email).first()
    if not user or not user.webauthn_credential_id:
        register_failed_login(
            db,
            email=safe_email,
            organization_id=user.company_id if user else None,
            user_id=user.id if user else None,
            context=extract_request_security_context(request),
        )
        record_audit_event(
            db,
            company_id=user.company_id if user else None,
            user_id=user.id if user else None,
            event_type="login_failure",
            event_category="authentication",
            description="Login options requested for an account without a registered passkey.",
            target_type="user",
            target_id=str(user.id) if user else None,
            request_context=extract_request_security_context(request),
            event_metadata={"email": safe_email},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="No passkey enrolled for this account",
                error_code="validation_error",
            ),
        )
    _ensure_authenticating_user_is_active(user)

    options = generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[
            {"id": base64url_to_bytes(user.webauthn_credential_id), "type": "public-key"}
        ],
    )

    challenge_b64 = bytes_to_base64url(options.challenge)
    _store_challenge(db, user.id, challenge_b64, "login")
    record_audit_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type="login_challenge_issued",
        event_category="authentication",
        description="Login challenge issued.",
        target_type="user",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return _serialize_webauthn_value(options)


@router.post("/webauthn/login/verify")
def webauthn_login_verify(
    request: Request,
    response: Response,
    payload: WebAuthnLoginVerifyRequest,
    db: Session = Depends(get_db),
):
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    request_email = payload.email or ""
    request_credential = payload.credential
    safe_email = request_email.strip().lower()
    if not safe_email or not request_credential:
        raise HTTPException(
            status_code=422,
            detail=error_payload(
                detail="email and credential are required",
                error_code="validation_error",
            ),
        )

    _cleanup_expired_challenges(db)
    user = db.query(User).filter(User.email == safe_email).first()
    if not user or not user.webauthn_credential_id:
        register_failed_login(
            db,
            email=safe_email,
            organization_id=user.company_id if user else None,
            user_id=user.id if user else None,
            context=extract_request_security_context(request),
        )
        record_audit_event(
            db,
            company_id=user.company_id if user else None,
            user_id=user.id if user else None,
            event_type="login_failure",
            event_category="authentication",
            description="Invalid login attempt.",
            target_type="user",
            target_id=str(user.id) if user else None,
            request_context=extract_request_security_context(request),
            event_metadata={"email": safe_email},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Invalid login",
                error_code="unauthorized",
            ),
        )
    _ensure_authenticating_user_is_active(user)

    expected_challenge_b64 = _get_valid_challenge(db, user.id,"login")
    if not expected_challenge_b64:
        record_audit_event(
            db,
            company_id=user.company_id,
            user_id=user.id,
            event_type="login_failure",
            event_category="authentication",
            description="Login failed because the challenge expired.",
            target_type="user",
            target_id=str(user.id),
            request_context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Missing login challenge",
                error_code="session_expired",
            ),
        )

    try:
        verification = verify_authentication_response(
            credential=request_credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64url_to_bytes(user.webauthn_public_key),
            credential_current_sign_count=user.webauthn_sign_count,
            require_user_verification=True,
        )
    except Exception:
        register_failed_login(
            db,
            email=safe_email,
            organization_id=user.company_id,
            user_id=user.id,
            context=extract_request_security_context(request),
        )
        record_audit_event(
            db,
            company_id=user.company_id,
            user_id=user.id,
            event_type="login_failure",
            event_category="authentication",
            description="Login verification failed.",
            target_type="user",
            target_id=str(user.id),
            request_context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Login verification failed",
                error_code="unauthorized",
            ),
        )

    user.webauthn_sign_count = verification.new_sign_count
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    _delete_challenge(db, user.id, "login")
    record_audit_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type="login_success",
        event_category="authentication",
        description="User authenticated with passkey.",
        target_type="user",
        target_id=str(user.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tier": getattr(user, "tier", "free"),
            "role": normalize_role(user.role),
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL),
    )
    _issue_refresh_cookie(
        db=db,
        request=request,
        response=response,
        user=user,
    )
    

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/employee/webauthn/login/options")
def employee_webauthn_login_options(
    request: Request,
    payload: WebAuthnLoginOptionsRequest,
    db: Session = Depends(get_db),
):
    ensure_default_company_and_employee(db)
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    safe_email = _clean_required(payload.email, "email").lower()
    employee = _load_employee_by_email(db, safe_email)
    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else None
    if not user or not user.webauthn_credential_id:
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="No passkey enrolled for this employee account", error_code="validation_error"),
        )
    _ensure_authenticating_user_is_active(user)
    options = generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[{"id": base64url_to_bytes(user.webauthn_credential_id), "type": "public-key"}],
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    _store_challenge(db, user.id, challenge_b64, "employee_login")
    return _serialize_webauthn_value(options)


@router.post("/employee/webauthn/login/verify")
def employee_webauthn_login_verify(
    request: Request,
    response: Response,
    payload: WebAuthnLoginVerifyRequest,
    db: Session = Depends(get_db),
):
    _enforce_auth_rate_limit(db=db, request=request, identifier=payload.email)
    safe_email = _clean_required(payload.email, "email").lower()
    employee = _load_employee_by_email(db, safe_email)
    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else None
    if not user or not user.webauthn_credential_id:
        register_failed_login(
            db,
            email=safe_email,
            organization_id=employee.company_id,
            user_id=user.id if user else None,
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Invalid employee login", error_code="unauthorized"),
        )
    _ensure_authenticating_user_is_active(user)
    expected_challenge_b64 = _get_valid_challenge(db, user.id, "employee_login")
    if not expected_challenge_b64:
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Missing login challenge", error_code="session_expired"),
        )
    try:
        verification = verify_authentication_response(
            credential=payload.credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64url_to_bytes(user.webauthn_public_key),
            credential_current_sign_count=user.webauthn_sign_count,
            require_user_verification=True,
        )
    except Exception:
        register_failed_login(
            db,
            email=safe_email,
            organization_id=employee.company_id,
            user_id=user.id,
            context=extract_request_security_context(request),
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Employee login verification failed", error_code="unauthorized"),
        )
    user.webauthn_sign_count = verification.new_sign_count
    user.last_login_at = datetime.now(timezone.utc)
    employee.last_login = user.last_login_at
    db.add(user)
    db.add(employee)
    db.commit()
    _delete_challenge(db, user.id, "employee_login")
    record_audit_event(
        db,
        company_id=employee.company_id,
        user_id=user.id,
        event_type="employee_login_success",
        event_category="authentication",
        description="Employee authenticated to the compliance workspace.",
        target_type="employee",
        target_id=str(employee.id),
        request_context=extract_request_security_context(request),
        event_metadata={"employee_role": employee.role},
    )
    db.commit()
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "tier": getattr(user, "tier", "business"), "role": normalize_role(user.role)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL),
    )
    _issue_refresh_cookie(
        db=db,
        request=request,
        response=response,
        user=user,
    )
    return {"access_token": access_token, "token_type": "bearer", "employee": True}
