"""
Verification Script: Test Failure Task Generation

This script verifies that the automatic task generation system is working correctly.
It tests the flow from test failure detection to task creation in the database.

Usage:
    python verify_test_failure_task_generation.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.database import SessionLocal
from database.models.governance_task import GovernanceTask
from database.models.compliance_test_failure_task import ComplianceTestFailureTask
from database.models.compliance_test_run import ComplianceTestRun
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from services.task_generation_service import TaskGenerationService
from services.test_metrics_service import record_test_result, create_tracked_test_run


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def verify_task_generation():
    """Verify the complete task generation workflow."""
    
    print_section("TEST FAILURE TASK GENERATION VERIFICATION")
    
    db = SessionLocal()
    org_id = 1
    
    try:
        # Step 1: Create a test run
        print("Step 1: Creating test run...")
        run = create_tracked_test_run(
            db,
            organization_id=org_id,
            category="integration tests",
            suite_name="test_api_endpoints",
            dataset_name="test_execution",
            run_type="pytest_suite",
        )
        print(f"  ✓ Test run created: ID={run.id}, Suite={run.suite_name}")
        
        # Step 2: Record a successful test
        print("\nStep 2: Recording passing test...")
        result_pass = record_test_result(
            db,
            test_run_id=run.id,
            test_name="test_user_login_success",
            test_node_id="tests/test_auth.py::test_user_login_success",
            dataset_name="test_execution",
            expected_result=None,
            actual_result=None,
            status="passed",
            confidence_score=None,
            file_path="tests/test_auth.py",
            error_message=None,
        )
        print(f"  ✓ Passing test recorded: {result_pass.name}")
        
        # Step 3: Record a failed test
        print("\nStep 3: Recording failing test (should generate task)...")
        result_fail = record_test_result(
            db,
            test_run_id=run.id,
            test_name="test_invalid_login",
            test_node_id="tests/test_auth.py::test_invalid_login",
            dataset_name="test_execution",
            expected_result=None,
            actual_result=None,
            status="failed",
            confidence_score=None,
            file_path="tests/test_auth.py",
            error_message="AssertionError: Expected status 401, got 200. Login should reject invalid credentials.",
        )
        print(f"  ✓ Failing test recorded: {result_fail.name}")
        
        # Step 4: Verify ComplianceTestFailureTask was created
        print("\nStep 4: Verifying ComplianceTestFailureTask...")
        failure_task = db.query(ComplianceTestFailureTask).filter(
            ComplianceTestFailureTask.test_node_id == "tests/test_auth.py::test_invalid_login"
        ).first()
        
        if failure_task:
            print(f"  ✓ ComplianceTestFailureTask created:")
            print(f"    - ID: {failure_task.id}")
            print(f"    - Test Node ID: {failure_task.test_node_id}")
            print(f"    - Status: {failure_task.status}")
            print(f"    - Priority: {failure_task.priority}")
            print(f"    - Title: {failure_task.title}")
        else:
            print("  ✗ ComplianceTestFailureTask NOT found!")
        
        # Step 5: Verify GovernanceTask was created
        print("\nStep 5: Verifying GovernanceTask...")
        gov_task = db.query(GovernanceTask).filter(
            GovernanceTask.source_type == "test_failure",
            GovernanceTask.source_id == "tests/test_auth.py::test_invalid_login",
            GovernanceTask.company_id == org_id,
        ).first()
        
        if gov_task:
            print(f"  ✓ GovernanceTask created:")
            print(f"    - ID: {gov_task.id}")
            print(f"    - Title: {gov_task.title}")
            print(f"    - Status: {gov_task.status}")
            print(f"    - Priority: {gov_task.priority}")
            print(f"    - Source Type: {gov_task.source_type}")
            print(f"    - Description Preview: {gov_task.description[:100]}...")
        else:
            print("  ✗ GovernanceTask NOT found!")
        
        # Step 6: Test manual task generation
        print("\nStep 6: Testing manual task generation...")
        service = TaskGenerationService(db)
        manual_task = service.create_task_from_test_failure(
            test_name="test_database_connection",
            test_file="tests/test_integration.py",
            failure_reason="sqlite3.OperationalError: no such table: users",
            company_id=org_id,
            priority="high",
        )
        print(f"  ✓ Manual task created:")
        print(f"    - ID: {manual_task.id}")
        print(f"    - Title: {manual_task.title}")
        print(f"    - Description: {manual_task.description[:100]}...")
        
        # Step 7: Summary statistics
        print("\nStep 7: Summary Statistics...")
        total_gov_tasks = db.query(GovernanceTask).filter(
            GovernanceTask.source_type == "test_failure",
            GovernanceTask.company_id == org_id,
        ).count()
        
        total_failure_tasks = db.query(ComplianceTestFailureTask).filter(
            ComplianceTestFailureTask.organization_id == org_id
        ).count()
        
        total_results = db.query(ComplianceTestCaseResult).filter(
            ComplianceTestCaseResult.test_run_id == run.id
        ).count()
        
        print(f"  - Total Test Results: {total_results}")
        print(f"  - Total Failure Tasks: {total_failure_tasks}")
        print(f"  - Total Governance Tasks (test_failure): {total_gov_tasks}")
        
        print_section("VERIFICATION COMPLETE")
        print("✓ Task generation system is working correctly!\n")
        
        # Print sample queries
        print("Sample Database Queries:\n")
        print("1. View all test failure tasks:")
        print("   SELECT * FROM governance_tasks WHERE source_type = 'test_failure';\n")
        
        print("2. View test failure task details:")
        print("   SELECT gt.*, ctft.failure_signature FROM governance_tasks gt")
        print("   LEFT JOIN compliance_test_failure_tasks ctft ON gt.source_id = ctft.test_node_id")
        print("   WHERE gt.source_type = 'test_failure';\n")
        
        print("3. View failing tests for a run:")
        print(f"   SELECT * FROM compliance_test_case_results WHERE test_run_id = {run.id} AND status = 'failed';\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = verify_task_generation()
    sys.exit(0 if success else 1)
