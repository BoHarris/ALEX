from pathlib import Path
from subprocess import CompletedProcess
from urllib.parse import quote

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base, get_db
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.company import Company
from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_failure_task import ComplianceTestFailureTask
from database.models.compliance_test_run import ComplianceTestRun
from database.models.employee import Employee
from database.models.governance_task import GovernanceTask
from database.models.governance_task_activity import GovernanceTaskActivity
from database.models.user import User
from dependencies.employee_guard import require_compliance_workspace_access, require_security_or_compliance_admin
from routers import compliance_router
from services import test_execution_service
from services import test_management_service
from services.test_management_service import encode_test_id


DISCOVERED_TESTS = [
    {
        "test_name": "test_passes_cleanly",
        "file_path": "tests/test_execution_sample.py",
        "node_id": "tests/test_execution_sample.py::test_passes_cleanly",
        "description": "Passing sample execution.",
        "category": "integration tests",
    },
    {
        "test_name": "test_fails_and_creates_work",
        "file_path": "tests/test_execution_sample.py",
        "node_id": "tests/test_execution_sample.py::test_fails_and_creates_work",
        "description": "Failing sample execution.",
        "category": "integration tests",
    },
]


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Company.__table__,
            User.__table__,
            Employee.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            ComplianceRecord.__table__,
            ComplianceActivity.__table__,
            ComplianceTestRun.__table__,
            ComplianceTestCaseResult.__table__,
            ComplianceTestFailureTask.__table__,
            GovernanceTask.__table__,
            GovernanceTaskActivity.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_factory(), session_factory


