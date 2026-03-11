from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
import shutil
import uuid

import pandas as pd
import pytest
from fastapi import HTTPException, UploadFile

from routers import scans as scans_router
from services import scan_service


class _FakeModel:
    def predict(self, frame):
        return [0 if index == 0 else 1 for index in range(len(frame))]


def _fake_redactor(series, column_name="", aggressive=False):
    redacted = series.astype(str).map(lambda value: "[REDACTED_PII_EMAIL]" if value else value)
    count = int(series.notna().sum())
    return redacted, count, len(series), 1.0 if len(series) else 0.0, {"PII_EMAIL": count}


def _write_csv(path: Path, rows: int) -> None:
    frame = pd.DataFrame(
        {
            "email": [f"user{index}@example.com" for index in range(rows)],
            "notes": [f"note-{index}" for index in range(rows)],
        }
    )
    frame.to_csv(path, index=False)


def _make_local_test_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".test_tmp" / f"scan_limits_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def test_chunked_scan_pipeline_redacts_csv_without_materializing_full_dataset(monkeypatch):
    base = _make_local_test_dir()
    monkeypatch.chdir(base)
    monkeypatch.setattr(scan_service, "_persist_scan_result", lambda **kwargs: 101)
    monkeypatch.setattr(scan_service, "scan_and_redact_column_with_details", _fake_redactor)

    try:
        input_path = base / "sample.csv"
        _write_csv(input_path, rows=4)

        result = scan_service.run_scan_pipeline(
            source_path=str(input_path),
            filename="sample.csv",
            context=scan_service.ScanContext(user_id=7),
            model=_FakeModel(),
            limits=scan_service.ScanLimits(max_rows=10, max_cells=50, max_columns=5, chunk_rows=2),
        )

        redacted_frame = pd.read_csv(result.redacted_file)

        assert result.scan_id == 101
        assert result.pii_columns == ["email"]
        assert result.redacted_count == 4
        assert result.total_values == 4
        assert redacted_frame["email"].tolist() == ["[REDACTED_PII_EMAIL]"] * 4
        assert redacted_frame["notes"].tolist() == [f"note-{index}" for index in range(4)]
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_chunked_scan_pipeline_rejects_files_over_row_limit():
    base = _make_local_test_dir()
    input_path = base / "too_many_rows.csv"
    _write_csv(input_path, rows=5)

    try:
        with pytest.raises(scan_service.ScanLimitError) as exc:
            scan_service.run_scan_pipeline(
                source_path=str(input_path),
                filename="too_many_rows.csv",
                context=scan_service.ScanContext(user_id=9),
                model=_FakeModel(),
                limits=scan_service.ScanLimits(max_rows=4, max_cells=100, max_columns=5, chunk_rows=2),
            )

        assert exc.value.status_code == 413
        assert exc.value.error_code == "FILE_TOO_LARGE"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_chunked_scan_pipeline_uses_multiple_chunks_for_large_csv(monkeypatch):
    base = _make_local_test_dir()
    monkeypatch.chdir(base)
    monkeypatch.setattr(scan_service, "_persist_scan_result", lambda **kwargs: 202)
    monkeypatch.setattr(scan_service, "scan_and_redact_column_with_details", _fake_redactor)

    try:
        input_path = base / "large.csv"
        _write_csv(input_path, rows=450)

        original_iter = scan_service._iter_csv_like_chunks
        observed_chunk_sizes: list[int] = []

        def _tracking_iter(*, source_path: str, ext: str, chunk_rows: int):
            for chunk in original_iter(source_path=source_path, ext=ext, chunk_rows=chunk_rows):
                observed_chunk_sizes.append(len(chunk))
                yield chunk

        monkeypatch.setattr(scan_service, "_iter_csv_like_chunks", _tracking_iter)

        result = scan_service.run_scan_pipeline(
            source_path=str(input_path),
            filename="large.csv",
            context=scan_service.ScanContext(user_id=11),
            model=_FakeModel(),
            limits=scan_service.ScanLimits(max_rows=500, max_cells=2000, max_columns=5, chunk_rows=100),
        )

        assert result.redacted_count == 450
        assert len(observed_chunk_sizes) > 1
        assert max(observed_chunk_sizes) <= 100
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_predict_returns_payload_too_large_for_scan_limit(monkeypatch):
    base = _make_local_test_dir()
    monkeypatch.chdir(base)
    monkeypatch.setattr(scans_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "register_scan_activity", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "reserve_scan_quota", lambda *args, **kwargs: True)
    monkeypatch.setattr(scans_router, "release_scan_quota_reservation", lambda *args, **kwargs: None)
    monkeypatch.setattr(scans_router, "extract_request_security_context", lambda request: {})

    async def _inline_run_in_threadpool(func):
        return func()

    monkeypatch.setattr(scans_router, "run_in_threadpool", _inline_run_in_threadpool)
    monkeypatch.setattr(
        scans_router,
        "run_scan_pipeline",
        lambda **kwargs: (_ for _ in ()).throw(scans_router.ScanLimitError("Uploaded file exceeds allowed processing limits")),
    )

    class _AppState:
        pii_model = _FakeModel()

    class _App:
        state = _AppState()

    class _Request:
        headers = {}
        app = _App()

    class _Db:
        def commit(self):
            return None

    upload = UploadFile(filename="sample.csv", file=BytesIO(b"email,notes\nada@example.com,ok\n"))

    try:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
            scans_router.create_scan(
                request=_Request(),
                file=upload,
                user_info={"user_id": 1, "company_id": None, "tier": "free"},
                    db=_Db(),
                    aggressive=False,
                )
            )
        assert exc.value.status_code == 413
        assert exc.value.detail["error_code"] == "file_too_large"
    finally:
        shutil.rmtree(base, ignore_errors=True)
