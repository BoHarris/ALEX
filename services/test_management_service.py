from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta, timezone
from statistics import mean
from urllib.parse import quote, unquote

from sqlalchemy.orm import Session

from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_failure_task import ComplianceTestFailureTask
from database.models.compliance_test_run import ComplianceTestRun
from services.test_failure_task_service import get_failure_task_for_test
from services.test_discovery_service import (
    build_test_node_id,
    infer_test_category,
    normalize_test_file_path,
    split_test_node_id,
    discover_repository_tests,
)

CATEGORY_DESCRIPTIONS = {
    "API tests": "Contract, routing, and backend integration checks.",
    "security tests": "Authentication, authorization, and hardening coverage.",
    "privacy tests": "PII detection, taxonomy, and redaction validation.",
    "UI tests": "Workflow, rendering, and interaction regressions.",
    "integration tests": "Cross-system end-to-end and environment validation.",
}

SORT_KEYS = {
    "last_run": lambda item: item["last_run_timestamp"] or "",
    "pass_rate": lambda item: item["pass_rate"],
    "failures": lambda item: item["failed_runs"],
    "flakiness": lambda item: item["flake_rate"],
    "name": lambda item: item["test_name"].lower(),
}


ACTIVE_RUN_STATUSES = {"queued", "running"}
RUN_TYPE_FULL_SUITE = "full_suite"


