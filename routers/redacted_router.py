# routers/redacted_router.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path
from mimetypes import guess_type

router = APIRouter(prefix="/redacted", tags=["Redacted"])

BASE_DIR = Path(__file__).resolve().parent.parent

REDACTED_DIR = BASE_DIR / "static" / "redacted"

@router.get("/files")
def list_redacted_files():
    if not REDACTED_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Redacted folder not found")
    files = [f.name for f in REDACTED_DIR.iterdir() if f.is_file()]
    return {"files": files}

@router.get("/download/{filename}")
def download_redacted_file(filename: str):
    path = REDACTED_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # auto‐guess the correct mime type
    mime, _ = guess_type(str(path))
    disposition = "inline" if mime =="application/pdf" else "attachment"
    return FileResponse(
        str(path),
        media_type=mime or "application/octet",
        headers={"Content-Disposition": f"{disposition}; filename={filename}"}
    )