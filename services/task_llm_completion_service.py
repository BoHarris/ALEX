"""
Orchestrates LLM-generated task completion workflow.
Generates and submits completion details for automation tasks.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from database.models.governance_task import GovernanceTask
from services.llm_completion_service import LLMCompletionAnalyzer, LLMAnalysisError
from services.governance_task_service import get_task_detail, update_task, add_task_activity
from services.automated_changes_service import mark_task_ready_for_review

logger = logging.getLogger(__name__)


class TaskLLMCompletionError(Exception):
    """Raised when LLM completion workflow fails."""
    pass


class TaskLLMCompletionOrchestrator:
    """Orchestrates LLM-powered task completion workflow."""
    
    def __init__(self):
        self.analyzer = LLMCompletionAnalyzer()
    
    def generate_and_submit_completion(
        self,
        db: Session,
        *,
        company_id: int,
        task_id: int,
        actor_user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Generate completion details using LLM and submit task to ready_for_review.
        
        This is the main orchestration function. It:
        1. Fetches the task
        2. Analyzes it with Claude
        3. Builds completion metadata
        4. Marks task as ready_for_review
        5. Logs activity
        
        Args:
            db: SQLAlchemy session
            company_id: Company ID for scoping
            task_id: Task ID to complete
            actor_user_id: User ID triggering the action
            
        Returns:
            Serialized task with LLM-generated details
            
        Raises:
            TaskLLMCompletionError: If workflow fails
        """
        try:
            # Step 1: Fetch task
            task = self._fetch_task(db, company_id, task_id)
            
            # Step 2: Check if already generated (idempotency)
            task_metadata = self._parse_metadata(task)
            if task_metadata.get("llm_completion_attempted"):
                logger.info(f"Task {task_id} already has LLM completion attempted. Skipping.")
                return get_task_detail(db, company_id=company_id, task_id=task_id)
            
            # Step 3: Generate details with Claude
            logger.info(f"Analyzing task {task_id} with Claude...")
            completion_details = self.analyzer.analyze_task(task)
            
            # Step 4: Submit to ready_for_review with LLM details
            logger.info(f"Submitting task {task_id} to ready_for_review with LLM details...")
            marked_task = mark_task_ready_for_review(
                db,
                company_id=company_id,
                task_id=task_id,
                actor_user_id=actor_user_id,
                branch_name=None,
                commit_message=None,
                implementation_summary=completion_details.get("implementation_summary"),
                review_notes=completion_details.get("review_notes"),
                execution_notes=completion_details.get("execution_notes"),
            )
            
            # Step 6: Update task metadata with LLM completion flags for audit trail
            logger.info(f"Recording LLM metadata for task {task_id}...")
            task_metadata["llm_completion_attempted"] = True
            task_metadata["llm_completion_timestamp"] = datetime.now(timezone.utc).isoformat()
            task_metadata["llm_model"] = self.analyzer.config.model
            task_metadata["llm_completion_source"] = "claude_auto"
            
            update_task(
                db,
                company_id=company_id,
                task_id=task_id,
                actor_employee_id=None,
                actor_user_id=None,
                metadata=task_metadata,
            )
            
            # Step 7: Log activity
            if marked_task:
                add_task_activity(
                    db,
                    task_id=task_id,
                    company_id=company_id,
                    actor_employee_id=None,
                    actor_type="system",
                    actor_label="LLM Automation",
                    action="llm_completion_generated",
                    details=f"Claude ({self.analyzer.config.model}) generated completion details and submitted to ready_for_review.",
                )
                logger.info(f"LLM completion workflow succeeded for task {task_id}")
            
            return marked_task or {}
            
        except LLMAnalysisError as e:
            logger.error(f"LLM analysis failed for task {task_id}: {e}")
            # Mark that attempt was made but failed
            self._record_llm_failure(db, task_id, company_id, str(e))
            raise TaskLLMCompletionError(f"LLM analysis failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in LLM completion workflow for task {task_id}: {e}")
            raise TaskLLMCompletionError(f"Workflow failed: {e}") from e
    
    @staticmethod
    def _fetch_task(db: Session, company_id: int, task_id: int) -> GovernanceTask:
        """Fetch task with company scoping."""
        task = (
            db.query(GovernanceTask)
            .filter(GovernanceTask.id == task_id, GovernanceTask.company_id == company_id)
            .first()
        )
        if not task:
            raise TaskLLMCompletionError(f"Task {task_id} not found")
        return task
    
    @staticmethod
    def _parse_metadata(task: GovernanceTask) -> dict[str, Any]:
        """Parse metadata_json from task."""
        if not task.metadata_json:
            return {}
        try:
            return json.loads(task.metadata_json)
        except json.JSONDecodeError:
            logger.warning(f"Task {task.id} has invalid metadata_json")
            return {}
    
    @staticmethod
    def _record_llm_failure(
        db: Session, task_id: int, company_id: int, error_message: str
    ) -> None:
        """Record LLM failure in task metadata for audit trail."""
        try:
            task = (
                db.query(GovernanceTask)
                .filter(GovernanceTask.id == task_id, GovernanceTask.company_id == company_id)
                .first()
            )
            if not task:
                return
            
            metadata = TaskLLMCompletionOrchestrator._parse_metadata(task)
            metadata["llm_completion_attempted"] = True
            metadata["llm_completion_failed"] = True
            metadata["llm_completion_error"] = error_message[:500]
            metadata["llm_completion_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Update task with failure metadata
            update_task(
                db,
                company_id=company_id,
                task_id=task_id,
                actor_employee_id=None,
                actor_user_id=None,
                metadata=metadata,
            )
            
            # Log failure activity
            add_task_activity(
                db,
                task_id=task_id,
                company_id=company_id,
                actor_employee_id=None,
                actor_type="system",
                actor_label="LLM Automation",
                action="llm_completion_failed",
                details=f"LLM completion failed: {error_message[:200]}",
            )
            
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to record LLM failure for task {task_id}: {e}")


# Create global orchestrator instance
_orchestrator: Optional[TaskLLMCompletionOrchestrator] = None


def get_llm_completion_orchestrator() -> TaskLLMCompletionOrchestrator:
    """Get or initialize the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskLLMCompletionOrchestrator()
    return _orchestrator


def generate_and_submit_llm_completion(
    db: Session,
    *,
    company_id: int,
    task_id: int,
    actor_user_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Convenience function to generate and submit LLM completion.
    
    Use this function from other services instead of directly instantiating the orchestrator.
    """
    orchestrator = get_llm_completion_orchestrator()
    return orchestrator.generate_and_submit_completion(
        db,
        company_id=company_id,
        task_id=task_id,
        actor_user_id=actor_user_id,
    )
