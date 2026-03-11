from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from database.models.scan_results import ScanResult
from services import scan_service
from services.audit_report_service import generate_audit_report_html
from utils import redaction
from utils.pii_taxonomy import GDPR_PERSONAL_DATA, PII_EMAIL, PII_PHONE


class _HeuristicModel:
    def predict(self, frame):
        predictions = []
        for _, row in frame.iterrows():
            looks_like_pii = (
                bool(row["has_email_keyword"])
                or float(row["pct_email_like"]) > 0
                or float(row["pct_phone_like"]) > 0
                or float(row["pct_ssn_like"]) > 0
                or float(row["pct_ip_like"]) > 0
                or bool(row["has_street_suffix"])
                or bool(row["has_known_name"])
            )
            predictions.append(0 if looks_like_pii else 1)
        return predictions


def _load_validation_cases() -> dict:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "pii_detection_validation_cases.json"
    with open(fixture_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _detect(frame: pd.DataFrame):
    return scan_service._predict_pii_columns(frame, model=_HeuristicModel())


def test_email_detection_includes_explainable_signals():
    cases = _load_validation_cases()
    frame = pd.DataFrame({"email": cases["pii_examples"]["email"]})

    pii_columns, detections = _detect(frame)

    assert pii_columns == ["email"]
    assert detections[0]["detected_type"] == PII_EMAIL
    assert detections[0]["policy_categories"] == [GDPR_PERSONAL_DATA, "HIPAA_IDENTIFIER"]
    assert detections[0]["confidence_score"] == 0.98
    assert "pattern_match_email_regex" in detections[0]["signals"]
    assert "column_name_keyword_email" in detections[0]["signals"]
    assert "ml_model_prediction" in detections[0]["signals"]


def test_phone_detection_is_identified_with_signal_based_score():
    cases = _load_validation_cases()
    frame = pd.DataFrame({"phone_number": cases["pii_examples"]["phone_number"]})

    pii_columns, detections = _detect(frame)

    assert pii_columns == ["phone_number"]
    assert detections[0]["detected_type"] == PII_PHONE
    assert GDPR_PERSONAL_DATA in detections[0]["policy_categories"]
    assert detections[0]["confidence_score"] == 0.98
    assert "pattern_match_phone_regex" in detections[0]["signals"]
    assert "column_name_keyword_phone" in detections[0]["signals"]


def test_false_positive_prevention_keeps_product_id_out_of_pii_results():
    cases = _load_validation_cases()
    frame = pd.DataFrame({"product_id": cases["non_pii_examples"]["product_id"]})

    pii_columns, detections = _detect(frame)

    assert pii_columns == []
    assert detections == []


def test_detection_scores_are_reproducible_for_identical_input():
    cases = _load_validation_cases()
    frame = pd.DataFrame(
        {
            "email": cases["pii_examples"]["email"],
            "phone_number": cases["pii_examples"]["phone_number"],
        }
    )

    first_columns, first_detections = _detect(frame)
    second_columns, second_detections = _detect(frame)

    assert first_columns == second_columns
    assert first_detections == second_detections


def test_report_includes_detection_reasoning_section():
    detection_results = [
        {
            "column": "email",
            "detected_type": PII_EMAIL,
            "display_name": "Email Address",
            "policy_categories": [GDPR_PERSONAL_DATA, "HIPAA_IDENTIFIER"],
            "confidence_score": 0.98,
            "signals": [
                "pattern_match_email_regex",
                "column_name_keyword_email",
                "ml_model_prediction",
            ],
        }
    ]
    scan = ScanResult(
        id=42,
        filename="customers.csv",
        file_type="csv",
        risk_score=40,
        pii_types_found="email",
        redacted_type_counts=json.dumps(
            scan_service.build_scan_result_metadata(
                redacted_type_counts={PII_EMAIL: 2},
                detection_results=detection_results,
            )
        ),
        total_pii_found=2,
    )

    html = generate_audit_report_html(scan)

    assert "Detection Reasoning" in html
    assert PII_EMAIL in html
    assert "GDPR Personal Data" in html
    assert "Email Address" in html
    assert "0.98" in html
    assert "pattern_match_email_regex" in html


def test_redactions_include_taxonomy_placeholder(monkeypatch):
    class _FakeResult:
        entity_type = "EMAIL_ADDRESS"

    monkeypatch.setattr(redaction.analyzer, "analyze", lambda text, language="en": [_FakeResult()])
    monkeypatch.setattr(
        redaction.anonymizer,
        "anonymize",
        lambda text, analyzer_results, operators: type(
            "_Result",
            (),
            {"text": operators["EMAIL_ADDRESS"].params["new_value"]},
        )(),
    )

    series = pd.Series(["ada@example.com"])
    redacted_series, redacted_count, total_values, _, type_counts = redaction.scan_and_redact_column_with_details(
        series,
        "email",
    )

    assert redacted_series.iloc[0] == "[REDACTED_PII_EMAIL]"
    assert redacted_count == 1
    assert total_values == 1
    assert type_counts[PII_EMAIL] == 1