def _parse_run_metadata(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _supports_pytest_execution(*, file_path: str | None = None, node_id: str | None = None) -> bool:
    normalized_file_path = str(file_path or "").strip().lower()
    normalized_node_id = str(node_id or "").strip().lower()
    return normalized_file_path.endswith(".py") or ".py::" in normalized_node_id


def encode_test_id(*, node_id: str | None = None, category: str | None = None, test_name: str, file_path: str | None = None) -> str:
    canonical_node_id = node_id or build_test_node_id(test_name=test_name, file_path=file_path, category=category)
    return quote(canonical_node_id, safe="")


def decode_test_id(test_id: str) -> str:
    return unquote(test_id)


def _status_rank(status: str) -> int:
    normalized = (status or "").lower()
    if normalized == "failed":
        return 4
    if normalized == "skipped":
        return 3
    if normalized == "running":
        return 2
    if normalized == "passed":
        return 1
    return 0


def _normalize_status(value: str | None) -> str:
    text = (value or "").strip().lower()
    return text or "unknown"


def _coerce_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _history_row(case: ComplianceTestCaseResult, run: ComplianceTestRun) -> dict[str, object]:
    finished_at = _coerce_datetime(case.last_run_at) or _coerce_datetime(run.completed_at) or _coerce_datetime(run.run_at)
    started_at = _coerce_datetime(run.started_at)
    file_path = normalize_test_file_path(case.file_name)
    test_node_id = build_test_node_id(test_name=case.name, file_path=file_path, category=run.category)
    if started_at is None and finished_at is not None and case.duration_ms is not None:
        started_at = finished_at - timedelta(milliseconds=max(case.duration_ms, 0))
    return {
        "result_id": case.id,
        "run_id": run.id,
        "run_type": run.run_type,
        "run_status": _normalize_status(run.status),
        "trigger_source": run.trigger_source,
        "execution_engine": run.execution_engine,
        "return_code": run.return_code,
        "failure_summary": run.failure_summary,
        "metadata": _parse_run_metadata(run.metadata_json),
        "test_node_id": test_node_id,
        "test_name": case.name,
        "suite_name": run.suite_name,
        "dataset_name": case.dataset_name or run.dataset_name,
        "category": run.category,
        "status": _normalize_status(case.status),
        "duration_ms": case.duration_ms,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "last_run_timestamp": finished_at.isoformat() if finished_at else None,
        "expected_result": case.expected_result,
        "actual_result": case.actual_result,
        "confidence_score": float(case.confidence_score) if case.confidence_score is not None else None,
        "output": case.output,
        "error_message": case.error_message,
        "description": case.description,
        "file_path": file_path,
        "file_name": file_path,
        "environment": case.dataset_name or run.dataset_name or "default",
        "build_version": None,
        "execution_supported": _supports_pytest_execution(file_path=file_path, node_id=test_node_id),
    }


def _compute_streak(history: list[dict[str, object]], target_status: str) -> int:
    streak = 0
    for item in history:
        if item["status"] != target_status:
            break
        streak += 1
    return streak


def _compute_flake_rate(history: list[dict[str, object]]) -> float:
    terminal_statuses = [item["status"] for item in history if item["status"] in {"passed", "failed"}]
    if len(terminal_statuses) < 2:
        return 0.0
    transitions = sum(1 for index in range(1, len(terminal_statuses)) if terminal_statuses[index] != terminal_statuses[index - 1])
    return round(transitions / (len(terminal_statuses) - 1), 2)


def _compute_quality_label(
    history: list[dict[str, object]],
    *,
    current_fail_streak: int,
    current_pass_streak: int,
    flaky: bool,
) -> str:
    if not history:
        return "Not Run"
    latest_status = history[0]["status"]
    if latest_status == "failed":
        return "Regressed" if current_fail_streak == 1 else "Failing"
    if latest_status == "passed" and current_pass_streak >= 1 and any(item["status"] == "failed" for item in history[1:4]):
        return "Improving"
    if flaky:
        return "Flaky"
    if latest_status == "skipped":
        return "Skipped"
    return "Stable"


def _compute_trend(history: list[dict[str, object]]) -> str:
    statuses = [item["status"] for item in history if item["status"] in {"passed", "failed"}]
    if not statuses:
        return "not_run"
    if statuses[0] == "failed":
        return "regressed" if any(status == "passed" for status in statuses[1:5]) else "failing"
    if statuses[0] == "passed" and any(status == "failed" for status in statuses[1:4]):
        return "improving"
    if len(set(statuses[:5])) > 1:
        return "unstable"
    return "stable"


def _build_discovered_test_inventory_item(discovered_test: dict[str, str | None]) -> dict[str, object]:
    test_name = str(discovered_test.get("test_name") or "")
    file_path = normalize_test_file_path(discovered_test.get("file_path"))
    node_id = str(discovered_test.get("node_id") or build_test_node_id(test_name=test_name, file_path=file_path))
    category = str(discovered_test.get("category") or infer_test_category(file_path, test_name))
    suite_name = Path(file_path).name if file_path else category
    execution_supported = _supports_pytest_execution(file_path=file_path, node_id=node_id)
    return {
        "test_id": encode_test_id(node_id=node_id, test_name=test_name),
        "test_node_id": node_id,
        "test_name": test_name,
        "category": category,
        "suite_name": suite_name,
        "status": "not_run",
        "description": discovered_test.get("description"),
        "file_path": file_path,
        "file_name": file_path,
        "expected_result": None,
        "actual_result": None,
        "confidence_score": None,
        "latest_environment": "repository",
        "total_runs": 0,
        "passed_runs": 0,
        "failed_runs": 0,
        "skipped_runs": 0,
        "pass_rate": 0.0,
        "flake_rate": 0.0,
        "flaky": False,
        "quality_label": "Not Run",
        "average_duration_ms": None,
        "last_duration_ms": None,
        "last_run_timestamp": None,
        "last_successful_run": None,
        "last_failed_run": None,
        "latest_failure_reason": None,
        "latest_run_id": None,
        "latest_result_id": None,
        "execution_supported": execution_supported,
        "execution_engine": "pytest" if execution_supported else None,
        "current_pass_streak": 0,
        "current_fail_streak": 0,
        "trend": "not_run",
        "history": [],
        "latest_execution": None,
    }


def _summarize_test_history(node_id: str, rows: list[tuple[ComplianceTestCaseResult, ComplianceTestRun]]) -> dict[str, object]:
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            _coerce_datetime(row[0].last_run_at) or _coerce_datetime(row[1].completed_at) or _coerce_datetime(row[1].run_at) or datetime.min.replace(tzinfo=timezone.utc),
            row[1].id,
            row[0].id,
        ),
        reverse=True,
    )
    history = [_history_row(case, run) for case, run in ordered_rows]
    latest_case, latest_run = ordered_rows[0]
    file_path, _ = split_test_node_id(node_id)
    effective_file_path = file_path or normalize_test_file_path(latest_case.file_name)
    statuses = [item["status"] for item in history]
    passed_runs = statuses.count("passed")
    failed_runs = statuses.count("failed")
    skipped_runs = statuses.count("skipped")
    total_runs = len(history)
    pass_rate = round((passed_runs / total_runs) * 100, 2) if total_runs else 0.0
    average_duration = round(mean([item["duration_ms"] for item in history if item["duration_ms"] is not None]), 2) if any(item["duration_ms"] is not None for item in history) else None
    last_successful_run = next((item["last_run_timestamp"] for item in history if item["status"] == "passed"), None)
    last_failed_run = next((item["last_run_timestamp"] for item in history if item["status"] == "failed"), None)
    latest_failure_reason = next((item["error_message"] for item in history if item["status"] == "failed" and item["error_message"]), None)
    current_pass_streak = _compute_streak(history, "passed")
    current_fail_streak = _compute_streak(history, "failed")
    flake_rate = _compute_flake_rate(history)
    flaky = passed_runs > 0 and failed_runs > 0
    quality_label = _compute_quality_label(
        history,
        current_fail_streak=current_fail_streak,
        current_pass_streak=current_pass_streak,
        flaky=flaky,
    )
    execution_supported = _supports_pytest_execution(file_path=effective_file_path, node_id=node_id)

    return {
        "test_id": encode_test_id(node_id=node_id, test_name=latest_case.name),
        "test_node_id": node_id,
        "test_name": latest_case.name,
        "category": latest_run.category or infer_test_category(effective_file_path, latest_case.name),
        "suite_name": latest_run.suite_name,
        "status": _normalize_status(latest_case.status),
        "description": latest_case.description,
        "file_path": effective_file_path,
        "file_name": effective_file_path,
        "expected_result": latest_case.expected_result,
        "actual_result": latest_case.actual_result,
        "confidence_score": float(latest_case.confidence_score) if latest_case.confidence_score is not None else None,
        "latest_environment": latest_case.dataset_name or latest_run.dataset_name or "default",
        "latest_run_id": latest_run.id,
        "latest_result_id": latest_case.id,
        "latest_run_status": _normalize_status(latest_run.status),
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "skipped_runs": skipped_runs,
        "pass_rate": pass_rate,
        "flake_rate": flake_rate,
        "flaky": flaky,
        "quality_label": quality_label,
        "average_duration_ms": average_duration,
        "last_duration_ms": latest_case.duration_ms,
        "last_run_timestamp": history[0]["last_run_timestamp"],
        "last_successful_run": last_successful_run,
        "last_failed_run": last_failed_run,
        "latest_failure_reason": latest_failure_reason,
        "execution_supported": execution_supported,
        "execution_engine": latest_run.execution_engine or ("pytest" if execution_supported else None),
        "current_pass_streak": current_pass_streak,
        "current_fail_streak": current_fail_streak,
        "trend": _compute_trend(history),
        "history": history,
        "latest_execution": history[0],
    }


