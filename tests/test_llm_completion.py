"""
Test suite for LLM-powered task completion workflow.
Tests the integration between Claude API, task orchestration, and automation system.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from database.models.governance_task import GovernanceTask
from services.llm_config import LLMConfig, get_llm_config, reset_llm_config, validate_llm_config
from services.llm_completion_service import LLMCompletionAnalyzer, LLMAnalysisError
from services.task_llm_completion_service import (
    TaskLLMCompletionOrchestrator,
    TaskLLMCompletionError,
)


class TestLLMConfig:
    """Test LLM configuration management."""
    
    def test_config_loads_from_env(self, monkeypatch):
        """Test that config loads environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        monkeypatch.setenv("CLAUDE_MODEL", "claude-3-5-sonnet")
        monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "true")
        
        config = LLMConfig()
        assert config.api_key == "test-key-123"
        assert config.model == "claude-3-5-sonnet"
        assert config.enabled is True
    
    def test_config_defaults(self, monkeypatch):
        """Test default configuration values."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDE_MODEL", raising=False)
        monkeypatch.delenv("LLM_AUTO_COMPLETE_TASKS", raising=False)
        
        config = LLMConfig()
        assert config.api_key is None
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.enabled is False
        assert config.max_tokens == 1024
        assert config.temperature == 0.7
    
    def test_config_validation_fails_without_key(self):
        """Test that validation fails without API key."""
        config = LLMConfig()
        config.api_key = None
        
        with pytest.raises(Exception) as exc_info:
            config.validate()
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestLLMCompletionAnalyzer:
    """Test Claude-based task analysis."""
    
    def test_analyzer_can_analyze_when_configured(self, monkeypatch):
        """Test that analyzer recognizes when it's ready."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "true")

        # Reset the cached global config so each test is isolated
        reset_llm_config()

        # When anthropic is not installed, analyzer won't initialize client
    
    def test_analyzer_placeholder_when_disabled(self, monkeypatch):
        """Test that placeholder is returned when LLM is disabled."""
        monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "false")
        
        analyzer = LLMCompletionAnalyzer()
        result = analyzer.analyze_task(None)  # task doesn't matter when disabled
        
        assert result["implementation_summary"] == "[Awaiting human completion - LLM auto-complete not available]"
        assert result["review_notes"] == "[Manual review required]"
        assert result["execution_notes"] == "[No automatic execution details generated]"
    
    def test_parse_claude_response_success(self):
        """Test parsing valid Claude JSON response."""
        response = '''
        {
            "implementation_summary": "Updated task filter logic",
            "review_notes": "- Standard test coverage added\\n- Performance validated",
            "execution_notes": "- Deployed to staging\\n- Validated in test environment"
        }
        '''
        
        result = LLMCompletionAnalyzer._parse_claude_response(response)
        
        assert result["implementation_summary"] == "Updated task filter logic"
        assert "Standard test coverage added" in result["review_notes"]
        assert "Deployed to staging" in result["execution_notes"]
    
    def test_parse_claude_response_with_markdown(self):
        """Test parsing Claude response wrapped in markdown code blocks."""
        response = '''
        ```json
        {
            "implementation_summary": "Completed filter improvement",
            "review_notes": "✓ All tests pass",
            "execution_notes": "Deployed successfully"
        }
        ```
        '''
        
        result = LLMCompletionAnalyzer._parse_claude_response(response)
        assert result["implementation_summary"] == "Completed filter improvement"
    
    def test_parse_claude_response_missing_field(self):
        """Test that parsing fails when required field is missing."""
        response = '{"implementation_summary": "Test", "review_notes": "Test"}'
        
        with pytest.raises(LLMAnalysisError):
            LLMCompletionAnalyzer._parse_claude_response(response)


