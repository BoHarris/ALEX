"""
Configuration and initialization for LLM (Claude Anthropic) services.
"""
import os
from typing import Optional


class LLMConfigError(Exception):
    """Raised when LLM configuration is invalid or missing."""
    pass


class LLMConfig:
    """Centralized LLM configuration."""
    
    def __init__(self):
        self.api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.model: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens: int = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))
        self.temperature: float = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
        self.enabled: bool = os.getenv("LLM_AUTO_COMPLETE_TASKS", "false").lower() == "true"
        
    def validate(self) -> None:
        """Validate configuration. Raises LLMConfigError if invalid."""
        if not self.api_key:
            raise LLMConfigError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "LLM services will not be available."
            )
    
    def is_available(self) -> bool:
        """Check if LLM is configured and available."""
        return bool(self.api_key) and self.enabled
    
    def __repr__(self) -> str:
        return (
            f"LLMConfig(model={self.model}, enabled={self.enabled}, "
            f"api_key={'***' if self.api_key else 'None'})"
        )


# Global config instance
_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """Get or initialize the global LLM config."""
    global _config
    if _config is None:
        _config = LLMConfig()
    return _config


def validate_llm_config() -> None:
    """Validate LLM config at startup. Call this during app initialization."""
    config = get_llm_config()
    if config.enabled:
        try:
            config.validate()
        except LLMConfigError as e:
            raise RuntimeError(f"LLM auto-complete enabled but configuration invalid: {e}") from e
