import html as html_lib
import io
import json
import logging
import mimetypes
import os
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from sqlalchemy.exc import IntegrityError

from database.database import SessionLocal
from database.models.scan_results import ScanResult
from services.retention_service import build_retention_expiration, resolve_retention_days
from services.audit_service import record_audit_event
from utils.constants import SUPPORTED_EXTENSIONS
from utils.redaction import scan_and_redact_column_with_details

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_model.pkl"
_xgb_model = None

EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
STREET_SUFFIXES = {"st", "street", "ave", "road", "rd", "blvd", "ln", "lane"}
MAX_FEATURE_SAMPLE_VALUES = max(3, int(os.getenv("FEATURE_SAMPLE_VALUES", "15")))


@dataclass(frozen=True)
class ScanContext:
    user_id: int
    company_id: Optional[int] = None
    tier: Optional[str] = None


@dataclass(frozen=True)
class ScanPipelineResult:
    filename: str
    pii_columns: list[str]
    redacted_file: str
    risk_score: int
    redacted_count: int
    total_values: int
    redacted_type_counts: dict[str, int]
    scan_id: int


def _load_xgboost_model(model_path: Path = MODEL_PATH):
    try:
        return joblib.load(model_path)
    except Exception as exc:
        raise RuntimeError(
            "StartupError: XGBoost model could not be loaded. "
            "Verify model file exists and is compatible with current environment."
        ) from exc


def initialize_scan_model(model_path: Path = MODEL_PATH):
    global _xgb_model
    if _xgb_model is None:
        _xgb_model = _load_xgboost_model(model_path)
    return _xgb_model


def set_scan_model(model) -> None:
    global _xgb_model
    _xgb_model = model


def get_scan_model():
    if _xgb_model is None:
        raise RuntimeError(
            "Scan model is not initialized. Startup validation must load the XGBoost model before scanning."
        )
    return _xgb_model


def _contains_dob_pattern(values: list[str]) -> bool:
    dob_regex = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
    return any(dob_regex.search(str(value)) for value in values) if values else False


def _contains_gender_term(values: list[str]) -> bool:
    gender_terms = {"male", "female", "man", "woman", "boy", "girl"}
    return any(any(term in str(value).lower() for term in gender_terms) for value in values) if values else False


def _contains_street_suffix(values: list[str]) -> bool:
    return any(any(suffix in str(value).lower() for suffix in STREET_SUFFIXES) for value in values) if values else False


def _contains_city_name(values: list[str]) -> bool:
    city_names = {"new york", "los angeles", "chicago", "houston", "phoenix"}
    return any(any(city in str(value).lower() for city in city_names) for value in values) if values else False


def _contains_known_name(values: list[str]) -> bool:
    known_names = {"john", "jane", "smith", "doe"}
    return any(any(name in str(value).lower() for name in known_names) for value in values) if values else False


def _contains_zip_code_pattern(values: list[str]) -> bool:
    zip_regex = re.compile(r"\b\d{5}(?:-\d{4})?\b")
    return any(zip_regex.search(str(value)) for value in values) if values else False


def _contains_phone_pattern(values: list[str]) -> bool:
    return any(PHONE_RE.search(str(value)) for value in values) if values else False


