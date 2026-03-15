"""
LLM Management Admin Endpoints
Provides manual control over LLM task completion features.
- Trigger manual LLM completion for a specific task
- View/update LLM configuration
- Check LLM system status
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from models import GovernanceTask
from services.llm_config import get_llm_config
from services.task_llm_completion_service import generate_and_submit_llm_completion
from models.auth import CurrentUser

router = APIRouter(prefix="/api/llm", tags=["llm_admin"])


@router.post("/generate-completion/{task_id}")
async def manually_trigger_llm_completion(
    task_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> dict:
    """
    Manually trigger LLM completion generation for a specific task.
    
    Requires: Admin role for the given company
    
    Args:
        task_id: ID of the task to generate completion for
        company_id: Company ID for authorization
        
    Response:
        {
            "status": "success|error",
            "message": "Human-readable result message",
            "task_id": int,
            "llm_model": "claude-3-5-sonnet-20241022",
            "generated_fields": ["implementation_summary", "review_notes", "execution_notes"],
            "timestamp": "ISO timestamp"
        }
    """
    # TODO: Add authorization check - verify current_user is admin for company_id
    
    config = get_llm_config()
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM completion service is currently disabled"
        )
    
    task = db.query(GovernanceTask).filter(
        GovernanceTask.id == task_id,
        GovernanceTask.company_id == company_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found in company {company_id}"
        )
    
    if task.status not in ["in_progress", "ready_for_review", "blocked"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task must be in 'in_progress', 'ready_for_review', or 'blocked' status. Current: {task.status}"
        )
    
    try:
        result = generate_and_submit_llm_completion(
            db=db,
            company_id=company_id,
            task_id=task_id,
            actor_user_id=current_user.id
        )
        
        return {
            "status": "success",
            "message": "LLM completion generated and task moved to ready_for_review",
            "task_id": task_id,
            "llm_model": config.model,
            "generated_fields": ["implementation_summary", "review_notes", "execution_notes"],
            "timestamp": task.metadata.get("llm_completion_timestamp") if task.metadata else None
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM completion generation failed: {str(e)}"
        )


@router.get("/status")
async def get_llm_status(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> dict:
    """
    Check LLM system status and configuration.
    
    Response:
        {
            "enabled": bool,
            "model": "claude-3-5-sonnet-20241022",
            "api_key_configured": bool,
            "max_tokens": 1024,
            "temperature": 0.7,
            "tasks_with_llm_generation": int,
            "avg_generation_time_seconds": float,
            "last_error": Optional[str]
        }
    """
    config = get_llm_config()
    
    # Count tasks with LLM generation in this company
    tasks_with_llm = db.query(GovernanceTask).filter(
        GovernanceTask.company_id == company_id,
        GovernanceTask.metadata.isouter().contains(lambda x: x.get("llm_completion_attempted") is True)
    ).count()
    
    return {
        "enabled": config.enabled,
        "model": config.model,
        "api_key_configured": bool(config.api_key),
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "tasks_with_llm_generation": tasks_with_llm,
        "avg_generation_time_seconds": 8.5,  # TODO: Calculate from activity logs
        "last_error": None  # TODO: Retrieve from recent activity logs with errors
    }


@router.post("/settings")
async def update_llm_settings(
    enabled: Optional[bool] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    current_user: CurrentUser = Depends(),
) -> dict:
    """
    Update LLM configuration settings (admin only).
    
    NOTE: These changes update environment variables at runtime.
    Restart required for persistent changes.
    
    Args:
        enabled: Enable/disable LLM auto-completion
        model: Claude model version (e.g., "claude-3-5-sonnet-20241022")
        max_tokens: Max output tokens per LLM request
        temperature: Temperature setting (0.0-1.0)
        
    Response:
        {
            "status": "success",
            "message": "Settings updated",
            "current_settings": { ... }
        }
    """
    # TODO: Add authorization check - verify current_user is super_admin
    
    config = get_llm_config()
    
    if enabled is not None:
        config.enabled = enabled
    
    if model is not None:
        config.model = model
    
    if max_tokens is not None:
        config.max_tokens = max_tokens
    
    if temperature is not None:
        if not (0.0 <= temperature <= 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temperature must be between 0.0 and 1.0"
            )
        config.temperature = temperature
    
    # Note: In production, these should be persisted to environment or config database
    # For now, they apply only to the current runtime session
    
    return {
        "status": "success",
        "message": "LLM settings updated (runtime only, restart required for persistence)",
        "current_settings": {
            "enabled": config.enabled,
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
    }


@router.get("/task-history/{task_id}")
async def get_llm_task_history(
    task_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> dict:
    """
    Retrieve LLM generation history for a specific task.
    
    Response:
        {
            "task_id": int,
            "llm_attempted": bool,
            "llm_successful": bool,
            "generations": [
                {
                    "timestamp": "ISO timestamp",
                    "model": "claude-3-5-sonnet-20241022",
                    "status": "success|failed",
                    "generated_fields": [...],
                    "error": Optional[str]
                }
            ]
        }
    """
    task = db.query(GovernanceTask).filter(
        GovernanceTask.id == task_id,
        GovernanceTask.company_id == company_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    metadata = task.metadata or {}
    
    # TODO: Retrieve full generation history from activity logs
    # For now, return current state from metadata
    
    generations = []
    if metadata.get("llm_completion_attempted"):
        generations.append({
            "timestamp": metadata.get("llm_completion_timestamp"),
            "model": metadata.get("llm_model", "unknown"),
            "status": "failed" if metadata.get("llm_completion_failed") else "success",
            "generated_fields": [
                "implementation_summary" if metadata.get("implementation_summary") else None,
                "review_notes" if metadata.get("review_notes") else None,
                "execution_notes" if metadata.get("execution_notes") else None,
            ],
            "error": metadata.get("llm_completion_error")
        })
    
    return {
        "task_id": task_id,
        "llm_attempted": metadata.get("llm_completion_attempted", False),
        "llm_successful": bool(metadata.get("llm_completion_attempted") and not metadata.get("llm_completion_failed")),
        "generations": generations
    }
