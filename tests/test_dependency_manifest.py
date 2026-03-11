from __future__ import annotations

from pathlib import Path


def _load_requirements() -> dict[str, str]:
    requirements_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    parsed: dict[str, str] = {}
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        parsed[name] = version
    return parsed


def test_requirements_manifest_exists_and_pins_versions():
    requirements_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    assert requirements_path.is_file()

    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        assert "==" in line, f"Dependency is not pinned: {line}"


def test_requirements_manifest_includes_critical_backend_dependencies():
    requirements = _load_requirements()

    expected = {
        "alembic",
        "fastapi",
        "python-dotenv",
        "python-jose",
        "python-multipart",
        "SQLAlchemy",
        "uvicorn",
        "webauthn",
        "pandas",
        "numpy",
        "xgboost",
        "scikit-learn",
        "PyPDF2",
        "python-docx",
        "reportlab",
        "presidio-analyzer",
        "presidio-anonymizer",
        "openpyxl",
        "xlrd",
    }

    assert expected.issubset(requirements.keys())