def _parse_to_dataframe(file_bytes: bytes, filename: str, ext: str) -> pd.DataFrame:
    file_format, _ = mimetypes.guess_type(filename)
    file_format = file_format or ""

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("PDF is encrypted or requires a password.") from exc
        texts = [page.extract_text() or "" for page in reader.pages]
        parsed = pd.DataFrame({"text": texts})
    elif ext == ".csv" or "csv" in file_format:
        parsed = pd.read_csv(io.BytesIO(file_bytes))
    elif ext == ".tsv":
        parsed = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
    elif ext in {".xls", ".xlsx"} or "excel" in file_format:
        parsed = pd.read_excel(io.BytesIO(file_bytes))
    elif ext == ".json" or "json" in file_format:
        data = json.load(io.BytesIO(file_bytes))
        parsed = pd.json_normalize(data)
    elif ext in {".txt", ".log"} or "plain" in file_format:
        lines = io.BytesIO(file_bytes).read().decode("utf-8", errors="ignore").splitlines()
        parsed = pd.DataFrame({"text": lines})
    elif ext == ".xml" or "xml" in file_format:
        tree = ET.parse(io.BytesIO(file_bytes))
        root = tree.getroot()
        parsed = pd.DataFrame([{child.tag: child.text for child in elem} for elem in root])
    elif ext == ".docx":
        doc = Document(io.BytesIO(file_bytes))
        chunks: list[str] = []
        for p in doc.paragraphs:
            if p.text and p.text.strip():
                chunks.append(p.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text and cell.text.strip():
                        chunks.append(cell.text)
        parsed = pd.DataFrame({"text": chunks})
    elif ext == ".html":
        try:
            tables = pd.read_html(io.BytesIO(file_bytes))
            parsed = tables[0] if tables else pd.DataFrame({"text": []})
        except Exception:
            raw = io.BytesIO(file_bytes).read().decode("utf-8", errors="ignore")
            raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw)
            text = re.sub(r"(?s)<.*?>", "\n", raw)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            parsed = pd.DataFrame({"text": lines})
    else:
        raise ValueError(f"Unsupported format: {file_format} / {ext}")

    df = parsed if isinstance(parsed, pd.DataFrame) else pd.DataFrame({"text": parsed})
    if df.empty:
        raise ValueError("File is empty or not supported.")
    return df


def _build_feature_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    features = df.columns.tolist()
    x = pd.DataFrame(features, columns=["column"])
    x["length"] = x["column"].apply(len)
    x["num_underscores"] = x["column"].apply(lambda col: col.count("_"))
    x["num_digits"] = x["column"].apply(lambda col: sum(c.isdigit() for c in col))
    x["has_at"] = x["column"].apply(lambda col: int("@" in col))
    x["has_email_keyword"] = x["column"].apply(lambda col: int("email" in col.lower()))

    # Sample values across each column (head/mid/tail) to reduce sparse/late-row PII misses.
    def column_sample_values(series: pd.Series) -> list[str]:
        values = series.dropna().astype(str)
        if values.empty:
            return []
        if len(values) <= MAX_FEATURE_SAMPLE_VALUES:
            return values.tolist()
        indices = np.linspace(0, len(values) - 1, num=MAX_FEATURE_SAMPLE_VALUES, dtype=int)
        return values.iloc[indices].tolist()

    value_samples = [column_sample_values(df[col]) for col in df.columns]
    x["parsed_values"] = value_samples

    def pct_match(regex: re.Pattern, values: list[str]) -> float:
        return float(np.mean([bool(regex.search(str(v))) for v in values])) if values else 0.0

    x["pct_email_like"] = x["parsed_values"].apply(lambda vals: pct_match(EMAIL_RE, vals))
    x["pct_phone_like"] = x["parsed_values"].apply(lambda vals: pct_match(PHONE_RE, vals))
    x["pct_ssn_like"] = x["parsed_values"].apply(lambda vals: pct_match(SSN_RE, vals))
    x["pct_ip_like"] = x["parsed_values"].apply(lambda vals: pct_match(IP_RE, vals))
    x["avg_digits_per_val"] = x["parsed_values"].apply(
        lambda vals: np.mean([sum(c.isdigit() for c in str(item)) for item in vals]) if vals else 0
    )
    x["avg_val_len"] = x["parsed_values"].apply(
        lambda vals: np.mean([len(str(item)) for item in vals]) if vals else 0
    )
    x["has_dob_pattern"] = x["parsed_values"].apply(_contains_dob_pattern)
    x["has_gender_term"] = x["parsed_values"].apply(_contains_gender_term)
    x["has_street_suffix"] = x["parsed_values"].apply(_contains_street_suffix)
    x["has_city_name"] = x["parsed_values"].apply(_contains_city_name)
    x["has_known_name"] = x["parsed_values"].apply(_contains_known_name)
    x["has_zip_pattern"] = x["parsed_values"].apply(_contains_zip_code_pattern)
    x["has_phone_pattern"] = x["parsed_values"].apply(_contains_phone_pattern)
    return x, features