def _query_test_rows(db: Session, *, organization_id: int):
    return (
        db.query(ComplianceTestCaseResult, ComplianceTestRun)
        .join(ComplianceTestRun, ComplianceTestRun.id == ComplianceTestCaseResult.test_run_id)
        .filter(ComplianceTestRun.organization_id == organization_id)
        .all()
    )


def _build_test_inventory(db: Session, *, organization_id: int) -> list[dict[str, object]]:
    grouped: dict[str, list[tuple[ComplianceTestCaseResult, ComplianceTestRun]]] = defaultdict(list)
    for case, run in _query_test_rows(db, organization_id=organization_id):
        grouped[build_test_node_id(test_name=case.name, file_path=case.file_name, category=run.category)].append((case, run))
    inventory_by_node_id = {
        node_id: _summarize_test_history(node_id, rows)
        for node_id, rows in grouped.items()
    }
    discovered_by_node_id = {str(item["node_id"]): item for item in discover_repository_tests()}
    for node_id, discovered_test in discovered_by_node_id.items():
        current = inventory_by_node_id.get(node_id)
        if current is None:
            inventory_by_node_id[node_id] = _build_discovered_test_inventory_item(discovered_test)
            continue
        if not current.get("description") and discovered_test.get("description"):
            current["description"] = discovered_test["description"]
        current["file_path"] = normalize_test_file_path(discovered_test.get("file_path"))
        current["file_name"] = normalize_test_file_path(discovered_test.get("file_path"))
        if current.get("category") in {None, "", "integration tests"}:
            current["category"] = discovered_test["category"]
        current["execution_supported"] = _supports_pytest_execution(file_path=current.get("file_path"), node_id=node_id)
        current["execution_engine"] = "pytest" if current["execution_supported"] else None
    inventory = list(inventory_by_node_id.values())
    return sorted(
        inventory,
        key=lambda item: (_status_rank(str(item["status"])), item["last_run_timestamp"] or "", str(item["file_path"] or ""), item["test_name"].lower()),
        reverse=True,
    )


