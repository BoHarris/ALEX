from __future__ import annotations

from fastapi import HTTPException


def error_payload(
    *,
    detail: str,
    error_code: str,
    error_id: str | None = None,
) -> dict:
    payload = {
        "detail": detail,
        "error_code": error_code,
    }
    if error_id:
        payload["error_id"] = error_id
    return payload


def raise_api_error(
    *,
    status_code: int,
    detail: str,
    error_code: str,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=error_payload(detail=detail, error_code=error_code),
    )


def default_error_code_for_status(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 413:
        return "payload_too_large"
    if status_code == 422:
        return "validation_error"
    if status_code == 429:
        return "rate_limit_exceeded"
    return "request_error"