def _write_redacted_file(redacted_df: pd.DataFrame, redacted_path: str, ext: str) -> None:
    if ext == ".csv":
        redacted_df.to_csv(redacted_path, index=False)
    elif ext == ".tsv":
        redacted_df.to_csv(redacted_path, index=False, sep="\t")
    elif ext in {".txt", ".log"}:
        redacted_df.to_csv(redacted_path, index=False)
    elif ext in {".xlsx", ".xls"}:
        redacted_df.to_excel(redacted_path, index=False)
    elif ext == ".json":
        redacted_df.to_json(redacted_path, orient="records", lines=True)
    elif ext == ".xml":
        root = ET.Element("root")
        for _, row in redacted_df.iterrows():
            item = ET.SubElement(root, "item")
            for col_name, value in row.items():
                child = ET.SubElement(item, col_name)
                child.text = "" if value is None else str(value)
        ET.ElementTree(root).write(redacted_path)
    elif ext == ".docx":
        out = Document()
        if list(redacted_df.columns) == ["text"]:
            for text in redacted_df["text"].fillna("").astype(str).tolist():
                out.add_paragraph(text)
        else:
            for _, row in redacted_df.iterrows():
                out.add_paragraph(" | ".join([str(value) for value in row.values]))
        out.save(redacted_path)
    elif ext == ".html":
        if list(redacted_df.columns) != ["text"]:
            html_out = redacted_df.to_html(index=False)
        else:
            text_blob = "\n".join(redacted_df["text"].fillna("").astype(str).tolist())
            html_out = "<pre>" + html_lib.escape(text_blob) + "</pre>"
        with open(redacted_path, "w", encoding="utf-8") as handle:
            handle.write(html_out)
    else:
        redacted_df.to_csv(redacted_path, index=False)


def _predict_pii_columns(df: pd.DataFrame, model=None) -> list[str]:
    x, features = _build_feature_dataframe(df)
    active_model = model or get_scan_model()
    predictions = active_model.predict(
        x[
            [
                "length",
                "num_underscores",
                "num_digits",
                "has_at",
                "has_email_keyword",
                "pct_email_like",
                "pct_phone_like",
                "pct_ssn_like",
                "pct_ip_like",
                "avg_digits_per_val",
                "avg_val_len",
                "has_dob_pattern",
                "has_gender_term",
                "has_street_suffix",
                "has_city_name",
                "has_known_name",
                "has_zip_pattern",
                "has_phone_pattern",
            ]
        ]
    )
    return [col for col, is_pii in zip(features, predictions) if is_pii == 0]


def _apply_redactions(
    df: pd.DataFrame,
    pii_columns: list[str],
    aggressive: bool,
) -> tuple[pd.DataFrame, int, int, dict[str, int]]:
    redacted_df = df.copy()
    total_redacted = 0
    total_values = 0
    redacted_type_counts: dict[str, int] = {}

    for col in pii_columns:
        redacted_col, redacted_count, col_total, _, column_type_counts = scan_and_redact_column_with_details(
            df[col], col, aggressive=aggressive
        )
        redacted_df[col] = redacted_col
        total_redacted += redacted_count
        total_values += col_total
        for label, count in column_type_counts.items():
            redacted_type_counts[label] = redacted_type_counts.get(label, 0) + count

    return redacted_df, total_redacted, total_values, redacted_type_counts


