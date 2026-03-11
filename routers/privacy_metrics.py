from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.database import get_db
from dependencies.tier_guard import require_company_admin
from services.privacy_metrics_service import get_privacy_metrics

router = APIRouter(tags=["Privacy Metrics"])


@router.get("/privacy-metrics")
def privacy_metrics(
    activity_window_days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    return get_privacy_metrics(
        db,
        company_id=current_user["company_id"],
        activity_window_days=activity_window_days,
    )
