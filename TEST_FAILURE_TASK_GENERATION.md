"""
Automatic Test Failure Task Generation - Implementation Guide

OVERVIEW
========

When tests fail during execution, the system automatically generates governance tasks
to track and manage the failures. This ensures that test failures are not overlooked
and can be properly addressed through the governance workflow.

ARCHITECTURE
============

The task generation system consists of three layers:

1. PYTEST HOOKS (tests/conftest.py)
   - Captures test execution results
   - Detects test failures
   - Collects failure reason/error message
   - Coordinates with task generation

2. TEST METRICS SERVICE (services/test_metrics_service.py)
   - record_test_result(): Records test outcomes
   - Triggers upsert_failure_task_for_result() for failures
   - Updates test run statistics

3. TEST FAILURE TASK SERVICE (services/test_failure_task_service.py)
   - upsert_failure_task_for_result(): Creates/updates tasks
   - _sync_governance_task(): Creates GovernanceTask
   - Manages ComplianceTestFailureTask entities

4. TASK GENERATION SERVICE (services/task_generation_service.py)
   - create_task(): Core task creation logic
   - create_task_from_test_failure(): Specialized test failure handling
   - Stores failure details and metadata

5. MODELS
   - GovernanceTask: Main task entity
   - ComplianceTestFailureTask: Test-specific task tracking
   - ComplianceTestCaseResult: Test result records
   - ComplianceTestRun: Test suite execution records

WORKFLOW
========

1. Test Execution:
   pytest runs tests and encounters failures

2. Test Result Recording:
   record_test_result() is called with:
   - test_name: Name of the failing test
   - test_node_id: pytest node ID (file::test)
   - status: "failed"
   - error_message: Failure reason/stack trace
   - file_path: Location of test file

3. Failure Detection:
   If status == "failed":
   → upsert_failure_task_for_result() is triggered

4. Task Creation:
   A ComplianceTestFailureTask is created with:
   - test_node_id: Unique identifier for the test
   - failure_signature: Normalized error message
   - title: "Investigate failing test: {test_name}"
   - description: Full details including error message
   - status: "open"
   - priority: Derived from test category

5. Governance Task Sync:
   _sync_governance_task() creates a GovernanceTask:
   - source_type: "test_failure"
   - source_id: test_node_id
   - metadata: Failure details and run info
   - description: Includes error message
   - priority: Based on test category

6. Task Available:
   - Task appears in compliance/tasks endpoints
   - Can be assigned to team members
   - Status tracked through workflow

CONFIGURATION
==============

Environment Variables:
- TEST_ORGANIZATION_ID: Organization for generated tasks (default: 1)
- TEST_EXECUTION_TIMEOUT_SECONDS: Max test execution time (default: 900)
- TEST_EXECUTION_MAX_LOG_CHARS: Max log size captured (default: 40000)

Pytest Configuration (pytest.ini):
- testpaths: tests directory
- addopts: -p no:cacheprovider
- markers: task_generation marker available

USAGE
=====

1. Run Tests with Automatic Task Generation:
   pytest tests/test_failure_task_generation_demo.py -v
   
2. View Generated Tasks:
   GET /compliance/tasks
   
   Also check:
   SELECT * FROM governance_tasks 
   WHERE source_type = 'test_failure' 
   ORDER BY created_at DESC;

3. Assign and Track:
   - Tasks appear in the governance dashboard
   - Can be assigned to team members
   - Status updated as team works on fixes
   - Original error message preserved for context

FAILURE REASON CAPTURE
=====================

The system captures:
- Full test name
- File path  
- Error message/traceback
- Duration (if available)
- Dataset name
- Suite/category information

All details are stored in:
- task.description: Human-readable summary
- task.metadata_json: Structured failure data
- compliance_test_failure_task.failure_signature: Normalized error
- compliance_test_case_result.error_message: Raw error output

PRIORITY ASSIGNMENT
===================

Task priority is automatically determined based on test category:

- security tests → HIGH
- integration tests → HIGH  
- privacy tests → MEDIUM
- other tests → LOW

MULTI-FAILURE HANDLING
======================

For test suites with multiple failures:
- One task is created per failing test
- Each task contains specific failure details
- Related tasks can be viewed from the test run

Example:
  Suite: test_api_endpoints.py runs 5 tests
  Results: 3 pass, 2 fail
  → 2 tasks generated (one for each failure)

DEDUPLICATION
==============

The system provides smart deduplication:
- Same test failure in consecutive runs updates existing task
- failure_signature tracks normalized error messages
- Duplicate failures don't create multiple tasks
- Latest run info always updated

Task Status Flow:
  open → in_progress → resolved/closed
  
Updates are recorded when:
- Same test fails again (preserves task)
- Same test passes (can mark resolved)
- Different error for same test (updates description)

INTEGRATION WITH TESTING WORKFLOW
==================================

1. Developer runs tests locally:
   pytest tests/ -v
   → Failures generate tasks if test is marked @task_generation

2. CI/CD runs full suite:
   pytest tests/ --junit-xml=report.xml
   → All failures create/update tasks

3. Team reviews failures:
   Check /compliance/tasks with source_type='test_failure'
   → Assign to developers
   → Track resolution progress

4. Once fixed:
   Re-run test → test passes
   → Same node_id now has status='passed'
   → Task can be marked resolved

CUSTOMIZATION
==============

To mark specific tests for task generation:
    @pytest.mark.task_generation
    def test_important_feature():
        assert critical_check()

To use with existing tests:
    Tests run with conftest.py automatically
    No changes needed to existing test code
    All failures tracked by default

To disable task generation for specific test:
    # Remove @pytest.mark.task_generation decorator
    def test_experimental_feature():
        # This won't generate tasks on failure

Example: Custom Task Generation
    from services.task_generation_service import TaskGenerationService
    from database.database import SessionLocal
    
    db = SessionLocal()
    service = TaskGenerationService(db)
    
    # Manually create task from test failure
    task = service.create_task_from_test_failure(
        test_name="test_user_login",
        test_file="tests/test_auth.py",
        failure_reason="AssertionError: Expected 200, got 401",
        company_id=1,
        priority="high"
    )

MONITORING & ALERTING
=====================

Check task generation health:
    SELECT COUNT(*) FROM governance_tasks 
    WHERE source_type = 'test_failure' 
    AND created_at > NOW() - INTERVAL '24 hours';

View recent failures by category:
    SELECT gt.*, cr.suite_name 
    FROM governance_tasks gt
    LEFT JOIN compliance_test_failure_task ctft ON gt.source_id = ctft.test_node_id
    WHERE source_type = 'test_failure'
    ORDER BY gt.created_at DESC;

TROUBLESHOOTING
===============

Issue: Tasks not being created
Solution: 
- Verify conftest.py is in tests/ directory
- Check TEST_ORGANIZATION_ID env var
- Ensure database session is initialized
- Check logs for errors in record_test_result()

Issue: Duplicate tasks for same failure
Solution:
- This shouldn't happen - system deduplicates by test_node_id
- If occurring, check for node_id collision
- Review upsert_failure_task_for_result() logic

Issue: Task priority incorrect
Solution:
- Check test run category setting
- Verify test category matches rule in test_metrics_service.py
- Review _task_priority() function in test_failure_task_service.py

BEST PRACTICES
==============

1. Add @pytest.mark.task_generation to critical tests
   - Tests for security features
   - Integration point tests
   - Data integrity tests

2. Write clear test names and failure messages
   - Good: test_user_cannot_access_admin_without_permission()
   - Bad: test_security()

3. Use assertions with descriptive messages
   - Good: assert token is not None, "Failed to generate auth token"
   - Bad: assert token

4. Run tests frequently to catch failures early
   - Local testing during development
   - Pre-commit hooks for changes
   - CI/CD for baseline suite

5. Review and resolve tasks promptly
   - Check /compliance/tasks regularly
   - Assign to appropriate team member
   - Update task status as work progresses

6. Learn from patterns
   - Monitor which tests fail most frequently
   - Improve flaky tests
   - Strengthen test suite based on failures
"""

# This file serves as documentation for the automatic test failure task generation system.
# For implementation details, see:
# - tests/conftest.py - pytest hooks and configuration
# - services/test_failure_task_service.py - failure task handling
# - services/task_generation_service.py - governance task creation
# - services/test_metrics_service.py - test result recording
# - database/models/governance_task.py - task model