def _category_rollup(category: str, tests: list[dict[str, object]]) -> dict[str, object]:
    passing = sum(1 for item in tests if item["status"] == "passed")
    failing = sum(1 for item in tests if item["status"] == "failed")
    skipped = sum(1 for item in tests if item["status"] == "skipped")
    flaky = sum(1 for item in tests if item["flaky"])
    not_run = sum(1 for item in tests if item["status"] == "not_run")
    last_run = max((item["last_run_timestamp"] for item in tests if item["last_run_timestamp"]), default=None)
    tests_with_runs = [item["pass_rate"] for item in tests if item["total_runs"]]
    average_pass_rate = round(mean(tests_with_runs), 2) if tests_with_runs else 0.0
    latest_status = "failed" if failing else "passed" if passing else "skipped" if skipped else "not_run" if not_run else "unknown"
    return {
        "category": category,
        "description": CATEGORY_DESCRIPTIONS.get(category, "Automated compliance validation coverage."),
        "total_tests": len(tests),
        "passing": passing,
        "failing": failing,
        "skipped": skipped,
        "not_run": not_run,
        "flaky": flaky,
        "average_pass_rate": average_pass_rate,
        "status": latest_status,
        "last_run_timestamp": last_run,
    }


def get_test_management_dashboard(db: Session, *, organization_id: int) -> dict[str, object]:
    inventory = _build_test_inventory(db, organization_id=organization_id)
    categories: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in inventory:
        categories[str(item["category"])].append(item)

    category_rollups = [_category_rollup(category, tests) for category, tests in categories.items()]
    category_rollups.sort(key=lambda item: (item["failing"], item["flaky"], item["last_run_timestamp"] or ""), reverse=True)

    total_tests = len(inventory)
    passing_tests = sum(1 for item in inventory if item["status"] == "passed")
    failing_tests = sum(1 for item in inventory if item["status"] == "failed")
    flaky_tests = sum(1 for item in inventory if item["flaky"])
    not_run_tests = sum(1 for item in inventory if item["status"] == "not_run")
    tests_with_runs = [item["pass_rate"] for item in inventory if item["total_runs"]]
    average_pass_rate = round(mean(tests_with_runs), 2) if tests_with_runs else 0.0
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    total_executions_last_7_days = sum(
        1
        for item in inventory
        for run in item["history"]
        if run["last_run_timestamp"] and _coerce_datetime(datetime.fromisoformat(str(run["last_run_timestamp"]))) >= recent_cutoff
    )
    active_runs = (
        db.query(ComplianceTestRun)
        .filter(
            ComplianceTestRun.organization_id == organization_id,
            ComplianceTestRun.status.in_(tuple(ACTIVE_RUN_STATUSES)),
        )
        .order_by(ComplianceTestRun.run_at.desc(), ComplianceTestRun.id.desc())
        .all()
    )
    recent_runs = (
        db.query(ComplianceTestRun)
        .filter(ComplianceTestRun.organization_id == organization_id)
        .order_by(ComplianceTestRun.run_at.desc(), ComplianceTestRun.id.desc())
        .limit(6)
        .all()
    )
    last_full_suite_run = (
        db.query(ComplianceTestRun)
        .filter(
            ComplianceTestRun.organization_id == organization_id,
            ComplianceTestRun.run_type == RUN_TYPE_FULL_SUITE,
        )
        .order_by(ComplianceTestRun.run_at.desc(), ComplianceTestRun.id.desc())
        .first()
    )
    open_failure_tasks = (
        db.query(ComplianceTestFailureTask)
        .filter(
            ComplianceTestFailureTask.organization_id == organization_id,
            ComplianceTestFailureTask.status.in_(("open", "in_progress")),
        )
        .count()
    )

    return {
        "summary": {
            "total_tests": total_tests,
            "passing_tests": passing_tests,
            "failing_tests": failing_tests,
            "flaky_tests": flaky_tests,
            "not_run_tests": not_run_tests,
            "average_pass_rate": average_pass_rate,
            "total_executions_last_7_days": total_executions_last_7_days,
            "running_runs": len(active_runs),
            "open_failure_tasks": open_failure_tasks,
            "last_full_suite_run": {
                "id": last_full_suite_run.id,
                "status": _normalize_status(last_full_suite_run.status),
                "completed_at": last_full_suite_run.completed_at.isoformat() if last_full_suite_run and last_full_suite_run.completed_at else None,
                "run_at": last_full_suite_run.run_at.isoformat() if last_full_suite_run and last_full_suite_run.run_at else None,
            } if last_full_suite_run is not None else None,
        },
        "categories": category_rollups,
        "recent_runs": [
            {
                "id": run.id,
                "run_type": run.run_type,
                "suite_name": run.suite_name,
                "category": run.category,
                "status": _normalize_status(run.status),
                "pytest_node_id": run.pytest_node_id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "run_at": run.run_at.isoformat() if run.run_at else None,
                "return_code": run.return_code,
                "failure_summary": run.failure_summary,
                "metadata": _parse_run_metadata(run.metadata_json),
            }
            for run in recent_runs
        ],
    }


