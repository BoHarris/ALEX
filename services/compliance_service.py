from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_approval import ComplianceApproval
from database.models.compliance_attachment import ComplianceAttachment
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_run import ComplianceTestRun
from database.models.company import Company
from database.models.employee import Employee
from database.models.training_module import TrainingModule
from database.models.user import User
from database.models.wiki_page import WikiPage
from services.audit_service import record_audit_event

logger = logging.getLogger(__name__)

DEFAULT_ORG_NAME = "Bo Harris LLC"
DEFAULT_EMPLOYEE_EMAIL = "bo.harris@boharrisllc.internal"

TRAINING_MODULES = [
    ("Security Awareness", "Security"),
    ("Privacy Fundamentals", "Privacy"),
    ("Incident Response", "Operations"),
    ("Data Handling", "Privacy"),
    ("Acceptable Use Policy", "HR"),
]

TRAINING_DOCS = {
    "policy_wiki": {
        "title": "How to Create a Runbook Page",
        "category": "Operational Runbooks",
        "template_name": "Runbook Template",
        "content": "# How to Create a Runbook Page\n\n## Purpose\nDocument repeatable operational procedures.\n\n## Steps\n1. Open the Compliance Workspace.\n2. Select Policy & Knowledge Base.\n3. Create a page using the appropriate template.\n4. Add tags, ownership, and review dates.\n\n## Best Practices\n- Keep runbooks task-focused.\n- Update version history with meaningful notes.\n- Link related controls and vendors when relevant.\n\n## Security Considerations\nDo not paste secrets or raw sensitive production data into wiki pages.\n",
    },
    "vendor": {
        "title": "How to Add a Vendor and Perform a Risk Review",
        "category": "Vendor Management Procedures",
        "template_name": "Vendor Review Template",
        "content": "# How to Add a Vendor and Perform a Risk Review\n\n## Purpose\nTrack external services and document risk decisions.\n\n## Steps\n1. Create the vendor record.\n2. Set data access level and contract dates.\n3. Record risk rating and review status.\n4. Attach questionnaires, contracts, and privacy review links.\n\n## Best Practices\n- Review high-risk vendors before contract renewal.\n- Capture evidence links in attachments.\n\n## Security Considerations\nDo not upload raw contract files containing secrets unless approved storage is used.\n",
    },
    "access_review": {
        "title": "How to Complete an Access Review",
        "category": "Security Policies",
        "template_name": "Access Review Template",
        "content": "# How to Complete an Access Review\n\n## Purpose\nValidate that employee access remains appropriate.\n\n## Steps\n1. Open the access review record.\n2. Confirm the employee role and permissions snapshot.\n3. Approve, revoke, or flag excessive access.\n4. Record notes and finalize the decision.\n\n## Best Practices\n- Review privileged roles first.\n- Document why access remains necessary.\n\n## Security Considerations\nFlag dormant or over-privileged accounts immediately.\n",
    },
    "incident": {
        "title": "How to Record a Security Incident",
        "category": "Incident Response Playbooks",
        "template_name": "Incident Template",
        "content": "# How to Record a Security Incident\n\n## Purpose\nCapture detection, response, and lessons learned in one timeline.\n\n## Steps\n1. Create the incident record.\n2. Set severity and assignment.\n3. Document investigation updates in the timeline.\n4. Add root cause and lessons learned before closure.\n\n## Best Practices\n- Keep updates chronological and factual.\n- Link related controls, vendors, and wiki procedures.\n\n## Security Considerations\nClosed incidents are immutable. Verify details before closing.\n",
    },
    "training": {
        "title": "How to Review Training Completion",
        "category": "Engineering Guidelines",
        "template_name": "Training Template",
        "content": "# How to Review Training Completion\n\n## Purpose\nTrack completion of required workforce training.\n\n## Steps\n1. Assign modules to employees.\n2. Monitor due dates and overdue items.\n3. Record completion timestamps and quiz scores.\n4. Escalate overdue assignments to managers.\n\n## Best Practices\n- Review completion rates monthly.\n- Reassign annual training before expiration.\n\n## Security Considerations\nOnly attach approved training documents and sanitized quiz evidence.\n",
    },
}


