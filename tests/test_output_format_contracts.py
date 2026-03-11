from __future__ import annotations

import json
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from services import scan_service


def _make_local_test_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".test_tmp" / f"output_contracts_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def test_json_output_is_valid_json_with_results_array():
    base = _make_local_test_dir()
    output_path = base / "redacted.json"
    frame = pd.DataFrame(
        [
            {"email": "[REDACTED_EMAIL]", "name": "[REDACTED_NAME]"},
            {"email": "[REDACTED_EMAIL]", "name": "Ada"},
        ]
    )

    try:
        scan_service._write_redacted_file(frame, str(output_path), ".json", scan_id=123)
        with open(output_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        assert payload["scan_id"] == 123
        assert isinstance(payload["results"], list)
        assert payload["results"][0]["email"] == "[REDACTED_EMAIL]"
        assert payload["results"][0]["name"] == "[REDACTED_NAME]"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_xml_output_sanitizes_tags_with_spaces_and_preserves_original_metadata():
    base = _make_local_test_dir()
    output_path = base / "redacted.xml"
    frame = pd.DataFrame([{"customer email": "[REDACTED_EMAIL]"}])

    try:
        scan_service._write_redacted_file(frame, str(output_path), ".xml")
        tree = ET.parse(output_path)
        root = tree.getroot()
        child = root.find("./item/customer_email")

        assert root.tag == "results"
        assert child is not None
        assert child.attrib["original"] == "customer email"
        assert child.text == "[REDACTED_EMAIL]"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_xml_output_handles_malformed_column_names_safely():
    base = _make_local_test_dir()
    output_path = base / "malformed.xml"
    frame = pd.DataFrame([{"123 customer email!": "[REDACTED_EMAIL]"}])

    try:
        scan_service._write_redacted_file(frame, str(output_path), ".xml")
        tree = ET.parse(output_path)
        root = tree.getroot()
        child = root.find("./item/field_123_customer_email")

        assert child is not None
        assert child.attrib["original"] == "123 customer email!"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_sanitize_xml_tag_normalizes_invalid_names():
    assert scan_service.sanitize_xml_tag("customer email") == "customer_email"
    assert scan_service.sanitize_xml_tag("123 customer email!") == "field_123_customer_email"
    assert scan_service.sanitize_xml_tag("$$$") == "field"
