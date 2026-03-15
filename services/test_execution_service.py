from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from services.audit_service import record_audit_event
from services.test_management_service import get_managed_test_detail, list_managed_tests
from services.test_metrics_service import record_test_result

logger = logging.getLogger(__name__)

RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_PASSED = "passed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELED = "canceled"

RUN_TYPE_RECORDED = "recorded"
RUN_TYPE_FULL_SUITE = "full_suite"
RUN_TYPE_SINGLE_TEST = "single_test"
RUN_TYPE_CATEGORY = "category"

TRIGGER_SOURCE_MANUAL = "manual"
TRIGGER_SOURCE_USER = "user"
TRIGGER_SOURCE_SEEDED = "seeded"

EXECUTION_ENGINE_PYTEST = "pytest"
ACTIVE_RUN_STATUSES = {RUN_STATUS_QUEUED, RUN_STATUS_RUNNING}

DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_NAME = "governance_execution"
TEST_EXECUTION_TIMEOUT_SECONDS = max(30, int(os.getenv("TEST_EXECUTION_TIMEOUT_SECONDS", "900")))
MAX_LOG_CHARS = max(2000, int(os.getenv("TEST_EXECUTION_MAX_LOG_CHARS", "40000")))
_execution_lock = threading.Lock()


class DuplicateTestRunError(RuntimeError):
    pass


class UnsupportedTestExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedPytestCase:
    test_name: str
    file_path: str | None
    node_id: str
    status: str
    duration_ms: int | None
    output: str | None
    error_message: str | None