def _persist_scan_result(
    *,
    context: ScanContext,
    filename: str,
    ext: str,
    risk_score: int,
    pii_columns: list[str],
    total_redacted: int,
    redacted_type_counts: dict[str, int],
    public_redacted_path: str,
) -> int:
    db = None
    try:
        pii_types_string = ",".join(pii_columns) if pii_columns else None
        db = SessionLocal()

        scan = ScanResult(
            user_id=context.user_id,
            company_id=context.company_id,
            filename=filename,
            file_type=ext.lstrip("."),
            risk_score=risk_score,
            pii_types_found=pii_types_string,
            redacted_type_counts=json.dumps(redacted_type_counts) if redacted_type_counts else None,
            total_pii_found=total_redacted,
            redacted_file_path=public_redacted_path,
            status="active",
            retention_expiration=build_retention_expiration(
                scanned_at=None,
                retention_days=resolve_retention_days(db, context.company_id, context.tier),
            ),
        )

        db.add(scan)
        db.commit()
        db.refresh(scan)
        logger.info(
            "Saved scan result id=%s user_id=%s file=%s",
            scan.id,
            context.user_id,
            filename,
        )
        record_audit_event(
            db,
            company_id=context.company_id,
            user_id=context.user_id,
            event_type="scan_created",
            event_category="scan",
            description=f"Scan created for file {filename}.",
            target_type="scan",
            target_id=str(scan.id),
            event_metadata={
                "file_type": ext.lstrip("."),
                "risk_score": risk_score,
                "total_redacted": total_redacted,
            },
        )
        db.commit()
        return scan.id
    except IntegrityError as exc:
        if db is not None:
            db.rollback()
        logger.exception(
            "Integrity error while persisting scan result user_id=%s file=%s",
            context.user_id,
            filename,
        )
        raise RuntimeError(
            "Failed to persist scan result due to integrity constraints. "
            "Verify user/company ids."
        ) from exc
    except Exception as exc:
        if db is not None:
            db.rollback()
        logger.exception(
            "Failed to persist scan result user_id=%s file=%s",
            context.user_id,
            filename,
        )
        raise RuntimeError("Failed to persist scan result.") from exc
    finally:
        if db is not None:
            db.close()


def run_scan_pipeline(
    *,
    file_bytes: bytes,
    filename: str,
    context: ScanContext,
    model=None,
    aggressive: bool = False,
) -> ScanPipelineResult:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type.")

    os.makedirs("redacted", exist_ok=True)

    df = _parse_to_dataframe(file_bytes=file_bytes, filename=filename, ext=ext)
    pii_columns = _predict_pii_columns(df, model=model)
    redacted_df, total_redacted, total_values, redacted_type_counts = _apply_redactions(
        df,
        pii_columns,
        aggressive,
    )

    file_id = str(uuid.uuid4())
    redacted_path = os.path.join("redacted", f"redacted_{file_id}{ext}")
    _write_redacted_file(redacted_df=redacted_df, redacted_path=redacted_path, ext=ext)

    risk_score = min(round((total_redacted / total_values) * 100), 100) if total_values > 0 else 0

    scan_id = _persist_scan_result(
        context=context,
        filename=filename,
        ext=ext,
        risk_score=risk_score,
        pii_columns=pii_columns,
        total_redacted=total_redacted,
        redacted_type_counts=redacted_type_counts,
        public_redacted_path=redacted_path,
    )

    logger.info(
        "Completed scan id=%s user_id=%s file=%s redacted_total=%s",
        scan_id,
        context.user_id,
        filename,
        total_redacted,
    )

    return ScanPipelineResult(
        filename=filename,
        pii_columns=pii_columns,
        redacted_file=redacted_path,
        risk_score=risk_score,
        redacted_count=total_redacted,
        total_values=total_values,
        redacted_type_counts=redacted_type_counts,
        scan_id=scan_id,
    )
