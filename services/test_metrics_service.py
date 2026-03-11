from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter

from sqlalchemy.orm import Session

from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from services.test_failure_task_service import upsert_failure_task_for_result
from services.test_discovery_service import split_test_node_id


NON_PII_SENTINELS = {"", "NONE", "NON_PII", "NOT_PII", "NO_DETECTION", "NULL"}


@dataclass(frozen=True)
class RecordedTestResult:
    result: ComplianceTestCaseResult
    duration_ms: int


def create_tracked_test_run(
    db: Session,
    *,
    organization_id: int,
    category: str,
    suite_name: str,
    status: str = "running",
    dataset_name: str | None = None,
    coverage_percent: Decimal | None = None,
    report_link: str | None = None,
) -> ComplianceTestRun:
    run = ComplianceTestRun(
        organization_id=organization_id,
        category=category,
        suite_name=suite_name,
        dataset_name=dataset_name,
        status=status,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        accuracy_score=None,
        coverage_percent=coverage_percent,
        report_link=report_link,
    )
    db.add(run)
    db.flush()
    return run


def record_test_result(
    db: Session,
    *,
    test_run_id: int,
    test_name: str,
    test_node_id: str | None = None,
    dataset_name: str | None,
    expected_result: str | None,
    actual_result: str | None,
    status: str,
    confidence_score: float | None,
    file_path: str | None = None,
    file_name: str | None = None,
    description: str | None = None,
    duration_ms: int | None = None,
    output: str | None = None,
    error_message: str | None = None,
    created_by_employee_id: int | None = None,
    created_by_user_id: int | None = None,
) -> ComplianceTestCaseResult:
    derived_file_path, derived_test_name = split_test_node_id(test_node_id) if test_node_id else (None, test_name)
    result = ComplianceTestCaseResult(
        test_run_id=test_run_id,
        name=derived_test_name,
        dataset_name=dataset_name,
        file_name=file_path or derived_file_path or file_name,
        description=description,
        expected_result=expected_result,
        actual_result=actual_result,
        status=status.lower(),
        confidence_score=Decimal(str(round(confidence_score, 4))) if confidence_score is not None else None,
        duration_ms=duration_ms,
        output=output,
        error_message=error_message,
    )
    db.add(result)
    db.flush()
    run = recalculate_test_run_summary(db, test_run_id=test_run_id)
    if result.status == "failed":
        upsert_failure_task_for_result(
            db,
            run=run,
            result=result,
            actor_employee_id=created_by_employee_id,
            actor_user_id=created_by_user_id,
        )
    return result


def track_test_execution(
    db: Session,
    *,
    test_run_id: int,
    test_name: str,
    test_node_id: str | None = None,
    dataset_name: str | None,
    expected_result: str | None,
    actual_result: str | None,
    confidence_score: float | None,
    file_path: str | None = None,
    file_name: str | None = None,
    description: str | None = None,
    output: str | None = None,
    error_message: str | None = None,
    created_by_employee_id: int | None = None,
    created_by_user_id: int | None = None,
) -> RecordedTestResult:
    started_at = perf_counter()
    normalized_expected = (expected_result or "").strip().upper()
    normalized_actual = (actual_result or "").strip().upper()
    status = "passed" if normalized_expected == normalized_actual else "failed"
    result = record_test_result(
        db,
        test_run_id=test_run_id,
        test_name=test_name,
        test_node_id=test_node_id,
        dataset_name=dataset_name,
        expected_result=normalized_expected or None,
        actual_result=normalized_actual or None,
        status=status,
        confidence_score=confidence_score,
        file_path=file_path,
        file_name=file_name,
        description=description,
        duration_ms=round((perf_counter() - started_at) * 1000),
        output=output,
        error_message=error_message,
        created_by_employee_id=created_by_employee_id,
        created_by_user_id=created_by_user_id,
    )
    return RecordedTestResult(result=result, duration_ms=result.duration_ms or 0)


def recalculate_test_run_summary(db: Session, *, test_run_id: int) -> ComplianceTestRun:
    run = db.query(ComplianceTestRun).filter(ComplianceTestRun.id == test_run_id).first()
    if run is None:
        raise ValueError("Test run not found")
    cases = db.query(ComplianceTestCaseResult).filter(ComplianceTestCaseResult.test_run_id == test_run_id).all()
    run.total_tests = len(cases)
    run.passed_tests = sum(1 for case in cases if case.status == "passed")
    run.failed_tests = sum(1 for case in cases if case.status == "failed")
    run.skipped_tests = sum(1 for case in cases if case.status == "skipped")
    completed = run.passed_tests + run.failed_tests
    run.accuracy_score = Decimal(str(round((run.passed_tests / completed), 4))) if completed else Decimal("0")
    if run.failed_tests:
        run.status = "failed"
    elif run.total_tests and run.passed_tests == run.total_tests:
        run.status = "passed"
    elif run.skipped_tests and run.total_tests == run.skipped_tests:
        run.status = "skipped"
    else:
        run.status = "running"
    db.add(run)
    db.flush()
    return run


def list_test_results(
    db: Session,
    *,
    organization_id: int,
    limit: int = 50,
    dataset_name: str | None = None,
    test_name: str | None = None,
    status: str | None = None,
):
    query = (
        db.query(ComplianceTestCaseResult, ComplianceTestRun)
        .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
        .filter(ComplianceTestRun.organization_id == organization_id)
    )
    if dataset_name:
        query = query.filter(ComplianceTestCaseResult.dataset_name == dataset_name)
    if test_name:
        query = query.filter(ComplianceTestCaseResult.name == test_name)
    if status:
        query = query.filter(ComplianceTestCaseResult.status == status.lower())
    return query.order_by(ComplianceTestCaseResult.last_run_at.desc()).limit(limit).all()


def list_test_runs(
    db: Session,
    *,
    organization_id: int,
    limit: int = 25,
    dataset_name: str | None = None,
    suite_name: str | None = None,
):
    query = db.query(ComplianceTestRun).filter(ComplianceTestRun.organization_id == organization_id)
    if dataset_name:
        query = query.filter(ComplianceTestRun.dataset_name == dataset_name)
    if suite_name:
        query = query.filter(ComplianceTestRun.suite_name == suite_name)
    return query.order_by(ComplianceTestRun.run_at.desc()).limit(limit).all()


def compute_test_metrics(
    db: Session,
    *,
    organization_id: int,
    dataset_name: str | None = None,
):
    rows = list_test_results(db, organization_id=organization_id, limit=5000, dataset_name=dataset_name)
    total = len(rows)
    passed = sum(1 for result, _ in rows if result.status == "passed")
    failed = sum(1 for result, _ in rows if result.status == "failed")

    false_positive = 0
    false_negative = 0
    for result, _ in rows:
        expected = (result.expected_result or "").strip().upper()
        actual = (result.actual_result or "").strip().upper()
        expected_is_non_pii = expected in NON_PII_SENTINELS
        actual_is_non_pii = actual in NON_PII_SENTINELS
        if expected_is_non_pii and not actual_is_non_pii:
            false_positive += 1
        elif not expected_is_non_pii and actual_is_non_pii:
            false_negative += 1

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "test_pass_rate": round((passed / total), 4) if total else 0.0,
        "detection_accuracy": round((passed / total), 4) if total else 0.0,
        "false_positive_rate": round((false_positive / total), 4) if total else 0.0,
        "false_negative_rate": round((false_negative / total), 4) if total else 0.0,
    }
