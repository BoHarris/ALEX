import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
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

RP_ID = os.getenv("RP_ID", "localhost")
RP_NAME = os.getenv("RP_NAME", "ALEX")
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

# Dev-only challenge storage
_REG_CHALLENGES = {}
_AUTH_CHALLENGES = {}


def _new_user_handle() -> str:
    return bytes_to_base64url(secrets.token_bytes(32))


@router.post("/webauthn/register/options")
def webauthn_register_options(
    email: str,
    first_name: str,
    last_name: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if user and user.webauthn_credential_id:
        raise HTTPException(status_code=400, detail="Passkey already enrolled for this account")

    if not user:
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
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

    _REG_CHALLENGES[user.id] = bytes_to_base64url(options.challenge)
    return {"user_id": user.id, "options": options}


@router.post("/webauthn/register/verify")
def webauthn_register_verify(
    user_id: int,
    credential: dict,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expected_challenge_b64 = _REG_CHALLENGES.get(user.id)
    if not expected_challenge_b64:
        raise HTTPException(status_code=400, detail="Missing registration challenge")

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=False,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {str(e)}")

    user.webauthn_credential_id = bytes_to_base64url(verification.credential_id)
    user.webauthn_public_key = bytes_to_base64url(verification.credential_public_key)
    user.webauthn_sign_count = verification.sign_count or 0

    db.add(user)
    db.commit()

    _REG_CHALLENGES.pop(user.id, None)
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

    _AUTH_CHALLENGES[user.id] = bytes_to_base64url(options.challenge)
    return options


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

    expected_challenge_b64 = _AUTH_CHALLENGES.get(user.id)
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
            require_user_verification=False,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login verification failed: {str(e)}")

    user.webauthn_sign_count = verification.new_sign_count
    db.add(user)
    db.commit()

    _AUTH_CHALLENGES.pop(user.id, None)

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
