"""
LLM Management Admin Endpoints
Provides manual control over LLM task completion features.
- Trigger manual LLM completion for a specific task
- View/update LLM configuration
- Check LLM system status
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import logging
import os

from database.database import get_db
from database.models.governance_task import GovernanceTask
from database.models.governance_task_activity import GovernanceTaskActivity
from database.models.llm_settings import LLMSettings
from services.llm_config import get_llm_config
from services.task_llm_completion_service import generate_and_submit_llm_completion
from services.security_service import enforce_auth_rate_limit
from services.llm_metrics_service import get_llm_metrics, get_llm_metrics_from_db, get_llm_metrics_prometheus
from dependencies.tier_guard import require_security_admin

# Allowed Claude models for validation
ALLOWED_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-5-haiku-latest"
]

logger = logging.getLogger(__name__)

# Rate limiting constants for LLM admin endpoints
LLM_RATE_WINDOW_SECONDS = int(os.getenv("LLM_RATE_WINDOW_SECONDS", "60"))
LLM_RATE_LIMIT_PER_IP = int(os.getenv("LLM_RATE_LIMIT_PER_IP", "10"))
LLM_RATE_LIMIT_PER_USER = int(os.getenv("LLM_RATE_LIMIT_PER_USER", "5"))


def _enforce_llm_rate_limit(
    *,
    db: Session,
    request: Request,
    user_id: int,
) -> None:
    enforce_auth_rate_limit(
        db,
        request=request,
        identifier=str(user_id),
        per_ip_limit=LLM_RATE_LIMIT_PER_IP,
        per_identifier_limit=LLM_RATE_LIMIT_PER_USER,
        window_seconds=LLM_RATE_WINDOW_SECONDS,
    )

router = APIRouter(prefix="/api/llm", tags=["llm_admin"])


@router.post("/generate-completion/{task_id}")
async def manually_trigger_llm_completion(
    task_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_security_admin),
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
    # Verify user is admin for the specific company
    if current_user["company_id"] != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized for this company"
        )
    
    # Enforce rate limiting
    _enforce_llm_rate_limit(db=db, request=request, user_id=current_user["id"])
    
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
            actor_user_id=current_user["id"]
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_security_admin),
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
    # Verify user is admin for the specific company
    if current_user["company_id"] != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized for this company"
        )
    
    # Enforce rate limiting
    _enforce_llm_rate_limit(db=db, request=request, user_id=current_user["id"])
    
    config = get_llm_config()
    
    # Count tasks with LLM generation in this company
    tasks_with_llm = db.query(GovernanceTask).filter(
        GovernanceTask.company_id == company_id,
        GovernanceTask.metadata.isouter().contains(lambda x: x.get("llm_completion_attempted") is True)
    ).count()
    
    # Calculate average generation time from activity logs
    avg_time_query = db.query(
        func.avg(
            func.extract('epoch', GovernanceTaskActivity.created_at - GovernanceTask.created_at)
        )
    ).join(
        GovernanceTask, GovernanceTaskActivity.task_id == GovernanceTask.id
    ).filter(
        GovernanceTaskActivity.action == "llm_completion_generated",
        GovernanceTaskActivity.company_id == company_id
    )
    avg_generation_time = avg_time_query.scalar()
    
    # Retrieve last error from recent failed activities
    last_error_activity = db.query(GovernanceTaskActivity).filter(
        GovernanceTaskActivity.action == "llm_completion_failed",
        GovernanceTaskActivity.company_id == company_id
    ).order_by(GovernanceTaskActivity.created_at.desc()).first()
    last_error = last_error_activity.details if last_error_activity else None
    
    return {
        "enabled": config.enabled,
        "model": config.model,
        "api_key_configured": bool(config.api_key),
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "tasks_with_llm_generation": tasks_with_llm,
        "avg_generation_time_seconds": avg_generation_time,
        "last_error": last_error
    }


@router.post("/settings")
async def update_llm_settings(
    request: Request,
    enabled: Optional[bool] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_security_admin),
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
    
    # Enforce rate limiting
    _enforce_llm_rate_limit(db=db, request=request, user_id=current_user["id"])
    
    config = get_llm_config()
    
    # Capture old values for audit logging
    old_settings = {
        "enabled": config.enabled,
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    
    changes = []
    
    if enabled is not None:
        if config.enabled != enabled:
            changes.append(f"enabled: {config.enabled} -> {enabled}")
        config.enabled = enabled
    
    if model is not None:
        if model not in ALLOWED_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{model}'. Allowed models: {', '.join(ALLOWED_MODELS)}"
            )
        if config.model != model:
            changes.append(f"model: {config.model} -> {model}")
        config.model = model
    
    if max_tokens is not None:
        if not (1 <= max_tokens <= 4096):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_tokens must be between 1 and 4096"
            )
        if config.max_tokens != max_tokens:
            changes.append(f"max_tokens: {config.max_tokens} -> {max_tokens}")
        config.max_tokens = max_tokens
    
    if temperature is not None:
        if not (0.0 <= temperature <= 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temperature must be between 0.0 and 1.0"
            )
        if config.temperature != temperature:
            changes.append(f"temperature: {config.temperature} -> {temperature}")
        config.temperature = temperature
    
    # Log audit trail for configuration changes
    if changes:
        logger.warning(
            f"LLM settings updated by user {current_user['id']} ({current_user.get('email', 'unknown')}): {', '.join(changes)}"
        )
    else:
        logger.info(
            f"LLM settings update attempted by user {current_user['id']} ({current_user.get('email', 'unknown')}) but no changes made"
        )
    
    # Persist settings to database
    settings = db.query(LLMSettings).first()
    if not settings:
        settings = LLMSettings()
        db.add(settings)
    settings.enabled = config.enabled
    settings.model = config.model
    settings.max_tokens = config.max_tokens
    settings.temperature = config.temperature
    db.commit()
    
    return {
        "status": "success",
        "message": "LLM settings updated and persisted to database",
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_security_admin),
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
    # Verify user is admin for the specific company
    if current_user["company_id"] != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized for this company"
        )
    
    # Enforce rate limiting
    _enforce_llm_rate_limit(db=db, request=request, user_id=current_user["id"])
    
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
    
    # Retrieve full generation history from activity logs
    activities = db.query(GovernanceTaskActivity).filter(
        GovernanceTaskActivity.task_id == task_id,
        GovernanceTaskActivity.action.in_(["llm_completion_generated", "llm_completion_failed"])
    ).order_by(GovernanceTaskActivity.created_at).all()
    
    generations = []
    for activity in activities:
        if activity.action == "llm_completion_generated":
            status = "success"
            error = None
            # Parse model from details if possible, else use current
            model = metadata.get("llm_model", "unknown")
            if "Claude (" in activity.details:
                try:
                    model = activity.details.split("Claude (")[1].split(")")[0]
                except IndexError:
                    pass
            generated_fields = [
                "implementation_summary" if metadata.get("implementation_summary") else None,
                "review_notes" if metadata.get("review_notes") else None,
                "execution_notes" if metadata.get("execution_notes") else None,
            ]
        else:  # llm_completion_failed
            status = "failed"
            error = activity.details.replace("LLM completion failed: ", "") if activity.details else None
            model = None
            generated_fields = []
        
        generations.append({
            "timestamp": activity.created_at.isoformat(),
            "model": model,
            "status": status,
            "generated_fields": generated_fields,
            "error": error
        })
    
    # Determine overall status
    has_attempts = len(activities) > 0
    has_success = any(activity.action == "llm_completion_generated" for activity in activities)
    
    return {
        "task_id": task_id,
        "llm_attempted": has_attempts,
        "llm_successful": has_success,
        "generations": generations
    }


@router.get("/metrics")
async def get_llm_metrics_runtime(
    current_user: dict = Depends(require_security_admin),
) -> dict:
    """
    Get real-time LLM performance metrics collected during runtime.
    
    Returns metrics from in-memory store including:
    - API call counts and success rates
    - Token usage statistics
    - Latency percentiles
    - Error breakdown by type
    
    Response:
        {
            "total_calls": int,
            "total_success": int,
            "total_failures": int,
            "success_rate": float (0-100),
            "total_tokens_used": int,
            "total_input_tokens": int,
            "total_output_tokens": int,
            "average_latency_ms": float,
            "median_latency_ms": float,
            "p99_latency_ms": float,
            "errors_by_type": dict,
            "timestamp": "ISO timestamp"
        }
    """
    metrics = get_llm_metrics()
    return {
        "total_calls": metrics.total_calls,
        "total_success": metrics.total_success,
        "total_failures": metrics.total_failures,
        "success_rate": metrics.success_rate,
        "total_tokens_used": metrics.total_tokens_used,
        "total_input_tokens": metrics.total_input_tokens,
        "total_output_tokens": metrics.total_output_tokens,
        "average_latency_ms": metrics.average_latency_ms,
        "median_latency_ms": metrics.median_latency_ms,
        "p99_latency_ms": metrics.p99_latency_ms,
        "errors_by_type": metrics.errors_by_type,
        "timestamp": metrics.timestamp,
    }


@router.get("/metrics/{company_id}")
async def get_llm_metrics_by_company(
    company_id: int,
    activity_window_days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_security_admin),
) -> dict:
    """
    Get aggregated LLM metrics from database activity logs for a company.
    
    Queries activity logs to calculate historical metrics over a time window.
    
    Args:
        company_id: Company ID to get metrics for
        activity_window_days: Number of days to include (1-365, default 30)
    
    Response:
        {
            "llm_completions_attempted": int,
            "llm_completions_successful": int,
            "llm_completions_failed": int,
            "llm_success_rate": float (0-100),
            "unique_tasks_completed": int,
            "average_completions_per_day": float,
            "time_window_days": int,
            "timestamp": "ISO timestamp"
        }
    """
    # Verify user is admin for the specific company
    if current_user["company_id"] != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized for this company"
        )
    
    # Validate activity window
    if not (1 <= activity_window_days <= 365):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="activity_window_days must be between 1 and 365"
        )
    
    metrics = get_llm_metrics_from_db(
        db,
        company_id=company_id,
        activity_window_days=activity_window_days,
    )
    return metrics


@router.get("/metrics-prometheus", response_class=None)
async def get_llm_metrics_prometheus_endpoint(
    current_user: dict = Depends(require_security_admin),
):
    """
    Get LLM metrics in Prometheus text format.
    
    Returns metrics in application/openmetrics-text format compatible with:
    - Prometheus servers
    - Grafana dashboards
    - Other monitoring systems
    
    Metrics include:
    - llm_api_calls_total: Counter of API calls by status (success/failure)
    - llm_tokens_used_total: Counter of tokens used by type (input/output/total)
    - llm_api_latency_ms: Histogram of API response latencies
    - llm_api_errors_total: Counter of errors by type
    
    Example Prometheus scrape config:
        - job_name: 'alex_llm'
          static_configs:
            - targets: ['localhost:8000']
          metrics_path: '/api/llm/metrics-prometheus'
    """
    from starlette.responses import Response
    
    metrics_bytes = get_llm_metrics_prometheus()
    return Response(
        content=metrics_bytes,
        media_type="application/openmetrics-text; version=1.0.0; charset=utf-8"
    )
