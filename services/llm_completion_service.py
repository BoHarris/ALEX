"""
Claude-powered task completion analysis service.
Analyzes automation tasks and generates implementation details.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from database.models.governance_task import GovernanceTask
from services.llm_config import get_llm_config, LLMConfigError

logger = logging.getLogger(__name__)

# Try to import anthropic, but don't fail if not available
try:
    from anthropic import Anthropic, APIError, APIConnectionError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. LLM completion will not be available.")


class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""
    pass


class LLMCompletionAnalyzer:
    """Analyzes governance tasks using Claude and generates completion details."""
    
    SYSTEM_PROMPT = """You are an automated compliance improvement assistant specializing in governance task completion.

Your role is to analyze compliance improvement tasks and generate realistic, actionable completion summaries.

When analyzing a task, you should:
1. Understand the improvement goal and scope
2. Consider industry best practices and compliance standards
3. Suggest realistic implementation steps
4. Propose measurable outcomes
5. Identify potential risks or considerations

Generate three outputs for each task:
- implementation_summary: A concise narrative (2-3 sentences) of what was completed
- review_notes: Key points for human review (2-3 bullet points)
- execution_notes: Technical details or evidence (2-3 bullet points)

All suggestions should be specific, plausible, and reference concrete deliverables."""
    
    def __init__(self):
        self.config = get_llm_config()
        self.client: Optional[Anthropic] = None
        
        if ANTHROPIC_AVAILABLE and self.config.api_key:
            try:
                self.client = Anthropic(api_key=self.config.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
    
    def can_analyze(self) -> bool:
        """Check if analyzer is ready to process tasks."""
        return self.client is not None and self.config.enabled
    
    def analyze_task(self, task: GovernanceTask) -> dict[str, str]:
        """
        Analyze a governance task and generate completion details.
        
        Args:
            task: GovernanceTask instance to analyze
            
        Returns:
            Dict with keys: implementation_summary, review_notes, execution_notes
            
        Raises:
            LLMAnalysisError: If analysis fails
        """
        if not self.can_analyze():
            logger.debug("LLM analyzer not available. Returning placeholder template.")
            return self._get_placeholder_template()
        
        try:
            # Build task context
            context = self._build_task_context(task)
            user_prompt = self._build_analysis_prompt(context)
            
            # Call Claude API
            logger.debug(f"Calling Claude API for task {task.id}")
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
            
            # Parse response
            response_text = message.content[0].text
            result = self._parse_claude_response(response_text)
            
            logger.info(f"LLM analysis completed for task {task.id}")
            return result
            
        except (APIError, APIConnectionError) as e:
            logger.error(f"Claude API error analyzing task {task.id}: {e}")
            raise LLMAnalysisError(f"Claude API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error analyzing task {task.id}: {e}")
            raise LLMAnalysisError(f"Analysis failed: {str(e)}") from e
    
    @staticmethod
    def _build_task_context(task: GovernanceTask) -> dict[str, Any]:
        """Extract relevant context from task."""
        metadata = {}
        if task.metadata_json:
            try:
                metadata = json.loads(task.metadata_json)
            except json.JSONDecodeError:
                logger.warning(f"Task {task.id} has invalid metadata_json")
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "source_module": task.source_module,
            "source_type": task.source_type,
            "linked_source": task.linked_source,
            "linked_source_metadata": task.linked_source_metadata,
            "metadata": metadata,
        }
    
    @staticmethod
    def _build_analysis_prompt(context: dict[str, Any]) -> str:
        """Build analysis prompt for Claude."""
        parts = [
            "Analyze the following governance improvement task and generate completion details:",
            "",
            f"Task ID: {context['id']}",
            f"Title: {context['title']}",
            f"Priority: {context['priority']}",
            f"Source: {context['source_module']}",
            "",
        ]
        
        if context["description"]:
            parts.append(f"Description:\n{context['description']}")
            parts.append("")
        
        if context.get("metadata", {}).get("suggested_improvement"):
            parts.append(f"Suggested Improvement:\n{context['metadata']['suggested_improvement']}")
            parts.append("")
        
        if context["linked_source"]:
            parts.append(f"Related Source: {context['linked_source']}")
            if context["linked_source_metadata"]:
                parts.append(f"Source Details: {context['linked_source_metadata'][:200]}")
            parts.append("")
        
        parts.extend([
            "Based on the task details above, generate:",
            "1. implementation_summary: 2-3 sentence summary of what was completed",
            "2. review_notes: 2-3 bullet points highlighting key achievements or items for review",
            "3. execution_notes: 2-3 bullet points with technical details or supporting evidence",
            "",
            "Format your response as JSON with these three fields.",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_claude_response(response_text: str) -> dict[str, str]:
        """
        Parse Claude's response and extract completion details.
        
        Attempts to extract JSON from response with fallback to text parsing.
        """
        try:
            # Try to extract JSON from response (Claude may wrap it in markdown)
            response_text = response_text.strip()
            
            # Remove markdown json wrapper if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["implementation_summary", "review_notes", "execution_notes"]
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValueError(f"Missing or empty field: {field}")
            
            return {
                "implementation_summary": str(data["implementation_summary"]),
                "review_notes": str(data["review_notes"]),
                "execution_notes": str(data["execution_notes"]),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse Claude response: {e}. Response: {response_text[:200]}")
            raise LLMAnalysisError(f"Failed to parse Claude response: {e}") from e
    
    @staticmethod
    def _get_placeholder_template() -> dict[str, str]:
        """Return placeholder template when LLM is unavailable."""
        return {
            "implementation_summary": "[Awaiting human completion - LLM auto-complete not available]",
            "review_notes": "[Manual review required]",
            "execution_notes": "[No automatic execution details generated]",
        }
