import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from dependencies.tier_guard import enforce_tier_limit
from services.scan_service import ScanContext, run_scan_pipeline
from utils.constants import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


class PredictionResult(BaseModel):
    scan_id: int
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

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

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
            scan_id=result.scan_id,
            filename=result.filename,
            pii_columns=result.pii_columns,
            redacted_file=f"/scans/{result.scan_id}/download",
            risk_score=result.risk_score,
            redacted_count=result.redacted_count,
            total_values=result.total_values,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected upload processing failure for %s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to process upload.") from exc