def _json_dumps(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def _slugify(value: str) -> str:
    lowered = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    parts = [part for part in lowered.split("-") if part]
    return "-".join(parts) or f"page-{uuid.uuid4().hex[:8]}"


def _coerce_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def serialize_compliance_record(record: ComplianceRecord) -> dict:
    return {
        "id": record.id,
        "organization_id": record.organization_id,
        "module": record.module,
        "title": record.title,
        "status": record.status,
        "owner_employee_id": record.owner_employee_id,
        "due_date": record.due_date.isoformat() if record.due_date else None,
        "review_date": record.review_date.isoformat() if record.review_date else None,
        "notes": record.notes,
        "created_by_employee_id": record.created_by_employee_id,
        "updated_by_employee_id": record.updated_by_employee_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "closed_at": record.closed_at.isoformat() if record.closed_at else None,
    }


def serialize_employee(employee: Employee) -> dict:
    return {
        "id": employee.id,
        "employee_id": employee.employee_id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "role": employee.role,
        "department": employee.department,
        "job_title": employee.job_title,
        "status": employee.status,
        "company_id": employee.company_id,
        "user_id": employee.user_id,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "last_login": employee.last_login.isoformat() if employee.last_login else None,
    }


def add_activity(db: Session, *, compliance_record_id: int, employee_id: int | None, action: str, details: str | None = None) -> None:
    db.add(
        ComplianceActivity(
            compliance_record_id=compliance_record_id,
            employee_id=employee_id,
            action=action,
            details=details,
        )
    )


def create_compliance_record(
    db: Session,
    *,
    organization_id: int,
    module: str,
    title: str,
    employee_id: int | None,
    status: str = "draft",
    due_date: datetime | None = None,
    review_date: datetime | None = None,
    notes: str | None = None,
    owner_employee_id: int | None = None,
) -> ComplianceRecord:
    record = ComplianceRecord(
        organization_id=organization_id,
        module=module,
        title=title,
        status=status,
        due_date=_coerce_dt(due_date),
        review_date=_coerce_dt(review_date),
        notes=notes,
        owner_employee_id=owner_employee_id or employee_id,
        created_by_employee_id=employee_id,
        updated_by_employee_id=employee_id,
    )
    db.add(record)
    db.flush()
    add_activity(
        db,
        compliance_record_id=record.id,
        employee_id=employee_id,
        action="record_created",
        details=f"Created {module} record.",
    )
    return record


def update_record_status(
    db: Session,
    *,
    record: ComplianceRecord,
    employee_id: int,
    status: str,
    details: str | None = None,
) -> ComplianceRecord:
    if record.closed_at is not None:
        raise ValueError("Closed compliance records are immutable.")
    record.status = status
    if status.lower() in {"closed", "completed"}:
        record.closed_at = datetime.now(timezone.utc)
    record.updated_by_employee_id = employee_id
    db.add(record)
    add_activity(db, compliance_record_id=record.id, employee_id=employee_id, action="status_updated", details=details or status)
    return record


def add_attachment(db: Session, *, record_id: int, employee_id: int | None, label: str, path_or_url: str, attachment_type: str = "link") -> None:
    db.add(
        ComplianceAttachment(
            compliance_record_id=record_id,
            employee_id=employee_id,
            label=label,
            path_or_url=path_or_url,
            attachment_type=attachment_type,
        )
    )
    add_activity(db, compliance_record_id=record_id, employee_id=employee_id, action="attachment_added", details=label)


def add_approval(db: Session, *, record_id: int, approver_employee_id: int, status: str, notes: str | None = None) -> None:
    db.add(
        ComplianceApproval(
            compliance_record_id=record_id,
            approver_employee_id=approver_employee_id,
            status=status,
            notes=notes,
            decided_at=datetime.now(timezone.utc) if status != "pending" else None,
        )
    )
    add_activity(db, compliance_record_id=record_id, employee_id=approver_employee_id, action="approval_recorded", details=status)


def log_compliance_audit(
    db: Session,
    *,
    company_id: int,
    user_id: int | None,
    employee_id: int | None,
    action: str,
    module: str,
    resource_type: str,
    resource_id: str,
    metadata: dict | None = None,
) -> None:
    record_audit_event(
        db,
        company_id=company_id,
        user_id=user_id,
        event_type=action,
        event_category="compliance",
        description=f"{module} action recorded.",
        target_type=resource_type,
        target_id=resource_id,
        event_metadata={"employee_id": employee_id, **(metadata or {})},
    )


def ensure_training_modules(db: Session, organization_id: int) -> None:
    existing_titles = {row.title for row in db.query(TrainingModule).filter(TrainingModule.organization_id == organization_id).all()}
    created = False
    for title, category in TRAINING_MODULES:
        if title in existing_titles:
            continue
        db.add(
            TrainingModule(
                organization_id=organization_id,
                title=title,
                category=category,
                description=f"{title} training module for internal governance workflows.",
            )
        )
        created = True
    if created:
        db.commit()


def ensure_training_docs(db: Session, organization_id: int, employee_id: int, user_id: int | None) -> None:
    existing_slugs = {page.slug for page in db.query(WikiPage).all()}
    for key, doc in TRAINING_DOCS.items():
        slug = _slugify(doc["title"])
        if slug in existing_slugs:
            continue
        record = create_compliance_record(
            db,
            organization_id=organization_id,
            module="wiki",
            title=doc["title"],
            employee_id=employee_id,
            status="published",
            review_date=datetime.now(timezone.utc) + timedelta(days=90),
            notes="Seeded training documentation.",
        )
        db.add(
            WikiPage(
                compliance_record_id=record.id,
                slug=slug,
                category=doc["category"],
                template_name=doc["template_name"],
                tags=_json_dumps(["training", key]),
                content_markdown=doc["content"],
                version=1,
            )
        )
        log_compliance_audit(
            db,
            company_id=organization_id,
            user_id=user_id,
            employee_id=employee_id,
            action="policy_page_created",
            module="wiki",
            resource_type="wiki_page",
            resource_id=str(record.id),
            metadata={"slug": slug, "seeded": True},
        )
        db.commit()


def ensure_test_runs(db: Session, organization_id: int) -> None:
    tests_dir = Path("tests")
    test_files = list(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    categories = [
        ("API tests", "api", "Automated API contract coverage", [
            ("passed", "passed", "skipped"),
            ("passed", "failed", "skipped"),
            ("passed", "passed", "skipped"),
        ]),
        ("security tests", "security", "Authentication and security hardening checks", [
            ("passed", "failed", "skipped"),
            ("passed", "passed", "skipped"),
            ("passed", "passed", "skipped"),
        ]),
        ("privacy tests", "privacy", "PII detection and redaction validation", [
            ("failed", "passed", "skipped"),
            ("passed", "passed", "skipped"),
            ("passed", "failed", "skipped"),
        ]),
        ("UI tests", "ui", "Frontend workflow and regression checks", [
            ("passed", "passed", "skipped"),
            ("passed", "passed", "skipped"),
            ("passed", "passed", "skipped"),
        ]),
        ("integration tests", "integration", "Cross-system environment validation", [
            ("failed", "failed", "skipped"),
            ("passed", "failed", "skipped"),
            ("failed", "failed", "skipped"),
        ]),
    ]

    def seed_cases_for_run(run: ComplianceTestRun, *, key: str, display_name: str, statuses: tuple[str, ...]) -> None:
        if db.query(ComplianceTestCaseResult).filter(ComplianceTestCaseResult.test_run_id == run.id).count():
            return
        seed_cases = [
            (
                f"test_{key}_primary_path",
                f"tests/test_{key}_suite.py",
                f"Validates the primary {display_name.lower()} path.",
                120,
                "All assertions passed.",
                None,
            ),
            (
                f"test_{key}_regression_guard",
                f"tests/test_{key}_suite.py",
                f"Protects the key {display_name.lower()} regressions.",
                240,
                "Regression suite executed.",
                "Expected status 200 but received 500.",
            ),
            (
                f"test_{key}_optional_scenario",
                f"tests/test_{key}_suite.py",
                f"Covers optional {display_name.lower()} behavior.",
                0,
                "Skipped pending environment prerequisites.",
                None,
            ),
        ]
        for (name, file_name, description, duration_ms, output, default_error), status in zip(seed_cases, statuses):
            db.add(
                ComplianceTestCaseResult(
                    test_run_id=run.id,
                    name=name,
                    dataset_name=run.dataset_name or "seed_baseline",
                    file_name=file_name,
                    description=description,
                    expected_result=None,
                    actual_result=None,
                    status=status,
                    confidence_score=None,
                    duration_ms=duration_ms,
                    output=output,
                    error_message=default_error if status == "failed" else None,
                    last_run_at=run.run_at,
                )
            )

    existing_runs = (
        db.query(ComplianceTestRun)
        .filter(ComplianceTestRun.organization_id == organization_id)
        .order_by(ComplianceTestRun.run_at.asc(), ComplianceTestRun.id.asc())
        .all()
    )
    if existing_runs:
        existing_by_category: dict[str, list[ComplianceTestRun]] = {}
        for run in existing_runs:
            existing_by_category.setdefault(run.category, []).append(run)
        for display_name, key, suite_suffix, status_windows in categories:
            for history_index, run in enumerate(existing_by_category.get(display_name, [])):
                statuses = status_windows[min(history_index, len(status_windows) - 1)]
                seed_cases_for_run(run, key=key, display_name=display_name, statuses=statuses)
        db.commit()
        return

    for display_name, key, suite_suffix, status_windows in categories:
        matching = [path for path in test_files if key in path.name.lower()]
        for history_index, statuses in enumerate(status_windows):
            passed_tests = sum(1 for status in statuses if status == "passed")
            failed_tests = sum(1 for status in statuses if status == "failed")
            skipped_tests = sum(1 for status in statuses if status == "skipped")
            total_tests = len(statuses)
            run = ComplianceTestRun(
                organization_id=organization_id,
                category=display_name,
                suite_name=f"{display_name} - {suite_suffix}",
                dataset_name="seed_baseline",
                status="failed" if failed_tests else "passed" if passed_tests else "skipped",
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                accuracy_score=Decimal(str(round((passed_tests / max(passed_tests + failed_tests, 1)), 4))),
                coverage_percent=Decimal("80.00") if matching else Decimal("60.00"),
                report_link=f"/tests/{key}",
                run_at=datetime.now(timezone.utc) - timedelta(days=(len(status_windows) - history_index - 1) * 7),
            )
            db.add(run)
            db.flush()
            seed_cases_for_run(run, key=key, display_name=display_name, statuses=statuses)
    db.commit()


def ensure_default_company_and_employee(db: Session) -> tuple[Company, Employee]:
    company = db.query(Company).filter(Company.company_name == DEFAULT_ORG_NAME).first()
    if not company:
        company = Company(
            company_name=DEFAULT_ORG_NAME,
            industry="Professional Services",
            subscription_tier="business",
            is_active=True,
            is_verified=True,
        )
        db.add(company)
        db.flush()

    user = db.query(User).filter(User.email == DEFAULT_EMPLOYEE_EMAIL).first()
    if not user:
        user = User(
            first_name="Bo",
            last_name="Harris",
            email=DEFAULT_EMPLOYEE_EMAIL,
            tier="business",
            role="security_admin",
            company_id=company.id,
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.company_id = company.id
        user.role = "security_admin"
        user.tier = "business"
        db.add(user)

    employee = db.query(Employee).filter(Employee.email == DEFAULT_EMPLOYEE_EMAIL).first()
    if not employee:
        employee = Employee(
            employee_id="EMP-0001",
            first_name="Bo",
            last_name="Harris",
            email=DEFAULT_EMPLOYEE_EMAIL,
            role="security_admin",
            department="Security",
            job_title="Security Admin",
            status="active",
            company_id=company.id,
            user_id=user.id,
            is_internal=True,
        )
        db.add(employee)
        db.flush()
    else:
        employee.company_id = company.id
        employee.user_id = user.id
        employee.role = "security_admin"
        employee.status = "active"
        db.add(employee)

    db.commit()
    ensure_training_modules(db, company.id)
    ensure_training_docs(db, company.id, employee.id, user.id)
    ensure_test_runs(db, company.id)
    return company, employee
