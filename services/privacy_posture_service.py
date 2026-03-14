from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_run import ComplianceTestRun
from database.models.scan_results import ScanResult
from database.models.wiki_page import WikiPage
from services.privacy_metrics_service import get_scan_metric_snapshot
from services.test_management_service import list_managed_tests
from services.test_metrics_service import compute_test_metrics
from utils.pii_taxonomy import PII_SENSITIVE_DATA

DEFAULT_COMPONENT_WEIGHTS = {
    "detection_coverage": 0.25,
    "redaction_effectiveness": 0.25,
    "policy_compliance": 0.25,
    "testing_reliability": 0.25,
}


def _coerce_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _clamp_ratio(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 4)


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return _clamp_ratio(float(numerator) / float(denominator))


def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    base = dict(DEFAULT_COMPONENT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in base:
                base[key] = max(float(value), 0.0)
    total_weight = sum(base.values())
    if total_weight <= 0:
        return dict(DEFAULT_COMPONENT_WEIGHTS)
    return {key: value / total_weight for key, value in base.items()}


def map_posture_risk_level(score: int | float) -> str:
    numeric_score = int(round(score))
    if numeric_score >= 85:
        return "low"
    if numeric_score >= 70:
        return "moderate"
    if numeric_score >= 50:
        return "elevated"
    return "critical"


def calculate_posture_score(
    component_scores: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
) -> int:
    normalized_weights = _normalize_weights(weights)
    weighted_total = sum(
        _clamp_ratio(component_scores.get(component, 0.0)) * normalized_weights[component]
        for component in DEFAULT_COMPONENT_WEIGHTS
    )
    return max(0, min(int(round(weighted_total * 100)), 100))


def _dataset_names_from_runs(test_runs: list[ComplianceTestRun]) -> set[str]:
    return {
        str(run.dataset_name).strip()
        for run in test_runs
        if run.dataset_name and str(run.dataset_name).strip().lower() != "default"
    }


def _compute_policy_compliance(
    *,
    scan_snapshot: dict[str, object],
    privacy_policy_count: int,
) -> tuple[float, list[str]]:
    findings = list(scan_snapshot.get("scan_findings", []))
    total_findings = len(findings)
    if total_findings == 0:
        return (1.0 if privacy_policy_count else 0.75), []

    missing_taxonomy = [
        finding for finding in findings
        if str(finding.get("detected_type") or "").strip() == PII_SENSITIVE_DATA
        or not finding.get("policy_categories")
    ]
    issues = len(missing_taxonomy)
    risks = [
        f"Dataset {finding.get('filename') or 'unknown'} missing taxonomy classification for column {finding.get('column') or 'unknown'}"
        for finding in missing_taxonomy[:5]
    ]
    if privacy_policy_count == 0:
        issues += 1
        risks.append("Privacy policy taxonomy documentation is missing from the compliance workspace")
    score = 1.0 - min(issues / max(total_findings, 1), 1.0)
    return _clamp_ratio(score), risks


def _compute_testing_reliability(
    *,
    test_metrics: dict[str, object],
    test_inventory: list[dict[str, object]],
) -> tuple[float, list[str]]:
    if not test_inventory:
        return 0.0, []

    pass_rate = float(test_metrics.get("test_pass_rate", 0.0) or 0.0)
    executed_tests = [item for item in test_inventory if item.get("total_runs")]
    average_flake_rate = (
        sum(float(item.get("flake_rate", 0.0) or 0.0) for item in executed_tests) / len(executed_tests)
        if executed_tests
        else 0.0
    )
    max_fail_streak = max((int(item.get("current_fail_streak", 0) or 0) for item in executed_tests), default=0)
    streak_penalty = min(max_fail_streak / 5, 1.0) * 0.15
    reliability = (pass_rate * 0.7) + ((1 - average_flake_rate) * 0.3) - streak_penalty

    risks: list[str] = []
    failing_tests = sorted(
        [item for item in executed_tests if str(item.get("status")) == "failed"],
        key=lambda item: (int(item.get("current_fail_streak", 0) or 0), float(item.get("flake_rate", 0.0) or 0.0)),
        reverse=True,
    )
    if failing_tests:
        risks.append(f"{len(failing_tests)} failing compliance regression tests")
    flaky_tests = [item for item in executed_tests if float(item.get("flake_rate", 0.0) or 0.0) >= 0.5]
    if flaky_tests:
        risks.append(f"{len(flaky_tests)} tests show high flake rates")

    return _clamp_ratio(reliability), risks


def _build_component_scores(
    *,
    scan_snapshot: dict[str, object],
    test_metrics: dict[str, object],
    test_inventory: list[dict[str, object]],
    privacy_policy_count: int,
    total_dataset_count: int,
) -> tuple[dict[str, float], list[str]]:
    scanned_dataset_count = len(set(scan_snapshot.get("dataset_names", [])))
    detection_coverage = _safe_ratio(scanned_dataset_count, total_dataset_count)

    sensitive_scan_count = int(scan_snapshot.get("sensitive_scan_count", 0) or 0)
    successful_redaction_scans = int(scan_snapshot.get("successful_redaction_scans", 0) or 0)
    redaction_effectiveness = _safe_ratio(successful_redaction_scans, sensitive_scan_count)
    if sensitive_scan_count == 0 and int(scan_snapshot.get("total_scans", 0) or 0) > 0:
        redaction_effectiveness = 1.0

    policy_compliance, policy_risks = _compute_policy_compliance(
        scan_snapshot=scan_snapshot,
        privacy_policy_count=privacy_policy_count,
    )
    testing_reliability, testing_risks = _compute_testing_reliability(
        test_metrics=test_metrics,
        test_inventory=test_inventory,
    )

    component_scores = {
        "detection_coverage": detection_coverage,
        "redaction_effectiveness": redaction_effectiveness,
        "policy_compliance": policy_compliance,
        "testing_reliability": testing_reliability,
    }
    return component_scores, [*policy_risks, *testing_risks]


def _build_scan_risks(scan_snapshot: dict[str, object]) -> list[str]:
    risks: list[str] = []
    sensitive_scan_count = int(scan_snapshot.get("sensitive_scan_count", 0) or 0)
    successful_redaction_scans = int(scan_snapshot.get("successful_redaction_scans", 0) or 0)
    if sensitive_scan_count > successful_redaction_scans:
        risks.append("Detected sensitive data exists without a redacted output artifact")

    findings = list(scan_snapshot.get("scan_findings", []))
    for finding in findings:
        if str(finding.get("detected_type") or "").strip() != PII_SENSITIVE_DATA:
            continue
        risks.append(f"Dataset {finding.get('filename') or 'unknown'} missing taxonomy classification")
        if len(risks) >= 5:
            break
    return risks


def _summarize_test_inventory_as_of(
    test_inventory: list[dict[str, object]],
    *,
    as_of: datetime,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    executed_tests: list[dict[str, object]] = []
    passed = 0
    failed = 0
    for test in test_inventory:
        history = [
            item for item in list(test.get("history", []))
            if item.get("last_run_timestamp")
            and (_coerce_datetime(datetime.fromisoformat(str(item["last_run_timestamp"]))) or as_of) <= as_of
        ]
        if not history:
            continue
        statuses = [str(item.get("status")) for item in history]
        latest = history[0]
        terminal_statuses = [status for status in statuses if status in {"passed", "failed"}]
        transitions = sum(1 for index in range(1, len(terminal_statuses)) if terminal_statuses[index] != terminal_statuses[index - 1])
        flake_rate = round(transitions / (len(terminal_statuses) - 1), 2) if len(terminal_statuses) > 1 else 0.0
        current_fail_streak = 0
        for status in statuses:
            if status != "failed":
                break
            current_fail_streak += 1
        executed_tests.append(
            {
                "test_name": test.get("test_name"),
                "status": latest.get("status"),
                "flake_rate": flake_rate,
                "current_fail_streak": current_fail_streak,
                "total_runs": len(history),
            }
        )
        if latest.get("status") == "passed":
            passed += 1
        elif latest.get("status") == "failed":
            failed += 1
    total = passed + failed
    return {
        "test_pass_rate": round((passed / total), 4) if total else 0.0,
        "passed": passed,
        "failed": failed,
        "total_tests": total,
    }, executed_tests


def _build_trend(
    *,
    db: Session,
    company_id: int,
    scan_rows: list[ScanResult],
    test_inventory: list[dict[str, object]],
    test_runs: list[ComplianceTestRun],
    privacy_policy_count: int,
    weights: dict[str, float] | None,
) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    timeline_dates = sorted(
        {
            (_coerce_datetime(row.scanned_at) or now).date().isoformat()
            for row in scan_rows
        }
        | {
            (_coerce_datetime(run.run_at) or now).date().isoformat()
            for run in test_runs
        }
    )
    if len(timeline_dates) < 2:
        return []

    trend: list[dict[str, object]] = []
    for date_text in timeline_dates[-3:]:
        as_of = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc) + timedelta(days=1) - timedelta(seconds=1)
        scan_snapshot = get_scan_metric_snapshot(
            db,
            company_id=company_id,
            activity_window_days=30,
            as_of=as_of,
            scan_rows=scan_rows,
        )
        test_metrics, executed_inventory = _summarize_test_inventory_as_of(test_inventory, as_of=as_of)
        eligible_test_runs = [run for run in test_runs if (_coerce_datetime(run.run_at) or as_of) <= as_of]
        known_datasets = set(scan_snapshot.get("dataset_names", [])) | _dataset_names_from_runs(eligible_test_runs)
        component_scores, _ = _build_component_scores(
            scan_snapshot=scan_snapshot,
            test_metrics=test_metrics,
            test_inventory=executed_inventory,
            privacy_policy_count=privacy_policy_count,
            total_dataset_count=len(known_datasets) or len(set(scan_snapshot.get("dataset_names", []))),
        )
        trend.append({"date": date_text, "score": calculate_posture_score(component_scores, weights=weights)})
    return trend


def get_privacy_posture(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
    weights: dict[str, float] | None = None,
) -> dict[str, object]:
    scan_rows = db.query(ScanResult).filter(ScanResult.company_id == company_id).all()
    scan_snapshot = get_scan_metric_snapshot(
        db,
        company_id=company_id,
        activity_window_days=activity_window_days,
        scan_rows=scan_rows,
    )
    test_metrics = compute_test_metrics(db, organization_id=company_id)
    test_inventory = list_managed_tests(db, organization_id=company_id, sort="last_run")["tests"]
    test_runs = db.query(ComplianceTestRun).filter(ComplianceTestRun.organization_id == company_id).all()
    privacy_policy_count = (
        db.query(WikiPage)
        .join(ComplianceRecord, ComplianceRecord.id == WikiPage.compliance_record_id)
        .filter(
            ComplianceRecord.organization_id == company_id,
            WikiPage.category.ilike("%privacy%"),
        )
        .count()
    )

    known_datasets = set(scan_snapshot.get("dataset_names", [])) | _dataset_names_from_runs(test_runs)
    component_scores, component_risks = _build_component_scores(
        scan_snapshot=scan_snapshot,
        test_metrics=test_metrics,
        test_inventory=test_inventory,
        privacy_policy_count=privacy_policy_count,
        total_dataset_count=len(known_datasets) or len(set(scan_snapshot.get("dataset_names", []))),
    )
    posture_score = calculate_posture_score(component_scores, weights=weights)

    top_risks: list[str] = []
    for risk in [*_build_scan_risks(scan_snapshot), *component_risks]:
        if risk not in top_risks:
            top_risks.append(risk)
        if len(top_risks) >= 5:
            break

    payload = {
        "posture_score": posture_score,
        "risk_level": map_posture_risk_level(posture_score),
        "component_scores": component_scores,
        "components": component_scores,
        "top_risks": top_risks,
    }
    trend = _build_trend(
        db=db,
        company_id=company_id,
        scan_rows=scan_rows,
        test_inventory=test_inventory,
        test_runs=test_runs,
        privacy_policy_count=privacy_policy_count,
        weights=weights,
    )
    if trend:
        payload["trend"] = trend
    return payload