def list_managed_tests(
    db: Session,
    *,
    organization_id: int,
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    file_path: str | None = None,
    sort: str = "last_run",
) -> dict[str, object]:
    inventory = _build_test_inventory(db, organization_id=organization_id)
    filtered = inventory
    if category:
        filtered = [item for item in filtered if item["category"] == category]
    if status:
        normalized_status = _normalize_status(status)
        if normalized_status == "flaky":
            filtered = [item for item in filtered if item["flaky"]]
        else:
            filtered = [item for item in filtered if item["status"] == normalized_status]
    if search:
        needle = search.strip().lower()
        filtered = [
            item for item in filtered
            if needle in item["test_name"].lower()
            or needle in str(item.get("description") or "").lower()
            or needle in str(item.get("file_path") or "").lower()
        ]
    if file_path:
        normalized_path = file_path.strip().lower()
        filtered = [item for item in filtered if normalized_path in str(item.get("file_path") or "").lower()]

    sort_key = SORT_KEYS.get(sort, SORT_KEYS["last_run"])
    reverse = sort != "name"
    filtered = sorted(filtered, key=sort_key, reverse=reverse)

    summary = {
        "total_tests": len(filtered),
        "passing": sum(1 for item in filtered if item["status"] == "passed"),
        "failing": sum(1 for item in filtered if item["status"] == "failed"),
        "skipped": sum(1 for item in filtered if item["status"] == "skipped"),
        "not_run": sum(1 for item in filtered if item["status"] == "not_run"),
        "flaky": sum(1 for item in filtered if item["flaky"]),
        "average_pass_rate": round(mean([item["pass_rate"] for item in filtered if item["total_runs"]]), 2) if any(item["total_runs"] for item in filtered) else 0.0,
    }
    return {"tests": filtered, "summary": summary}


def get_managed_test_detail(db: Session, *, organization_id: int, test_id: str) -> dict[str, object]:
    node_id = decode_test_id(test_id)
    inventory = _build_test_inventory(db, organization_id=organization_id)
    for item in inventory:
        if item["test_node_id"] == node_id:
            detail = dict(item)
            detail["task"] = get_failure_task_for_test(db, organization_id=organization_id, test_node_id=node_id)
            return detail
    raise ValueError("Test not found")


def get_managed_test_history(db: Session, *, organization_id: int, test_id: str) -> list[dict[str, object]]:
    return list(get_managed_test_detail(db, organization_id=organization_id, test_id=test_id)["history"])
