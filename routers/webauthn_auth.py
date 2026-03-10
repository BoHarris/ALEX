import os
import secrets
import dataclasses
from datetime import timedelta, datetime, timezone
from enum import Enum

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company import Company
from database.models.user import User
from database.models.webauthn_challenge import WebAuthnChallenge
from utils.auth_utils import create_access_token

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



class WebAuthnRegisterOptionsRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    company_name: str | None = None
    create_company: bool = False


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


def _clean_required(value: str | None, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail=f"{field} is required")
    return text


def _clean_optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text if text else None


def _resolve_register_request(
    payload: WebAuthnRegisterOptionsRequest | None,
    email: str | None,
    first_name: str | None,
    last_name: str | None,
    company_name: str | None,
    create_company: bool | None,
) -> WebAuthnRegisterOptionsRequest:
    if payload is not None:
        return payload

    return WebAuthnRegisterOptionsRequest(
        email=email or "",
        first_name=first_name or "",
        last_name=last_name or "",
        company_name=company_name,
        create_company=bool(create_company),
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
            raise HTTPException(status_code=422, detail="company_name is required when create_company is true")
        existing = db.query(Company).filter(Company.company_name == company_name_clean).first()
        if existing:
            raise HTTPException(status_code=409, detail="Company already exists")

        company = Company(company_name=company_name_clean, is_active=True)
        db.add(company)
        db.flush()
        return company.id, "admin"

    if company_name_clean:
        existing = db.query(Company).filter(Company.company_name == company_name_clean).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Company not found")
        return existing.id, "member"

    return None, "member"


@router.post("/webauthn/register/options")
def webauthn_register_options(
    payload: WebAuthnRegisterOptionsRequest | None = Body(default=None),
    email: str | None = Query(default=None),
    first_name: str | None = Query(default=None),
    last_name: str | None = Query(default=None),
    company_name: str | None = Query(default=None),
    create_company: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    request_payload = _resolve_register_request(
        payload=payload,
        email=email,
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        create_company=create_company,
    )

    safe_email = _clean_required(request_payload.email, "email").lower()
    safe_first_name = _clean_required(request_payload.first_name, "first_name")
    safe_last_name = _clean_required(request_payload.last_name, "last_name")
    requested_company_name = _clean_optional(request_payload.company_name)
    should_create_company = bool(request_payload.create_company)

    user = db.query(User).filter(User.email == safe_email).first()

    if user and user.webauthn_credential_id:
        raise HTTPException(status_code=400, detail="Passkey already enrolled for this account")

    company_id: int | None
    role: str
    if (
        user
        and should_create_company
        and requested_company_name
        and user.company_id is not None
    ):
        current_company = db.query(Company).filter(Company.id == user.company_id).first()
        if current_company and current_company.company_name == requested_company_name:
            company_id = current_company.id
            role = "admin"
        else:
            company_id, role = _resolve_company_membership(
                db=db,
                create_company=should_create_company,
                company_name=requested_company_name,
            )
    else:
        company_id, role = _resolve_company_membership(
            db=db,
            create_company=should_create_company,
            company_name=requested_company_name,
        )

    if user:
        user.first_name = safe_first_name
        user.last_name = safe_last_name
        user.company_id = company_id
        user.role = role
        if not user.webauthn_user_handle:
            user.webauthn_user_handle = _new_user_handle()
    else:
        user = User(
            email=safe_email,
            first_name=safe_first_name,
            last_name=safe_last_name,
            company_id=company_id,
            role=role,
            webauthn_user_handle=_new_user_handle(),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
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
    _store_challenge(db, user.id, challenge_b64, "register")
    return {"user_id": user.id, "options": _serialize_webauthn_value(options)}


@router.post("/webauthn/register/verify")
def webauthn_register_verify(
    user_id: int,
    credential: dict,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expected_challenge_b64 = _get_valid_challenge(db, user.id, "register")
    if not expected_challenge_b64:
        raise HTTPException(status_code=400, detail="Missing registration challenge")

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=True,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {str(e)}")

    user.webauthn_credential_id = bytes_to_base64url(verification.credential_id)
    user.webauthn_public_key = bytes_to_base64url(verification.credential_public_key)
    user.webauthn_sign_count = verification.sign_count or 0

    db.add(user)
    db.commit()

    _delete_challenge(db, user.id, "register")
    return {"status": "ok", "message": "Passkey enrolled"}


@router.post("/webauthn/login/options")
def webauthn_login_options(
    email: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.webauthn_credential_id:
        raise HTTPException(status_code=400, detail="No passkey enrolled for this account")

    options = generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[
            {"id": base64url_to_bytes(user.webauthn_credential_id), "type": "public-key"}
        ],
    )

    challenge_b64 = bytes_to_base64url(options.challenge)
    _store_challenge(db, user.id, challenge_b64, "login")
    return _serialize_webauthn_value(options)


@router.post("/webauthn/login/verify")
def webauthn_login_verify(
    response: Response,
    email: str,
    credential: dict,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.webauthn_credential_id:
        raise HTTPException(status_code=400, detail="Invalid login")

    expected_challenge_b64 = _get_valid_challenge(db, user.id,"login")
    if not expected_challenge_b64:
        raise HTTPException(status_code=400, detail="Missing login challenge")

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64url_to_bytes(user.webauthn_public_key),
            credential_current_sign_count=user.webauthn_sign_count,
            require_user_verification=True,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login verification failed: {str(e)}")

    user.webauthn_sign_count = verification.new_sign_count
    db.add(user)
    db.commit()

    _delete_challenge(db, user.id, "login")

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "tier": getattr(user, "tier", "free")},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL),
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id), "ver": int(getattr(user, "refresh_version", 0)), "typ": "refresh"},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_TTL),
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL * 60,
        secure=True,
    )
    

    return {"access_token": access_token, "token_type": "bearer"}