def _seed_org(session, *, email: str = "operator@example.com", company_name: str = "Acme"):
    company = Company(company_name=company_name, is_active=True, is_verified=True)
    session.add(company)
    session.commit()
    user = User(first_name="Casey", last_name="Operator", email=email, role="security_admin", company_id=company.id, tier="business")
    session.add(user)
    session.commit()
    employee = Employee(
        employee_id=f"EMP-{company.id:04d}",
        first_name="Casey",
        last_name="Operator",
        email=email,
        role="security_admin",
        department="Security",
        job_title="Security Admin",
        status="active",
        company_id=company.id,
        user_id=user.id,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return company, user, employee


def _employee_context(employee):
    return {
        "user_id": employee.user_id,
        "employee_id": employee.id,
        "employee_role": employee.role,
        "organization_id": employee.company_id,
        "employee": {"id": employee.id},
    }


def _build_test_app(session, current_context_ref):
    app = FastAPI()
    app.include_router(compliance_router.router)

    def override_db():
        try:
            yield session
        finally:
            pass

    def override_workspace():
        return current_context_ref["value"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_security_or_compliance_admin] = override_workspace
    app.dependency_overrides[require_compliance_workspace_access] = override_workspace
    return app


def _write_junit_report(report_path: Path, *, target_node_ids: list[str]) -> None:
    cases = []
    for node_id in target_node_ids:
        if node_id.endswith("test_passes_cleanly"):
            cases.append(
                """
<testcase classname="tests.test_execution_sample" file="tests/test_execution_sample.py" name="test_passes_cleanly" time="0.008">
  <system-out>execution completed</system-out>
</testcase>
""".strip()
            )
        elif node_id.endswith("test_fails_and_creates_work"):
            cases.append(
                """
<testcase classname="tests.test_execution_sample" file="tests/test_execution_sample.py" name="test_fails_and_creates_work" time="0.011">
  <failure message="Expected privacy remediation">assert remediation_required</failure>
  <system-out>validation drift detected</system-out>
</testcase>
""".strip()
            )
    failures = sum(1 for node_id in target_node_ids if node_id.endswith("test_fails_and_creates_work"))
    skipped = 0
    suite_xml = f"""
<testsuite name="pytest" tests="{len(target_node_ids)}" failures="{failures}" skipped="{skipped}">
  {' '.join(cases)}
</testsuite>
""".strip()
    report_path.write_text(suite_xml + "\n", encoding="utf-8")


def _install_fake_execution(monkeypatch):
    monkeypatch.setattr(
        test_management_service,
        "discover_repository_tests",
        lambda: DISCOVERED_TESTS,
    )

    def fake_subprocess_run(command, cwd, capture_output, text, timeout, env, check):
        assert capture_output is True
        assert text is True
        assert check is False
        assert command[:4] == [test_execution_service.sys.executable, "-m", "pytest", "-q"]
        report_arg = next(item for item in command if str(item).startswith("--junitxml="))
        report_path = Path(str(report_arg).split("=", 1)[1])
        selected_node_ids = [str(item) for item in command if "::" in str(item)]
        if not selected_node_ids:
            selected_node_ids = [item["node_id"] for item in DISCOVERED_TESTS]
        _write_junit_report(report_path, target_node_ids=selected_node_ids)
        return CompletedProcess(
            args=command,
            returncode=1 if any(node_id.endswith("test_fails_and_creates_work") for node_id in selected_node_ids) else 0,
            stdout="collected tests\nexecution complete",
            stderr="1 failed" if any(node_id.endswith("test_fails_and_creates_work") for node_id in selected_node_ids) else "",
        )

    monkeypatch.setattr(test_execution_service.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(test_execution_service, "DEFAULT_REPOSITORY_ROOT", Path.cwd())


def _queue_inline(_background_tasks, db, run):
    test_execution_service.queue_test_execution(run.id, execute_inline=True)
    db.expire_all()
    return db.query(ComplianceTestRun).filter(ComplianceTestRun.id == run.id).first()


def test_run_all_endpoint_executes_suite_persists_results_and_failure_task(monkeypatch):
    session, session_factory = _session()
    _company, _user, employee = _seed_org(session)
    current_context = {"value": _employee_context(employee)}
    app = _build_test_app(session, current_context)
    client = TestClient(app)

    monkeypatch.setattr(compliance_router, "_demo_workspace_seeding_enabled", lambda: False)
    monkeypatch.setattr(test_execution_service, "SessionLocal", session_factory)
    monkeypatch.setattr(compliance_router, "_queue_test_run", _queue_inline)
    _install_fake_execution(monkeypatch)

    response = client.post("/compliance/tests/run-all")
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["run_type"] == "full_suite"
    assert run["status"] == "failed"

    detail = client.get(f"/compliance/tests/runs/{run['id']}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["failed_tests"] == 1
    assert payload["run"]["total_tests"] == 2
    assert len(payload["results"]) == 2
    assert session.query(ComplianceTestFailureTask).count() == 1


def test_run_test_endpoint_executes_single_test_and_supports_scoping(monkeypatch):
    session, session_factory = _session()
    _company, _user, employee = _seed_org(session)
    _other_company, _other_user, other_employee = _seed_org(session, email="other@example.com", company_name="OtherCo")
    current_context = {"value": _employee_context(employee)}
    app = _build_test_app(session, current_context)
    client = TestClient(app)

    monkeypatch.setattr(compliance_router, "_demo_workspace_seeding_enabled", lambda: False)
    monkeypatch.setattr(test_execution_service, "SessionLocal", session_factory)
    monkeypatch.setattr(compliance_router, "_queue_test_run", _queue_inline)
    _install_fake_execution(monkeypatch)

    test_id = encode_test_id(test_name="test_passes_cleanly", file_path="tests/test_execution_sample.py")
    response = client.post(f"/compliance/tests/run-test/{quote(test_id, safe='')}")
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["run_type"] == "single_test"
    assert run["status"] == "passed"
    assert run["pytest_node_id"] == "tests/test_execution_sample.py::test_passes_cleanly"

    detail = client.get(f"/compliance/tests/runs/{run['id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "passed"

    current_context["value"] = _employee_context(other_employee)
    forbidden = client.get(f"/compliance/tests/runs/{run['id']}")
    assert forbidden.status_code == 404


def test_run_category_endpoint_executes_known_category(monkeypatch):
    session, session_factory = _session()
    _company, _user, employee = _seed_org(session)
    current_context = {"value": _employee_context(employee)}
    app = _build_test_app(session, current_context)
    client = TestClient(app)

    monkeypatch.setattr(compliance_router, "_demo_workspace_seeding_enabled", lambda: False)
    monkeypatch.setattr(test_execution_service, "SessionLocal", session_factory)
    monkeypatch.setattr(compliance_router, "_queue_test_run", _queue_inline)
    _install_fake_execution(monkeypatch)

    response = client.post("/compliance/tests/categories/integration%20tests/run")
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["run_type"] == "category"
    assert run["status"] == "failed"
    assert run["metadata"]["target"] == "category"

    detail = client.get(f"/compliance/tests/runs/{run['id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "failed"


def test_run_all_endpoint_prevents_duplicate_active_runs(monkeypatch):
    session, session_factory = _session()
    _company, _user, employee = _seed_org(session)
    current_context = {"value": _employee_context(employee)}
    app = _build_test_app(session, current_context)
    client = TestClient(app)

    monkeypatch.setattr(compliance_router, "_demo_workspace_seeding_enabled", lambda: False)
    monkeypatch.setattr(test_execution_service, "SessionLocal", session_factory)
    monkeypatch.setattr(compliance_router, "_queue_test_run", lambda background_tasks, db, run: run)
    _install_fake_execution(monkeypatch)

    first = client.post("/compliance/tests/run-all")
    second = client.post("/compliance/tests/run-all")
    assert first.status_code == 200
    assert first.json()["run"]["status"] == "queued"
    assert second.status_code == 409


def test_run_all_endpoint_enforces_admin_permissions(monkeypatch):
    session, session_factory = _session()
    _company, _user, employee = _seed_org(session)
    current_context = {"value": _employee_context(employee)}
    app = _build_test_app(session, current_context)

    def raise_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[require_security_or_compliance_admin] = raise_forbidden
    client = TestClient(app)

    monkeypatch.setattr(compliance_router, "_demo_workspace_seeding_enabled", lambda: False)
    monkeypatch.setattr(test_execution_service, "SessionLocal", session_factory)
    _install_fake_execution(monkeypatch)

    response = client.post("/compliance/tests/run-all")
    assert response.status_code == 403
