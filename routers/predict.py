import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from dependencies.tier_guard import enforce_tier_limit
from services.scan_service import ScanContext, run_scan_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])


class PredictionResult(BaseModel):
    filename: str
    pii_columns: list[str]
    redacted_file: str
    risk_score: float
    redacted_count: int
    total_values: int


@router.post("/", response_model=PredictionResult)
async def predict(
    file: UploadFile = File(...),
    user_info: dict = Depends(enforce_tier_limit),
    aggressive: bool = False,
):
    if not isinstance(user_info, dict):
        logger.error("Invalid user_info injected into predict route: %r", type(user_info))
        raise HTTPException(status_code=500, detail="Invalid authentication context.")

    user_id = user_info.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Missing user identity.")

    try:
        file_bytes = await file.read()
        context = ScanContext(
            user_id=int(user_id),
            company_id=user_info.get("company_id"),
            tier=user_info.get("tier"),
        )
        result = run_scan_pipeline(
            file_bytes=file_bytes,
            filename=file.filename,
            context=context,
            aggressive=aggressive,
        )
        return PredictionResult(
            filename=result.filename,
            pii_columns=result.pii_columns,
            redacted_file=result.redacted_file,
            risk_score=result.risk_score,
            redacted_count=result.redacted_count,
            total_values=result.total_values,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
