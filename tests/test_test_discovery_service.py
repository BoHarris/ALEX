from pathlib import Path

from services.test_discovery_service import build_test_node_id, discover_pytest_cases, split_test_node_id


def test_discover_pytest_cases_returns_individual_functions_and_methods():
    test_file = Path("tests/test_generated_discovery_suite.py")
    try:
        test_file.write_text(
            """
def test_detect_email():
    \"\"\"Email detection stays separate.\"\"\"
    assert True

def test_detect_phone():
    assert True

class TestRiskSignals:
    def test_detect_ssn(self):
        assert True
""".strip(),
            encoding="utf-8",
        )

        discovered = discover_pytest_cases("tests")
        node_ids = {item["node_id"] for item in discovered}
        assert "tests/test_generated_discovery_suite.py::test_detect_email" in node_ids
        assert "tests/test_generated_discovery_suite.py::test_detect_phone" in node_ids
        assert "tests/test_generated_discovery_suite.py::TestRiskSignals::test_detect_ssn" in node_ids
    finally:
        if test_file.exists():
            test_file.unlink()


def test_build_and_split_test_node_id_round_trip():
    node_id = build_test_node_id(test_name="test_detect_email", file_path="tests/privacy_tests.py")
    file_path, test_name = split_test_node_id(node_id)
    assert node_id == "tests/privacy_tests.py::test_detect_email"
    assert file_path == "tests/privacy_tests.py"
    assert test_name == "test_detect_email"


def test_split_test_node_id_preserves_class_method_names():
    file_path, test_name = split_test_node_id("tests/privacy_tests.py::TestRiskSignals::test_detect_ssn")
    assert file_path == "tests/privacy_tests.py"
    assert test_name == "TestRiskSignals::test_detect_ssn"
