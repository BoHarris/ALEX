from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.api_key import ApiKey
from dependencies.tier_guard import require_company_admin
from utils.api_errors import error_payload
from utils.api_key_auth import generate_api_key_secret, hash_api_key

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class CreateApiKeyRequest(BaseModel):
    name: str


@router.get("")
def list_api_keys(
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.company_id == current_user["company_id"])
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return {
        "api_keys": [
            {
                "id": item.id,
                "name": item.name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "last_used": item.last_used.isoformat() if item.last_used else None,
                "usage_count": item.usage_count,
                "created_by_user_id": item.created_by_user_id,
            }
            for item in keys
        ]
    }


@router.post("")
def create_api_key(
    payload: CreateApiKeyRequest,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    raw_key = generate_api_key_secret()
    api_key = ApiKey(
        company_id=current_user["company_id"],
        created_by_user_id=current_user["user_id"],
        name=payload.name.strip() or "Automation Key",
        hashed_key=hash_api_key(raw_key),
        usage_count=0,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
    }


@router.delete("/{api_key_id}")
def revoke_api_key(
    api_key_id: int,
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == api_key_id, ApiKey.company_id == current_user["company_id"])
        .first()
    )
    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="API key not found", error_code="not_found"),
        )
    db.delete(api_key)
    db.commit()
    return {"revoked_api_key_id": api_key_id}
