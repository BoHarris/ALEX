"""
QUICK START: Automatic Test Failure Task Generation

===============================================================================
OVERVIEW
===============================================================================

Your ALEX platform now automatically generates governance tasks when tests fail!

When a test fails:
1. The system captures the failure reason (error message)
2. A task is created with the failure details
3. The task appears in the governance dashboard
4. Your team can assign and track the fix


===============================================================================
HOW IT WORKS (3 STEPS)
===============================================================================

STEP 1: Test Runs and Fails
   pytest runs your test suite
   → A test fails with an error

STEP 2: System Captures Failure
   The pytest hook automatically:
   ✓ Captures the test name (e.g., test_user_login)
   ✓ Captures the file location (e.g., tests/test_auth.py)
   ✓ Captures the failure reason (error message)
   ✓ Records a ComplianceTestFailureTask

STEP 3: Governance Task Created
   A GovernanceTask is automatically created with:
   ✓ Title: "Investigate failing test: {test_name}"
   ✓ Description: Includes failure reason
   ✓ Status: "todo" (ready for assignment)
   ✓ Priority: Based on test category
   ✓ Source: test_failure


===============================================================================
RUNNING TESTS
===============================================================================

To run tests and automatically generate tasks:

    # Run a specific test file
    pytest tests/test_auth.py -v

    # Run a specific test
    pytest tests/test_auth.py::test_user_login -v

    # Run entire test suite
    pytest tests/ -v

    # Run with verbose output
    pytest tests/ -vv

Any failures will automatically create tasks!


===============================================================================
VIEWING GENERATED TASKS
===============================================================================

Option 1: Via API
   GET http://127.0.0.1:8000/compliance/tasks
   
   Response shows all tasks including test failures as:
   {
     "id": 1,
     "title": "Investigate failing test: test_user_login",
     "status": "todo",
     "priority": "high",
     "source_type": "test_failure",
     "description": "..."
   }

Option 2: Via Database
   sqlite3 <your_db_file>
   
   SELECT * FROM governance_tasks 
   WHERE source_type = 'test_failure' 
   ORDER BY created_at DESC;

Option 3: Dashboard UI
   Navigate to /compliance/tasks in your browser


===============================================================================
UNDERSTANDING TASK PRIORITY
===============================================================================

Priority is automatically set based on test category:

High Priority:
   ✓ security tests → HIGH (security-related failures)
   ✓ integration tests → HIGH (cross-system failures)

Medium Priority:
   ✓ privacy tests → MEDIUM (privacy-related issues)

Low Priority:
   ✓ other tests → LOW (unit tests, documentation tests, etc.)


===============================================================================
MULTI-FAILURE HANDLING
===============================================================================

When a test suite fails with multiple failures:

Example Suite Run:
   tests/test_api.py::test_endpoint_1 ✓ PASS
   tests/test_api.py::test_endpoint_2 ✗ FAIL
   tests/test_api.py::test_endpoint_3 ✓ PASS
   tests/test_api.py::test_endpoint_4 ✗ FAIL

Result:
   ✓ 2 tasks are generated (one per failure)
   ✓ Each task has its own failure details
   ✓ Each can be assigned and tracked separately


===============================================================================
TASK DETAILS CAPTURED
===============================================================================

Each generated task includes:

Title:
   "Investigate failing test: test_name"

Description (includes):
   • Test name
   • File location
   • Suite name
   • Environment/dataset
   • Complete failure reason (first 200 chars)

Metadata (accessible via API):
   • test_name: Name of the failing test
   • test_file: Path to test file
   • failure_reason: Full error message
   • failure_signature: Normalized error (for deduplication)

Tracking Info:
   • created_at: When the failure was detected
   • updated_at: Last failure detection
   • source_id: Unique test identifier (file::test_name)


===============================================================================
EXAMPLE WORKFLOW
===============================================================================

1. Developer makes code changes
   $ git commit -m "Fix user authentication"

2. Run tests locally
   $ pytest tests/test_auth.py -v
   
   Result:
   FAILED tests/test_auth.py::test_login_with_invalid_password
   ErrorMessage: Expected 401, got 200 - invalid password was accepted

3. Task automatically created
   ✓ Check /compliance/tasks or GET /compliance/tasks API
   ✓ New task appears: "Investigate failing test: test_login_with_invalid_password"
   ✓ Status: "todo"
   ✓ Priority: "high"

4. Team reviews task
   ✓ Reads the captured error message
   ✓ Understands exactly what failed
   ✓ Assigns to appropriate developer

5. Developer fixes and re-runs
   $ pytest tests/test_auth.py -v
   
   Result:
   PASSED tests/test_auth.py::test_login_with_invalid_password

6. Task marked as resolved
   ✓ Test passes on next run
   ✓ Same task_id is referenced
   ✓ Status updated to reflect resolution


===============================================================================
MARKING TESTS FOR SPECIFIC HANDLING
===============================================================================

Use pytest markers to highlight important tests:

   @pytest.mark.task_generation
   def test_critical_feature():
       """This test will generate a task if it fails."""
       assert critical_check()

All tests generate tasks by default. The marker is optional for documentation.


===============================================================================
CUSTOMIZING TASK GENERATION
===============================================================================

To manually create a task from a test failure:

   from services.task_generation_service import TaskGenerationService
   from database.database import SessionLocal
   
   db = SessionLocal()
   service = TaskGenerationService(db)
   
   task = service.create_task_from_test_failure(
       test_name="test_user_login",
       test_file="tests/test_auth.py",
       failure_reason="ConnectionError: Could not reach database",
       company_id=1,
       priority="high"
   )
   
   print(f"Task created with ID: {task.id}")


===============================================================================
DEDUPLICATION & UPDATES
===============================================================================

The system is smart about duplicate failures:

Scenario 1: Same Test Fails Again
   Run 1: test_login fails with "Expected 401, got 200"
   → Task created

   Run 2: test_login fails with "Expected 401, got 200"
   → SAME task updated (not duplicated)
   → updated_at timestamp refreshed

Scenario 2: Different Error for Same Test
   Run 1: test_login fails with "Expected 401, got 200"
   → Task created

   Run 2: test_login fails with "Connection timeout"
   → Task description updated with new error
   → Status remains open

Scenario 3: Test Starts Passing
   Run 1: test_login fails
   → Task created

   Run 2: test_login passes
   → Can mark task as resolved


===============================================================================
CONFIGURATION OPTIONS
===============================================================================

Set via environment variables:

# Organization ID for generated tasks
export TEST_ORGANIZATION_ID=1

# Max test execution time (seconds)
export TEST_EXECUTION_TIMEOUT_SECONDS=900

# Max log size to capture (chars)
export TEST_EXECUTION_MAX_LOG_CHARS=40000


===============================================================================
TROUBLESHOOTING
===============================================================================

Q: Task not appearing after test failure
A: 
   • Check /compliance/tasks API
   • Verify database is running
   • Check application logs for errors
   • Run: python verify_test_failure_task_generation.py

Q: Same test creates multiple tasks
A:
   • Should not happen - system deduplicates
   • Check test naming for duplicates
   • Review test_node_id generation

Q: Task priority not as expected
A:
   • Priority based on test category (see table above)
   • Check test run category setting
   • Review ComplianceTestRun.category field

Q: Error message not captured
A:
   • Ensure test has clear assertion errors
   • Check ComplianceTestCaseResult.error_message
   • Long messages truncated to 500 chars


===============================================================================
FILES MODIFIED/CREATED
===============================================================================

Created:
   ✓ tests/conftest.py
     - pytest hooks for failure detection
     - automatic test result recording
     
   ✓ tests/test_failure_task_generation_demo.py
     - sample tests demonstrating task generation
     
   ✓ TEST_FAILURE_TASK_GENERATION.md
     - comprehensive documentation
     
   ✓ verify_test_failure_task_generation.py
     - verification script

Modified:
   ✓ services/task_generation_service.py
     - enhanced test failure handling
     - added metadata support
     
   ✓ pytest.ini
     - configured pytest hooks
     - added markers


===============================================================================
NEXT STEPS
===============================================================================

1. Run the demo tests:
   pytest tests/test_failure_task_generation_demo.py -v

2. Try running the verification script:
   python verify_test_failure_task_generation.py

3. Run your existing tests:
   pytest tests/ -v
   → Watch tasks appear for failures!

4. Check the API:
   curl http://127.0.0.1:8000/compliance/tasks

5. View generated tasks in the dashboard:
   http://127.0.0.1:8000/compliance/tasks/


===============================================================================
SUPPORT & QUESTIONS
===============================================================================

For more details, see:
   • TEST_FAILURE_TASK_GENERATION.md - Full technical documentation
   • tests/conftest.py - Implementation details
   • services/task_generation_service.py - Task creation logic
   • services/test_failure_task_service.py - Failure tracking

Test it out and your team will now catch and track all test failures
automatically through the governance system!
"""

# This file provides a quick-start guide for the test failure task generation feature.
# Run the demo tests and verification script to see it in action!
