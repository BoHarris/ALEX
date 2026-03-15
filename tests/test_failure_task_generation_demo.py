"""
Demonstration: Automatic Task Generation from Test Failures

This test file demonstrates how the system automatically generates governance tasks
when tests fail. When you run pytest on this suite, any failures will automatically
create tasks in the governance task system.

To run these tests:
    pytest tests/test_failure_task_generation_demo.py -v
    
To see generated tasks, check the governance_tasks table:
    SELECT * FROM governance_tasks WHERE source_type = 'test_failure' ORDER BY created_at DESC;
"""
import pytest


@pytest.mark.task_generation
def test_database_connection():
    """
    A sample test that should pass.
    No task will be generated for passing tests.
    """
    assert True


@pytest.mark.task_generation
def test_api_response_validation():
    """
    A sample test that will fail and generate a task.
    The task will contain details about why this test failed.
    """
    # This will fail and trigger task generation
    expected = 200
    actual = 500
    assert actual == expected, f"API returned {actual}, expected {expected}"


@pytest.mark.task_generation
def test_data_integrity_check():
    """
    Another sample test that will fail.
    Each failure generates a separate task.
    """
    data = {"status": "error"}
    assert data["status"] == "success", "Data integrity check failed"


@pytest.mark.task_generation  
def test_performance_threshold():
    """
    Sample performance test that will fail.
    """
    response_time = 5000  # milliseconds
    max_allowed = 1000
    assert response_time <= max_allowed, f"Response time {response_time}ms exceeds threshold {max_allowed}ms"


class TestFeatureIntegration:
    """Test class with multiple tests that can each generate tasks on failure."""
    
    @pytest.mark.task_generation
    def test_user_registration_flow(self):
        """Test user registration integration."""
        user_created = False
        assert user_created, "User registration failed"
    
    @pytest.mark.task_generation
    def test_authentication_token_generation(self):
        """Test authentication token generation."""
        token = None
        assert token is not None, "Failed to generate authentication token"
    
    @pytest.mark.task_generation
    def test_permission_verification(self):
        """Test permission verification."""
        has_permission = False
        assert has_permission, "User does not have required permissions"


# Example of a test that would pass (no task generated)
@pytest.mark.task_generation
def test_library_import():
    """This test passes, so no task will be generated."""
    import sys
    assert sys.version_info.major >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
