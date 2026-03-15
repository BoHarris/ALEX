"""
Pytest configuration and hooks for automatic task generation on test failures.

This module integrates with the task generation system to automatically create
governance tasks when tests fail, capturing the failure reason and test details.
"""
import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from services.test_metrics_service import record_test_result

# Default organization ID for local test execution
DEFAULT_ORG_ID = 1
DEFAULT_EMPLOYEE_ID = None
DEFAULT_USER_ID = None


class TestFailureCollector:
    """Collects test failures and generates tasks."""
    
    def __init__(self):
        self.failures = []
        self.session = None
        self.current_run = None
    
    def start_session(self, org_id=DEFAULT_ORG_ID):
        """Start a database session for task generation."""
        from database.models.compliance_test_run import ComplianceTestRun
        
        try:
            self.session = SessionLocal()
            # Create or get a test run
            self.current_run = ComplianceTestRun(
                organization_id=org_id,
                run_type="pytest_suite",
                trigger_source="automated",
                execution_engine="pytest",
                category="integration_tests",
                suite_name="pytest_suite",
                dataset_name="test_execution",
                status="running",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
            )
            self.session.add(self.current_run)
            self.session.flush()
        except Exception as e:
            print(f"Warning: Could not initialize test run for task generation: {e}")
            self.session = None
            self.current_run = None
    
    def record_test_failure(self, test_name, test_file, failure_reason):
        """Record a test failure and generate a task."""
        if not self.session or not self.current_run:
            return
        
        try:
            # Record the test result which will trigger task generation
            record_test_result(
                self.session,
                test_run_id=self.current_run.id,
                test_name=test_name,
                test_node_id=f"{test_file}::{test_name}",
                dataset_name="test_execution",
                expected_result=None,
                actual_result=None,
                status="failed",
                confidence_score=None,
                file_path=test_file,
                description=None,
                duration_ms=None,
                output=None,
                error_message=failure_reason,
                created_by_employee_id=DEFAULT_EMPLOYEE_ID,
                created_by_user_id=DEFAULT_USER_ID,
            )
            self.session.commit()
            print(f"✓ Generated task for failing test: {test_name}")
        except Exception as e:
            print(f"Warning: Could not generate task for {test_name}: {e}")
            self.session.rollback()
    
    def close(self):
        """Close the database session."""
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass


# Global test failure collector
test_failure_collector = TestFailureCollector()


@pytest.fixture(scope="session", autouse=True)
def initialize_test_run():
    """Initialize the test run session for task generation."""
    org_id = int(os.getenv("TEST_ORGANIZATION_ID", DEFAULT_ORG_ID))
    test_failure_collector.start_session(org_id=org_id)
    yield
    test_failure_collector.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test failures and generate tasks.
    
    Called after each test phase (setup, call, teardown).
    We use it to capture failure information and create governance tasks.
    """
    outcome = yield
    rep = outcome.get_result()
    
    # Only process failures from the test call phase
    if rep.failed and call.when == "call":
        test_name = item.name
        test_file = item.fspath.strpath
        
        # Get the failure reason
        failure_reason = None
        if rep.longrepr:
            try:
                failure_reason = str(rep.longrepr)[:500]  # Capture first 500 chars of error
            except Exception:
                failure_reason = "Test failed - see logs for details"
        
        if not failure_reason:
            failure_reason = "Test assertion failed"
        
        # Record the failure and generate a task
        test_failure_collector.record_test_failure(
            test_name=test_name,
            test_file=test_file,
            failure_reason=failure_reason,
        )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "task_generation: mark test to trigger task generation on failure",
    )


# Optional: Custom marker support
def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items.
    
    You can add special handling for tests marked with task_generation marker.
    """
    for item in items:
        if "task_generation" in item.keywords:
            # This test is marked for task generation (default behavior)
            pass
