#!/usr/bin/env python3
"""Create comprehensive improvement tasks from code review findings."""

from database.database import SessionLocal
from database.models.governance_task import GovernanceTask
from datetime import datetime, timezone, timedelta

def main():
    db = SessionLocal()
    
    # Critical security & architecture tasks
    critical_tasks = [
        {
            'title': '[CRITICAL SECURITY] Fix Authorization on LLM Admin Endpoints',
            'priority': 'critical',
            'description': '''## Priority: CRITICAL
## Category: Security & Access Control

### Issue:
All LLM admin endpoints in routers/llm_admin.py lack company scoping and role verification.
- manually_trigger_llm_completion(): Any user can trigger for any company
- update_llm_settings(): Any authenticated user can modify global settings
- get_llm_status/task_history(): No company verification

### Security Impact:
- Users can run LLM automation on competitors' data
- Settings changes affect all companies
- Potential for lateral privilege escalation

### Required Fixes:
1. Add company_id parameter validation to all endpoints
2. Verify current_user.company_id matches target company
3. Require specific roles (admin/super_admin) for settings modification
4. Add audit logging for all config changes
5. Implement proper authorization middleware

### Files to Fix:
- routers/llm_admin.py (lines 52, 166, 203 - TODO markers)
- tests/test_llm_api_authorization.py (create new, 8+ test cases)

### Acceptance Criteria:
✓ Unauthorized requests return 403 Forbidden
✓ All TODO authorization markers resolved
✓ 8+ authorization test cases pass
✓ Audit logging captures all changes
✓ Company scoping enforced on all endpoints
✓ Role-based access control implemented

### Effort Estimate: 2-3 hours
### Impact: Eliminates critical security vulnerability
''',
            'source_type': 'security_audit',
            'source_module': 'security',
        },
        {
            'title': '[CRITICAL] Fix Syntax Error in AWS Config Connector',
            'priority': 'critical',
            'description': '''## Priority: CRITICAL
## Category: Bug Fix & Stability

### Issue:
connectors/aws_config.py has syntax error that prevents code from running:
- Line 32: Incorrect syntax `except(BotoCoreError, ClientError)` (missing space)
- Should be: `except (BotoCoreError, ClientError)`

### Impact:
- AWS connector fails on any API error
- Exception handling doesn't work
- Production outages if AWS API called

### Additional Issues in this function:
1. No logging before exception re-raise
2. Missing timeout configuration for AWS calls
3. Incomplete error context (should include operation details)
4. No retry logic for transient failures
5. Generic RuntimeError loses stack trace (should use `raise ... from e`)

### Required Fixes:
1. Fix syntax error (add space before parenthesis)
2. Add logging.error() with full context
3. Preserve exception chain with `raise ... from e`
4. Add timeout to AWS client operations
5. Implement exponential backoff for retries (3 attempts)
6. Improve error messages with operation/resource context

### Files to Modify:
- connectors/aws_config.py (line 22-40)
- tests/test_aws_connector.py (add 5+ error scenario tests)

### Acceptance Criteria:
✓ Syntax error fixed
✓ Code passes linting
✓ All exception handling tests pass
✓ Proper exception chaining maintained
✓ Logging includes operation context
✓ 5+ error scenario tests added

### Effort Estimate: 1-2 hours
### Impact: Fixes production-blocking bug in AWS connector
''',
            'source_type': 'bug_report',
            'source_module': 'connectors',
        },
        {
            'title': '[CRITICAL] Fix Race Condition in Scan Quota Check',
            'priority': 'critical',
            'description': '''## Priority: CRITICAL
## Category: Concurrency & Data Integrity

### Issue:
utils/tier_limiter.py reserve_scan_quota() has race condition:
- Checks quota, then increments (not atomic)
- Between check and increment, another thread could increment
- Allows users to exceed quota limits

### Vulnerable Code Location:
utils/tier_limiter.py lines 46-58

### Attack Scenario:
1. User A checks quota: count=99, limit=100 ✓ allowed
2. User B checks quota: count=99, limit=100 ✓ allowed (before A increments)
3. User A increments: count=100
4. User B increments: count=101 (EXCEEDS LIMIT!)

### Correct Solution:
Use database-level atomic operation with RETURNING clause:
```python
result = db.execute(
    update(ScanQuotaCounter)
    .where(ScanQuotaCounter.id == record.id)
    .where(ScanQuotaCounter.count < daily_limit)
    .values(count=ScanQuotaCounter.count + 1)
    .returning(ScanQuotaCounter.count)
)
```

### Required Fixes:
1. Move logic to atomic database operation
2. Use WHERE clause to enforce limit atomically
3. Add integration tests with concurrent requests
4. Verify quota is truly enforced under load

### Files to Modify:
- utils/tier_limiter.py (refactor _reserve_scan_quota)
- tests/test_tier_limiter.py (add concurrency tests)

### Acceptance Criteria:
✓ Atomic database operation implemented
✓ WHERE clause enforces limit in database
✓ Concurrency tests pass (50+ simultaneous requests)
✓ Quota never exceeded under load
✓ Performance acceptable (< 5ms per check)
✓ No more implicit race condition

### Effort Estimate: 1-2 hours
### Impact: Prevents quota abuse and billing fraud
''',
            'source_type': 'bug_report',
            'source_module': 'billing',
        },
        {
            'title': '[CRITICAL] Replace Broad Exception Handling',
            'priority': 'critical',
            'description': '''## Priority: CRITICAL
## Category: Code Quality & Debugging

### Issue:
Multiple services catch `Exception` (too broad) which masks real bugs:

Locations:
- services/llm_completion_service.py line 76: catches Exception
- services/audit_service.py: broad exception handling
- routers/scans.py: catches all exceptions without differentiation
- services/scan_service.py: generic error handling

### Problem:
- Typos and logic errors get caught and hidden
- Makes debugging extremely difficult
- Production errors become generic "something failed" messages
- Violates principle of catching specific exceptions

### Proper Pattern:
```python
# BAD - too broad
except Exception:
    logger.error("Operation failed")

# GOOD - specific exceptions
except (APIError, APIConnectionError) as e:
    logger.error(f"API error: {e}")
    handle_api_retry()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise HTTPException(400, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error: {e}")  # Still logged, but tracked
    raise
```

### Required Fixes:
1. Replace all `except Exception:` with specific exception types
2. Add proper logging with exception context
3. Let unexpected exceptions propagate (with logging)
4. Add error classification for recovery strategies
5. Add tests for each exception type

### Files to Modify:
- services/llm_completion_service.py (line 76+)
- services/scan_service.py (multiple locations)
- services/audit_service.py (broad catches)
- routers/scans.py (error handlers)

### Acceptance Criteria:
✓ No naked `except Exception:` in code
✓ All exceptions caught are specific types
✓ Unexpected errors logged with full traceback
✓ Error classification added for retry logic
✓ 10+ test cases for different exception scenarios
✓ Debugging improved (real errors no longer hidden)

### Effort Estimate: 2-3 hours
### Impact: Dramatically improves debugging and reliability
''',
            'source_type': 'code_quality',
            'source_module': 'core_services',
        },
    ]
    
    # High priority fixes
    high_priority_tasks = [
        {
            'title': 'Complete Missing LLM Test Coverage',
            'priority': 'high',
            'description': '''## Priority: HIGH
## Category: Testing & Quality Assurance

### Current Status:
- test_llm_completion.py: 14 unit tests ✓
- test_llm_integration_workflow.py: 6 integration tests ✓
- **MISSING**: End-to-end workflow tests
- **MISSING**: Error scenario tests
- **MISSING**: Concurrency tests

### Required Test Scenarios:

**E2E Workflow (Happy Path)**:
- Create task → Trigger LLM → Task moves to ready_for_review
- Verify LLM metadata populated (summary, notes, execution notes)
- Verify activity log entry created
- Verify all database writes completed

**Error Recovery**:
- LLM API returns 429 (rate limit) → Retry logic triggered
- LLM API returns 401 (auth failure) → No retry, graceful fail
- LLM API timeout → Retry with increased timeout
- Network error → Exponential backoff
- Verify all errors logged with context

**Concurrency**:
- 5 simultaneous LLM tasks triggered
- Verify no database conflicts
- Verify all complete successfully
- Verify no duplicate processing

**Edge Cases**:
- Task with 50KB description
- Task with special characters/unicode
- Task with null/empty fields
- Task already in processing state

### Files to Create/Modify:
- tests/test_llm_e2e_workflow.py (new, 100+ lines)
- tests/test_llm_error_scenarios.py (new, 80+ lines)
- tests/test_llm_concurrency.py (new, 60+ lines)

### Acceptance Criteria:
✓ 20+ new test cases added
✓ All E2E scenarios passing
✓ Error handling validated
✓ Concurrency tests pass
✓ Coverage >85% for LLM code
✓ 100% pass rate before merge

### Effort Estimate: 3-4 hours
### Impact: Ensures LLM system reliability
''',
            'source_type': 'quality_assurance',
            'source_module': 'llm_services',
        },
        {
            'title': 'Add Input Validation to All LLM Settings Endpoints',
            'priority': 'high',
            'description': '''## Priority: HIGH
## Category: Code Quality & Security

### Issue:
LLM settings endpoints lack input validation:
- routers/llm_admin.py POST /api/llm/settings (line 139)
- No validation on max_tokens (could be negative)
- No whitelist validation for model names
- Temperature not constrained (valid range 0.0-1.0)
- No validation on config names or descriptions

### Required Validation:

**max_tokens**:
- Must be > 0
- Must be <= 4096 (API limit)
- Must be integer

**model**:
- Must be in whitelist: claude-3-5-sonnet-20241022, etc.
- Must not contain injection payloads

**temperature**:
- Must be >= 0.0
- Must be <= 1.0  
- Must be numeric

**config_name**:
- Must not be empty
- Must be alphanumeric + underscore
- Must be < 50 characters

### Implementation:
1. Create validation function in services/llm_config.py
2. Add Pydantic model for request validation
3. Return detailed 400 errors for each validation failure
4. Add request logging before/after validation
5. Document validation in API spec

### Files to Modify:
- routers/llm_admin.py (add validation function call)
- services/llm_config.py (add validation function)
- models/llm_settings.py (create Pydantic model)
- tests/test_llm_admin_endpoints.py (add validation tests)

### Acceptance Criteria:
✓ All invalid inputs rejected with 400
✓ Detailed error messages for each validation
✓ Valid inputs accepted without modification
✓ 8+ test cases covering boundary conditions
✓ No breaking changes to valid requests
✓ Validation logged for audit trail

### Effort Estimate: 2-3 hours
### Impact: Prevents invalid config and API abuse
''',
            'source_type': 'code_security',
            'source_module': 'llm_admin',
        },
        {
            'title': 'Fix N+1 Query Pattern in Governance Task Serialization',
            'priority': 'high',
            'description': '''## Priority: HIGH
## Category: Performance

### Issue:
serialize_task() in governance_task_service.py performs multiple sequential queries:
- Queries assignee employee (line X)
- Queries reporter employee (line Y)
- Queries incident details (if present)
- Each called per-task in loops = N+1 pattern

### Current Performance:
- 50 tasks = 50+ database queries
- Response time: 500-800ms

### After Fix:
- 50 tasks = 2-3 database queries
- Response time: 50-100ms
- Improvement: 10x faster

### Solution:
1. Pre-fetch all related employees via _employee_lookup()
2. Pass to serialize_task() to avoid re-querying
3. Pre-fetch all incidents in one query
4. Build lookup dictionaries before serialization loop
5. Update serialize_task() signature to accept lookup dictionaries

### Already Partially Fixed:
- _employee_lookup() function exists (line X)
- Need to use in list_tasks() and other functions

### Files to Modify:
- services/governance_task_service.py (update list_tasks, get_task_detail, etc.)
- routers/compliance_router.py (pass pre-loaded data)

### Acceptance Criteria:
✓ N+1 pattern eliminated
✓ Pre-loaded lookup dictionaries used
✓ Query count reduced by 90%
✓ No breaking changes to API
✓ Performance benchmarks show 10x improvement
✓ All tests pass

### Effort Estimate: 2-3 hours
### Impact: 10x faster governance task queries
''',
            'source_type': 'performance',
            'source_module': 'governance_tasks',
        },
    ]
    
    # Medium priority improvements
    medium_tasks = [
        {
            'title': 'Add Cost Tracking & Budget Limits to LLM Service',
            'priority': 'medium',
            'description': '''## Priority: MEDIUM
## Category: Feature Implementation & Cost Management

### Current Issue:
No mechanism to track LLM costs or enforce budget limits.
System can make unlimited Claude API calls without tracking.

### Required Implementation:

**Cost Calculation**:
- Extract token usage from Claude response (input_tokens, output_tokens)
- Calculate cost: (input_tokens × $0.003 + output_tokens × $0.015) / 1M
- Store in task metadata: llm_cost_usd, tokens_used

**Budget Enforcement**:
- Add env var: LLM_DAILY_BUDGET_USD (default: $10)
- Before calling Claude, check daily spend
- If at limit, return 429 Too Many Requests

**Metrics Display**:
- Total tokens used today
- Estimated cost today
- Budget remaining
- Success rate
- Average cost per task

### Files to Create/Modify:
- services/llm_cost_tracker.py (new, cost calculation)
- services/llm_completion_service.py (capture token usage)
- services/task_llm_completion_service.py (store costs)
- routers/llm_admin.py (metrics endpoint)

### Acceptance Criteria:
✓ Cost tracking accurate
✓ Budget enforcement prevents API calls
✓ Metrics endpoint shows all stats
✓ 5+ test cases with mock costs
✓ Environment variables documented
✓ No performance regression

### Effort Estimate: 3-4 hours
### Impact: Prevents runaway costs
''',
            'source_type': 'feature_request',
            'source_module': 'llm_services',
        },
        {
            'title': 'Implement Comprehensive Error Handling & Retry Logic',
            'priority': 'medium',
            'description': '''## Priority: MEDIUM
## Category: Reliability

### Issue:
LLM service lacks sophisticated error handling for transient failures.
Current: Catches errors, returns generic failure message.
Missing: Retry logic, error classification, partial recovery.

### Error Types to Handle:

**Retryable** (with exponential backoff):
- 429 Too Many Requests (rate limit)
- 500 Internal Server Error
- 503 Service Unavailable
- Timeout errors
- Connection errors

**Permanent** (no retry):
- 401 Unauthorized (API key issue)
- 403 Forbidden
- 400 Bad Request (malformed input)
- 413 Payload Too Large

### Implementation:
1. Create error classification function
2. Implement exponential backoff (1s, 2s, 4s, max 3 attempts)
3. Add jitter to prevent thundering herd
4. Store error details in metadata
5. Log all retry attempts
6. Alert on permanent failures

### Error Metadata:
```python
{
    llm_error_category: "rate_limited",
    llm_attempt_count: 2,
    llm_last_error_code: 429,
    llm_last_error_message: "...",
    llm_completion_failed: true
}
```

### Files to Modify:
- services/llm_completion_service.py (error handling)
- services/task_llm_completion_service.py (retry logic)
- tests/test_llm_error_handling.py (8+ test cases)

### Acceptance Criteria:
✓ Error categories properly identified
✓ Retryable errors retry 3x with backoff
✓ Permanent errors fail immediately
✓ All error details logged and stored
✓ 8+ test cases pass
✓ No false recovery attempts

### Effort Estimate: 2-3 hours
### Impact: 99%+ LLM task completion rate
''',
            'source_type': 'reliability',
            'source_module': 'llm_services',
        },
    ]
    
    all_tasks = critical_tasks + high_priority_tasks + medium_tasks
    
    created_count = 0
    for task_data in all_tasks:
        try:
            task = GovernanceTask(
                title=task_data['title'],
                description=task_data['description'],
                source_type=task_data['source_type'],
                source_module=task_data['source_module'],
                priority=task_data['priority'],
                company_id=1,
                status='todo',
                due_date=datetime.now(timezone.utc) + timedelta(days=7),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(task)
            db.flush()
            created_count += 1
            priority_emoji = '🔴' if task_data['priority'] == 'critical' else '🟠' if task_data['priority'] == 'high' else '🟡'
            print(f'✓ Task #{task.id:4d} [{priority_emoji}] {task_data["title"][:75]}')
        except Exception as e:
            print(f'✗ Error creating task: {str(e)[:80]}')
    
    db.commit()
    db.close()
    
    print(f'\n✅ Successfully created {created_count}/{len(all_tasks)} improvement tasks!')
    print('📊 Task Distribution:')
    print(f'   🔴 CRITICAL: {len(critical_tasks)}')
    print(f'   🟠 HIGH: {len(high_priority_tasks)}')
    print(f'   🟡 MEDIUM: {len(medium_tasks)}')

if __name__ == '__main__':
    main()