@dataclass(frozen=True)
class ParsedPytestReport:
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    cases: list[ParsedPytestCase]
    failure_summary: str | None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def parse_test_run_metadata(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def supports_pytest_execution(*, file_path: str | None = None, node_id: str | None = None) -> bool:
    normalized_file_path = str(file_path or "").strip().lower()
    normalized_node_id = str(node_id or "").strip().lower()
    return normalized_file_path.endswith(".py") or ".py::" in normalized_node_id


def _sanitize_log_output(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = value.replace("\x00", "").strip()
    if len(sanitized) <= MAX_LOG_CHARS:
        return sanitized
    return f"{sanitized[:MAX_LOG_CHARS]}\n...[truncated]..."


def _failure_summary_from_text(*, stdout: str | None, stderr: str | None) -> str | None:
    combined = "\n".join(part for part in [stdout, stderr] if part).strip()
    if not combined:
        return None
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    if not lines:
        return None
    return "\n".join(lines[:8])[:2000]


def _normalize_file_path(file_path: str | None) -> str | None:
    if not file_path:
        return None
    return str(Path(file_path).as_posix())


def _test_name_from_case(*, classname: str | None, name: str) -> str:
    normalized_classname = (classname or "").strip()
    class_name = normalized_classname.rsplit(".", 1)[-1] if normalized_classname else ""
    if class_name.startswith("Test") and "::" not in name:
        return f"{class_name}::{name}"
    return name


def _file_path_from_classname(classname: str | None) -> str | None:
    normalized = (classname or "").strip()
    if not normalized:
        return None
    parts = [part for part in normalized.split(".") if part]
    if not parts:
        return None
    if parts[-1].startswith("Test") and len(parts) > 1:
        parts = parts[:-1]
    if not parts:
        return None
    return f"{'/'.join(parts)}.py"


def _parse_duration_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return max(0, round(seconds * 1000))


def _collect_case_output(case_element: ET.Element) -> str | None:
    output_blocks: list[str] = []
    for child_tag in ("system-out", "system-err"):
        child = case_element.find(child_tag)
        if child is not None and child.text:
            output_blocks.append(child.text.strip())
    if not output_blocks:
        return None
    return _sanitize_log_output("\n\n".join(block for block in output_blocks if block))


def _collect_case_error(case_element: ET.Element) -> str | None:
    for child_tag in ("failure", "error", "skipped"):
        child = case_element.find(child_tag)
        if child is None:
            continue
        parts = [child.attrib.get("message"), child.text]
        message = "\n".join(part.strip() for part in parts if part and part.strip())
        if message:
            return _sanitize_log_output(message)
    return None


def parse_pytest_junit_report(report_path: str | Path) -> ParsedPytestReport:
    report_file = Path(report_path)
    if not report_file.exists():
        return ParsedPytestReport(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            cases=[],
            failure_summary=None,
        )

    try:
        root = ET.parse(report_file).getroot()
    except ET.ParseError:
        return ParsedPytestReport(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            cases=[],
            failure_summary="Pytest completed, but the JUnit report could not be parsed.",
        )

    case_elements = list(root.iter("testcase"))
    parsed_cases: list[ParsedPytestCase] = []
    failures: list[str] = []
    failed_tests = 0
    skipped_tests = 0

    for case_element in case_elements:
        name = case_element.attrib.get("name") or "unknown_test"
        classname = case_element.attrib.get("classname")
        file_path = _normalize_file_path(case_element.attrib.get("file") or _file_path_from_classname(classname))
        test_name = _test_name_from_case(classname=classname, name=name)
        node_id = f"{file_path}::{test_name}" if file_path else test_name
        has_failure = case_element.find("failure") is not None or case_element.find("error") is not None
        has_skip = case_element.find("skipped") is not None
        if has_failure:
            status = RUN_STATUS_FAILED
            failed_tests += 1
        elif has_skip:
            status = "skipped"
            skipped_tests += 1
        else:
            status = RUN_STATUS_PASSED

        error_message = _collect_case_error(case_element)
        output = _collect_case_output(case_element)
        if status == RUN_STATUS_FAILED and error_message:
            failures.append(f"{test_name}: {error_message.splitlines()[0]}")

        parsed_cases.append(
            ParsedPytestCase(
                test_name=test_name,
                file_path=file_path,
                node_id=node_id,
                status=status,
                duration_ms=_parse_duration_ms(case_element.attrib.get("time")),
                output=output,
                error_message=error_message,
            )
        )

    total_tests = len(parsed_cases)
    passed_tests = max(total_tests - failed_tests - skipped_tests, 0)
    failure_summary = "\n".join(failures[:5])[:2000] if failures else None
    return ParsedPytestReport(
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=failed_tests,
        skipped_tests=skipped_tests,
        cases=parsed_cases,
        failure_summary=failure_summary,
    )


def _metadata_targets(run: ComplianceTestRun) -> list[str]:
    metadata = parse_test_run_metadata(run.metadata_json)
    raw_targets = metadata.get("selected_node_ids")
    if not isinstance(raw_targets, list):
        return []
    return [str(item) for item in raw_targets if str(item).strip()]


def _active_run_exists(
    db: Session,
    *,
    organization_id: int,
    run_type: str,
    pytest_node_id: str | None = None,
    category: str | None = None,
) -> bool:
    query = db.query(ComplianceTestRun).filter(
        ComplianceTestRun.organization_id == organization_id,
        ComplianceTestRun.run_type == run_type,
        ComplianceTestRun.status.in_(tuple(ACTIVE_RUN_STATUSES)),
    )
    if pytest_node_id is not None:
        query = query.filter(ComplianceTestRun.pytest_node_id == pytest_node_id)
    if category is not None:
        query = query.filter(ComplianceTestRun.category == category)
    return query.first() is not None


def _create_execution_run(
    db: Session,
    *,
    organization_id: int,
    triggered_by_user_id: int | None,
    triggered_by_employee_id: int | None,
    run_type: str,
    category: str,
    suite_name: str,
    pytest_node_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ComplianceTestRun:
    run = ComplianceTestRun(
        organization_id=organization_id,
        triggered_by_user_id=triggered_by_user_id,
        triggered_by_employee_id=triggered_by_employee_id,
        run_type=run_type,
        trigger_source=TRIGGER_SOURCE_USER,
        execution_engine=EXECUTION_ENGINE_PYTEST,
        pytest_node_id=pytest_node_id,
        category=category,
        suite_name=suite_name,
        dataset_name=DEFAULT_DATASET_NAME,
        status=RUN_STATUS_QUEUED,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        accuracy_score=None,
        coverage_percent=None,
        report_link=None,
        started_at=None,
        completed_at=None,
        return_code=None,
        stdout=None,
        stderr=None,
        failure_summary=None,
        metadata_json=_json_dumps(metadata),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_audit_event(
        db,
        company_id=organization_id,
        user_id=triggered_by_user_id,
        event_type="test_execution_queued",
        event_category="testing",
        description=f"Queued {run_type.replace('_', ' ')} test execution.",
        target_type="compliance_test_run",
        target_id=str(run.id),
        event_metadata={"run_type": run_type, "category": category, "pytest_node_id": pytest_node_id},
    )
    db.commit()
    db.refresh(run)
    return run


def _single_test_targets(db: Session, *, organization_id: int, test_id: str) -> dict[str, Any]:
    detail = get_managed_test_detail(db, organization_id=organization_id, test_id=test_id)
    node_id = str(detail["test_node_id"])
    file_path = detail.get("file_path")
    if not supports_pytest_execution(file_path=file_path, node_id=node_id):
        raise UnsupportedTestExecutionError("Only backend Python tests can be executed from this workspace.")
    return detail


def start_full_suite_run(
    db: Session,
    *,
    organization_id: int,
    triggered_by_user_id: int | None,
    triggered_by_employee_id: int | None,
) -> ComplianceTestRun:
    with _execution_lock:
        if _active_run_exists(db, organization_id=organization_id, run_type=RUN_TYPE_FULL_SUITE):
            raise DuplicateTestRunError("A full suite run is already queued or running for this organization.")
        return _create_execution_run(
            db,
            organization_id=organization_id,
            triggered_by_user_id=triggered_by_user_id,
            triggered_by_employee_id=triggered_by_employee_id,
            run_type=RUN_TYPE_FULL_SUITE,
            category="backend tests",
            suite_name="Backend pytest suite",
            metadata={"target": "full_suite"},
        )


def start_single_test_run(
    db: Session,
    *,
    organization_id: int,
    triggered_by_user_id: int | None,
    triggered_by_employee_id: int | None,
    test_id: str,
) -> ComplianceTestRun:
    detail = _single_test_targets(db, organization_id=organization_id, test_id=test_id)
    node_id = str(detail["test_node_id"])
    with _execution_lock:
        if _active_run_exists(
            db,
            organization_id=organization_id,
            run_type=RUN_TYPE_SINGLE_TEST,
            pytest_node_id=node_id,
        ):
            raise DuplicateTestRunError("This test already has a queued or running execution.")
        return _create_execution_run(
            db,
            organization_id=organization_id,
            triggered_by_user_id=triggered_by_user_id,
            triggered_by_employee_id=triggered_by_employee_id,
            run_type=RUN_TYPE_SINGLE_TEST,
            category=str(detail["category"]),
            suite_name=str(detail["suite_name"] or detail["test_name"]),
            pytest_node_id=node_id,
            metadata={
                "target": "single_test",
                "selected_test_id": test_id,
                "selected_test_name": detail["test_name"],
                "selected_node_ids": [node_id],
            },
        )


def start_category_run(
    db: Session,
    *,
    organization_id: int,
    triggered_by_user_id: int | None,
    triggered_by_employee_id: int | None,
    category_name: str,
) -> ComplianceTestRun:
    inventory = list_managed_tests(db, organization_id=organization_id, category=category_name, sort="name")
    node_ids = sorted(
        {
            str(item["test_node_id"])
            for item in inventory["tests"]
            if supports_pytest_execution(file_path=item.get("file_path"), node_id=item.get("test_node_id"))
        }
    )
    if not node_ids:
        raise UnsupportedTestExecutionError("No backend Python tests are available for this category.")
    with _execution_lock:
        if _active_run_exists(
            db,
            organization_id=organization_id,
            run_type=RUN_TYPE_CATEGORY,
            category=category_name,
        ):
            raise DuplicateTestRunError("This category already has a queued or running execution.")
        return _create_execution_run(
            db,
            organization_id=organization_id,
            triggered_by_user_id=triggered_by_user_id,
            triggered_by_employee_id=triggered_by_employee_id,
            run_type=RUN_TYPE_CATEGORY,
            category=category_name,
            suite_name=f"{category_name} pytest run",
            metadata={
                "target": "category",
                "selected_node_ids": node_ids,
                "target_count": len(node_ids),
            },
        )


def queue_test_execution(
    run_id: int,
    *,
    background_tasks: BackgroundTasks | None = None,
    execute_inline: bool = False,
) -> None:
    if execute_inline or background_tasks is None:
        execute_test_run(run_id)
        return
    background_tasks.add_task(execute_test_run, run_id)


def _command_for_run(run: ComplianceTestRun) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--disable-warnings",
    ]
    targets = _metadata_targets(run)
    if run.run_type == RUN_TYPE_SINGLE_TEST and run.pytest_node_id:
        targets = [run.pytest_node_id]
    return command + targets


def _persist_case_results(db: Session, *, run: ComplianceTestRun, report: ParsedPytestReport) -> None:
    for parsed_case in report.cases:
        record_test_result(
            db,
            test_run_id=run.id,
            test_name=parsed_case.test_name,
            test_node_id=parsed_case.node_id,
            dataset_name=run.dataset_name,
            expected_result=None,
            actual_result=None,
            status=parsed_case.status,
            confidence_score=None,
            file_path=parsed_case.file_path,
            description=None,
            duration_ms=parsed_case.duration_ms,
            output=parsed_case.output,
            error_message=parsed_case.error_message,
            created_by_employee_id=run.triggered_by_employee_id,
            created_by_user_id=run.triggered_by_user_id,
        )


def _final_run_status(*, report: ParsedPytestReport, return_code: int) -> str:
    if report.failed_tests or return_code != 0:
        return RUN_STATUS_FAILED
    if report.total_tests and report.skipped_tests == report.total_tests:
        return "skipped"
    return RUN_STATUS_PASSED


def execute_test_run(run_id: int) -> None:
    db = SessionLocal()
    report_path: str | None = None
    try:
        run = db.query(ComplianceTestRun).filter(ComplianceTestRun.id == run_id).first()
        if run is None:
            raise RuntimeError("Test run not found")

        run.status = RUN_STATUS_RUNNING
        run.started_at = run.started_at or _utcnow()
        db.add(run)
        record_audit_event(
            db,
            company_id=run.organization_id,
            user_id=run.triggered_by_user_id,
            event_type="test_execution_started",
            event_category="testing",
            description=f"Started {run.run_type.replace('_', ' ')} test execution.",
            target_type="compliance_test_run",
            target_id=str(run.id),
            event_metadata={"run_type": run.run_type, "category": run.category, "pytest_node_id": run.pytest_node_id},
        )
        db.commit()
        db.refresh(run)

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as handle:
            report_path = handle.name

        command = _command_for_run(run) + [f"--junitxml={report_path}"]
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        completed = subprocess.run(
            command,
            cwd=str(DEFAULT_REPOSITORY_ROOT),
            capture_output=True,
            text=True,
            timeout=TEST_EXECUTION_TIMEOUT_SECONDS,
            env=environment,
            check=False,
        )

        db.query(ComplianceTestCaseResult).filter(ComplianceTestCaseResult.test_run_id == run.id).delete()
        report = parse_pytest_junit_report(report_path)
        _persist_case_results(db, run=run, report=report)
        db.refresh(run)
        run.total_tests = report.total_tests or run.total_tests
        run.passed_tests = report.passed_tests or run.passed_tests
        run.failed_tests = report.failed_tests or run.failed_tests
        run.skipped_tests = report.skipped_tests or run.skipped_tests
        completed_count = run.passed_tests + run.failed_tests
        run.accuracy_score = (run.passed_tests / completed_count) if completed_count else None
        run.return_code = completed.returncode
        run.stdout = _sanitize_log_output(completed.stdout)
        run.stderr = _sanitize_log_output(completed.stderr)
        run.failure_summary = report.failure_summary or _failure_summary_from_text(
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        run.status = _final_run_status(report=report, return_code=completed.returncode)
        run.completed_at = _utcnow()
        db.add(run)
        record_audit_event(
            db,
            company_id=run.organization_id,
            user_id=run.triggered_by_user_id,
            event_type="test_execution_completed" if run.status == RUN_STATUS_PASSED else "test_execution_failed",
            event_category="testing",
            description=f"Completed {run.run_type.replace('_', ' ')} test execution with status {run.status}.",
            target_type="compliance_test_run",
            target_id=str(run.id),
            event_metadata={
                "run_type": run.run_type,
                "status": run.status,
                "return_code": run.return_code,
                "total_tests": run.total_tests,
                "failed_tests": run.failed_tests,
            },
        )
        db.commit()
    except subprocess.TimeoutExpired as exc:
        db.rollback()
        run = db.query(ComplianceTestRun).filter(ComplianceTestRun.id == run_id).first()
        if run is not None:
            run.status = RUN_STATUS_FAILED
            run.completed_at = _utcnow()
            run.return_code = None
            run.stdout = _sanitize_log_output(exc.stdout if isinstance(exc.stdout, str) else None)
            run.stderr = _sanitize_log_output(exc.stderr if isinstance(exc.stderr, str) else None)
            run.failure_summary = f"Test execution timed out after {TEST_EXECUTION_TIMEOUT_SECONDS} seconds."
            db.add(run)
            record_audit_event(
                db,
                company_id=run.organization_id,
                user_id=run.triggered_by_user_id,
                event_type="test_execution_failed",
                event_category="testing",
                description="Test execution timed out.",
                target_type="compliance_test_run",
                target_id=str(run.id),
                event_metadata={"run_type": run.run_type, "timeout_seconds": TEST_EXECUTION_TIMEOUT_SECONDS},
            )
            db.commit()
        logger.warning("Test execution run %s timed out.", run_id)
    except Exception as exc:
        db.rollback()
        run = db.query(ComplianceTestRun).filter(ComplianceTestRun.id == run_id).first()
        if run is not None:
            run.status = RUN_STATUS_FAILED
            run.completed_at = _utcnow()
            run.failure_summary = str(exc)[:2000]
            db.add(run)
            record_audit_event(
                db,
                company_id=run.organization_id,
                user_id=run.triggered_by_user_id,
                event_type="test_execution_failed",
                event_category="testing",
                description="Test execution failed unexpectedly.",
                target_type="compliance_test_run",
                target_id=str(run.id),
                event_metadata={"run_type": run.run_type, "reason": str(exc)},
            )
            db.commit()
        logger.exception("Unexpected failure executing test run %s", run_id)
    finally:
        if report_path:
            try:
                os.remove(report_path)
            except OSError:
                pass
        db.close()
