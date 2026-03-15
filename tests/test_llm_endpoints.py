"""
Integration tests for LLM admin endpoints.
Tests the full API flow for LLM management features.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app  # Import the FastAPI app
from database.database import SessionLocal
from database.models.governance_task import GovernanceTask
from database.models.company import Company
from database.models.employee import Employee


@pytest.fixture
def client():
    """Test client for API calls."""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Test database session."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_company_and_admin(test_db):
    """Create test company and admin user."""
    # Create company
    company = Company(name="Test Corp", status="active")
    test_db.add(company)
    test_db.flush()

    # Create admin employee
    admin = Employee(
        company_id=company.id,
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        role="admin"
    )
    test_db.add(admin)
    test_db.commit()

    return company, admin


@pytest.fixture
def test_task(test_db, test_company_and_admin):
    """Create a test governance task."""
    company, admin = test_company_and_admin

    task = GovernanceTask(
        company_id=company.id,
        title="Test Task",
        description="A test task for LLM integration",
        priority="medium",
        status="in_progress",
        source_module="test",
        source_type="manual"
    )
    test_db.add(task)
    test_db.commit()

    return task


def test_llm_status_endpoint(client, test_company_and_admin):
    """Test GET /api/llm/status endpoint."""
    company, admin = test_company_and_admin

    # Mock authentication
    with patch('dependencies.tier_guard.require_security_admin') as mock_auth:
        mock_auth.return_value = {"id": admin.id, "company_id": company.id}

        response = client.get(f"/api/llm/status?company_id={company.id}")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "model" in data
        assert "api_key_configured" in data
        assert "max_tokens" in data
        assert "temperature" in data
        assert "tasks_with_llm_generation" in data
        assert "avg_generation_time_seconds" in data
        assert "last_error" in data


def test_llm_settings_endpoint(client, test_company_and_admin):
    """Test POST /api/llm/settings endpoint."""
    company, admin = test_company_and_admin

    # Mock authentication
    with patch('dependencies.tier_guard.require_security_admin') as mock_auth:
        mock_auth.return_value = {"id": admin.id, "company_id": company.id}

        # Test updating settings
        settings_data = {
            "enabled": True,
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "temperature": 0.8
        }

        response = client.post("/api/llm/settings", json=settings_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "current_settings" in data


def test_llm_task_history_endpoint(client, test_company_and_admin, test_task):
    """Test GET /api/llm/task-history/{task_id} endpoint."""
    company, admin = test_company_and_admin

    # Mock authentication
    with patch('dependencies.tier_guard.require_security_admin') as mock_auth:
        mock_auth.return_value = {"id": admin.id, "company_id": company.id}

        response = client.get(f"/api/llm/task-history/{test_task.id}?company_id={company.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == test_task.id
        assert "llm_attempted" in data
        assert "llm_successful" in data
        assert "generations" in data
        assert isinstance(data["generations"], list)


@patch('services.task_llm_completion_service.generate_and_submit_llm_completion')
def test_llm_generate_completion_endpoint(mock_generate, client, test_company_and_admin, test_task):
    """Test POST /api/llm/generate-completion/{task_id} endpoint."""
    company, admin = test_company_and_admin

    # Mock the service call
    mock_generate.return_value = {
        "status": "success",
        "message": "LLM completion generated",
        "task_id": test_task.id,
        "llm_model": "claude-3-5-sonnet-20241022",
        "generated_fields": ["implementation_summary"],
        "timestamp": "2024-01-01T00:00:00Z"
    }

    # Mock authentication
    with patch('dependencies.tier_guard.require_security_admin') as mock_auth:
        mock_auth.return_value = {"id": admin.id, "company_id": company.id}

        response = client.post(f"/api/llm/generate-completion/{test_task.id}?company_id={company.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["task_id"] == test_task.id
        assert "llm_model" in data


def test_llm_settings_validation(client, test_company_and_admin):
    """Test input validation for LLM settings."""
    company, admin = test_company_and_admin

    # Mock authentication
    with patch('dependencies.tier_guard.require_security_admin') as mock_auth:
        mock_auth.return_value = {"id": admin.id, "company_id": company.id}

        # Test invalid model
        response = client.post("/api/llm/settings", json={"model": "invalid-model"})
        assert response.status_code == 400

        # Test invalid temperature
        response = client.post("/api/llm/settings", json={"temperature": 2.0})
        assert response.status_code == 400

        # Test invalid max_tokens
        response = client.post("/api/llm/settings", json={"max_tokens": 0})
        assert response.status_code == 400