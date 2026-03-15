"""
LLM Performance Metrics Service
Collects metrics for LLM API usage, performance, and activity.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models.governance_task_activity import GovernanceTaskActivity

logger = logging.getLogger(__name__)

# Try to import prometheus_client, but don't fail if not available
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
    # Create a separate registry for LLM metrics
    _llm_registry = CollectorRegistry()
    
    # Define Prometheus metrics
    _llm_api_calls = Counter(
        'llm_api_calls_total',
        'Total number of LLM API calls',
        ['status'],  # labels: success, failure
        registry=_llm_registry
    )
    _llm_tokens_used = Counter(
        'llm_tokens_used_total',
        'Total tokens used in LLM API calls',
        ['token_type'],  # labels: input, output, total
        registry=_llm_registry
    )
    _llm_api_latency = Histogram(
        'llm_api_latency_ms',
        'LLM API response latency in milliseconds',
        buckets=(10, 50, 100, 200, 500, 1000, 2000, 5000),
        registry=_llm_registry
    )
    _llm_errors = Counter(
        'llm_api_errors_total',
        'Total number of LLM API errors by type',
        ['error_type'],
        registry=_llm_registry
    )
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Prometheus metrics will not be available.")

# In-memory metrics store (reset on app restart)
_llm_metrics_store = {
    "total_calls": 0,
    "total_failures": 0,
    "total_success": 0,
    "total_tokens_used": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_latency_ms": 0,
    "call_times": [],  # List of individual call latencies for percentile calculation
    "errors_by_type": {},  # Dict of error types and counts
}


@dataclass
class LLMMetricsSnapshot:
    """Snapshot of current LLM metrics."""
    total_calls: int
    total_success: int
    total_failures: int
    success_rate: float
    total_tokens_used: int
    total_input_tokens: int
    total_output_tokens: int
    average_latency_ms: float
    median_latency_ms: float
    p99_latency_ms: float
    errors_by_type: dict[str, int]
    timestamp: str


def record_llm_call(
    success: bool,
    latency_ms: float,
    tokens_used: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    error_type: Optional[str] = None,
) -> None:
    """
    Record metrics from an LLM API call.
    
    Args:
        success: Whether the call succeeded
        latency_ms: Response time in milliseconds
        tokens_used: Total tokens used (for backward compatibility)
        input_tokens: Input tokens used (if available)
        output_tokens: Output tokens used (if available)
        error_type: Type of error if failed
    """
    _llm_metrics_store["total_calls"] += 1
    
    if success:
        _llm_metrics_store["total_success"] += 1
    else:
        _llm_metrics_store["total_failures"] += 1
        if error_type:
            _llm_metrics_store["errors_by_type"][error_type] = (
                _llm_metrics_store["errors_by_type"].get(error_type, 0) + 1
            )
    
    _llm_metrics_store["total_latency_ms"] += latency_ms
    _llm_metrics_store["call_times"].append(latency_ms)
    
    # Track tokens
    if tokens_used > 0:
        _llm_metrics_store["total_tokens_used"] += tokens_used
    if input_tokens > 0:
        _llm_metrics_store["total_input_tokens"] += input_tokens
    if output_tokens > 0:
        _llm_metrics_store["total_output_tokens"] += output_tokens
    
    # Record Prometheus metrics if available
    if PROMETHEUS_AVAILABLE:
        status_label = "success" if success else "failure"
        _llm_api_calls.labels(status=status_label).inc()
        _llm_api_latency.observe(latency_ms)
        
        if input_tokens > 0:
            _llm_tokens_used.labels(token_type="input").inc(input_tokens)
        if output_tokens > 0:
            _llm_tokens_used.labels(token_type="output").inc(output_tokens)
        if tokens_used > 0:
            _llm_tokens_used.labels(token_type="total").inc(tokens_used)
        
        if error_type:
            _llm_errors.labels(error_type=error_type).inc()
    
    logger.debug(
        f"LLM metrics recorded: success={success}, latency={latency_ms}ms, "
        f"tokens={tokens_used}, input={input_tokens}, output={output_tokens}"
    )


def get_llm_metrics() -> LLMMetricsSnapshot:
    """
    Get current LLM metrics snapshot.
    
    Returns:
        LLMMetricsSnapshot with aggregated metrics
    """
    total_calls = _llm_metrics_store["total_calls"]
    call_times = _llm_metrics_store["call_times"]
    
    # Calculate success rate
    success_rate = (
        (_llm_metrics_store["total_success"] / total_calls * 100)
        if total_calls > 0
        else 0.0
    )
    
    # Calculate latency percentiles
    avg_latency = (
        _llm_metrics_store["total_latency_ms"] / total_calls
        if total_calls > 0
        else 0.0
    )
    
    if call_times:
        sorted_times = sorted(call_times)
        median_latency = sorted_times[len(sorted_times) // 2]
        p99_idx = max(0, int(len(sorted_times) * 0.99) - 1)
        p99_latency = sorted_times[p99_idx]
    else:
        median_latency = 0.0
        p99_latency = 0.0
    
    return LLMMetricsSnapshot(
        total_calls=total_calls,
        total_success=_llm_metrics_store["total_success"],
        total_failures=_llm_metrics_store["total_failures"],
        success_rate=round(success_rate, 2),
        total_tokens_used=_llm_metrics_store["total_tokens_used"],
        total_input_tokens=_llm_metrics_store["total_input_tokens"],
        total_output_tokens=_llm_metrics_store["total_output_tokens"],
        average_latency_ms=round(avg_latency, 2),
        median_latency_ms=round(median_latency, 2),
        p99_latency_ms=round(p99_latency, 2),
        errors_by_type=_llm_metrics_store["errors_by_type"].copy(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def get_llm_metrics_from_db(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
) -> dict[str, object]:
    """
    Get LLM metrics from database activity logs for a company.
    
    Queries governance_task_activity logs for LLM-related activities
    and calculates aggregated metrics over the specified time window.
    
    Args:
        db: Database session
        company_id: Company ID to filter by
        activity_window_days: Number of days to look back (default 30)
    
    Returns:
        Dictionary with:
        - llm_completions_attempted: Count of LLM completion attempts
        - llm_completions_successful: Count of successful completions
        - llm_completions_failed: Count of failed completions
        - llm_success_rate: Success rate percentage
        - unique_tasks_completed: Number of unique tasks processed
        - average_completions_per_day: Average completions per day in window
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=activity_window_days)
    
    # Get LLM-related activities
    llm_activities = db.query(GovernanceTaskActivity).filter(
        GovernanceTaskActivity.company_id == company_id,
        GovernanceTaskActivity.created_at >= cutoff_date,
        GovernanceTaskActivity.action.in_([
            "llm_completion_generated",
            "llm_completion_failed",
            "llm_completion_attempted",
        ]),
    )
    
    total_attempted = llm_activities.filter(
        GovernanceTaskActivity.action == "llm_completion_attempted"
    ).count()
    
    total_successful = llm_activities.filter(
        GovernanceTaskActivity.action == "llm_completion_generated"
    ).count()
    
    total_failed = llm_activities.filter(
        GovernanceTaskActivity.action == "llm_completion_failed"
    ).count()
    
    unique_tasks = db.query(
        func.count(func.distinct(GovernanceTaskActivity.task_id))
    ).filter(
        GovernanceTaskActivity.company_id == company_id,
        GovernanceTaskActivity.created_at >= cutoff_date,
        GovernanceTaskActivity.action.in_([
            "llm_completion_generated",
            "llm_completion_failed",
        ]),
    ).scalar() or 0
    
    success_rate = (
        (total_successful / total_attempted * 100)
        if total_attempted > 0
        else 0.0
    )
    
    avg_per_day = total_attempted / max(activity_window_days, 1)
    
    return {
        "llm_completions_attempted": total_attempted,
        "llm_completions_successful": total_successful,
        "llm_completions_failed": total_failed,
        "llm_success_rate": round(success_rate, 2),
        "unique_tasks_completed": unique_tasks,
        "average_completions_per_day": round(avg_per_day, 2),
        "time_window_days": activity_window_days,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_llm_metrics_prometheus() -> bytes:
    """
    Get LLM metrics in Prometheus text format.
    
    Returns:
        Prometheus-format metrics as bytes
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("prometheus_client not available. Returning empty metrics.")
        return b""
    
    return generate_latest(_llm_registry)
