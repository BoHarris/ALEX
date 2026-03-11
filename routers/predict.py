from routers.scans import (
    ScanLimitError,
    ScanResultPayload as PredictionResult,
    _company_allowed_extensions,
    _is_text_payload,
    _passes_content_signature_check,
    _stream_upload_to_tempfile,
    create_scan as predict,
)

# Compatibility module for legacy imports. The live API no longer mounts `/predict`.