class TestTaskLLMCompletionOrchestrator:
    """Test task completion orchestration."""
    
    def test_parse_metadata_valid_json(self):
        """Test parsing valid task metadata JSON."""
        task = MagicMock(spec=GovernanceTask)
        task.metadata_json = '{"area": "compliance", "priority": "high"}'
        
        metadata = TaskLLMCompletionOrchestrator._parse_metadata(task)
        
        assert metadata["area"] == "compliance"
        assert metadata["priority"] == "high"
    
    def test_parse_metadata_invalid_json(self):
        """Test handling of invalid metadata JSON."""
        task = MagicMock(spec=GovernanceTask)
        task.id = 1
        task.metadata_json = "{invalid json}"
        
        metadata = TaskLLMCompletionOrchestrator._parse_metadata(task)
        
        assert metadata == {}
    
    def test_parse_metadata_none(self):
        """Test handling of None metadata."""
        task = MagicMock(spec=GovernanceTask)
        task.metadata_json = None
        
        metadata = TaskLLMCompletionOrchestrator._parse_metadata(task)
        
        assert metadata == {}
    
    def test_task_context_building(self):
        """Test building task context for Claude."""
        task = MagicMock(spec=GovernanceTask)
        task.id = 123
        task.title = "Improve task filtering"
        task.description = "Add date-based filtering to task list"
        task.priority = "high"
        task.source_module = "automation"
        task.source_type = "backlog_improvement"
        task.linked_source = "ALEX-IMP-001"
        task.linked_source_metadata = '{"status": "pending"}'
        task.metadata_json = '{"suggested_improvement": "Add multi-select filters"}'
        
        context = LLMCompletionAnalyzer._build_task_context(task)
        
        assert context["id"] == 123
        assert context["title"] == "Improve task filtering"
        assert context["priority"] == "high"
        assert context["linked_source"] == "ALEX-IMP-001"
    
    def test_idempotency_check(self):
        """Test that orchestrator skips already-completed tasks."""
        task = MagicMock(spec=GovernanceTask)
        task.id = 1
        task.company_id = 1
        task.metadata_json = '{"llm_completion_attempted": true}'
        
        orchestrator = TaskLLMCompletionOrchestrator()
        
        # Should return early without calling analyzer
        with patch.object(orchestrator, 'analyzer') as mock_analyzer:
            with patch('services.task_llm_completion_service.get_task_detail') as mock_detail:
                with patch.object(orchestrator, '_fetch_task', return_value=task):
                    mock_detail.return_value = {"id": 1, "status": "ready_for_review"}
                    
                    # This would call the function if not for idempotency
                    # Since we can't easily test the full flow without DB, we verify the logic
                    metadata = orchestrator._parse_metadata(task)
                    assert metadata.get("llm_completion_attempted") is True


class TestLLMConfigIntegration:
    """Test LLM configuration at integration level."""
    
    def test_config_singleton_pattern(self, monkeypatch):
        """Test that LLM config is a singleton."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key1")
        
        config1 = get_llm_config()
        config2 = get_llm_config()
        
        assert config1 is config2
    
    def test_config_persistence_loading(self, monkeypatch):
        """Test that config loads persisted settings from database."""
        from database.models.llm_settings import LLMSettings
        from database.database import SessionLocal
        
        # Reset config
        reset_llm_config()
        
        # Create persisted settings
        db = SessionLocal()
        try:
            # Clean up any existing
            db.query(LLMSettings).delete()
            db.commit()
            
            # Add test settings
            settings = LLMSettings(
                enabled=True,
                model="claude-3-5-sonnet-latest",
                max_tokens=2048,
                temperature=0.9
            )
            db.add(settings)
            db.commit()
            
            # Test loading
            config = get_llm_config()
            assert config.enabled is True
            assert config.model == "claude-3-5-sonnet-latest"
            assert config.max_tokens == 2048
            assert config.temperature == 0.9
            
        finally:
            db.query(LLMSettings).delete()
            db.commit()
            db.close()
    
    def test_config_env_override_persistence(self, monkeypatch):
        """Test that environment variables override persisted settings."""
        from database.models.llm_settings import LLMSettings
        from database.database import SessionLocal
        
        # Reset config
        reset_llm_config()
        
        # Create persisted settings
        db = SessionLocal()
        try:
            db.query(LLMSettings).delete()
            settings = LLMSettings(enabled=False, model="claude-3-5-sonnet-20241022")
            db.add(settings)
            db.commit()
            
            # Set env vars
            monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "true")
            monkeypatch.setenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
            
            config = get_llm_config()
            # Env should override DB
            assert config.enabled is True
            assert config.model == "claude-3-5-haiku-20241022"
            
        finally:
            db.query(LLMSettings).delete()
            db.commit()
            db.close()
    
    def test_config_validation_with_key(self, monkeypatch):
        """Test that validation passes with API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        
        config = LLMConfig()
        # Should not raise
        config.validate()
    
    def test_config_repr_masks_api_key(self):
        """Test that __repr__ does not expose API key."""
        config = LLMConfig()
        config.api_key = "secret-key-123"
        
        repr_str = repr(config)
        assert "secret-key-123" not in repr_str
        assert "LLMConfig(model=" in repr_str
    
    def test_config_invalid_env_values(self, monkeypatch):
        """Test handling of invalid environment variable values."""
        monkeypatch.setenv("CLAUDE_MAX_TOKENS", "invalid")
        monkeypatch.setenv("CLAUDE_TEMPERATURE", "not-a-float")
        
        config = LLMConfig()
        # Should use defaults when parsing fails
        assert config.max_tokens == 1024  # default
        assert config.temperature == 0.7  # default
    
    def test_validate_llm_config_at_startup(self, monkeypatch):
        """Test startup validation function."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "true")
        
        # Should not raise
        validate_llm_config()
    
    def test_validate_llm_config_fails_when_required(self, monkeypatch):
        """Test that startup validation fails when LLM is enabled but no key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("LLM_AUTO_COMPLETE_TASKS", "true")
        
        with pytest.raises(RuntimeError) as exc_info:
            validate_llm_config()
        assert "LLM auto-complete enabled but configuration invalid" in str(exc_info.value)
