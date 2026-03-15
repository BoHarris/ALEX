#!/usr/bin/env python3
"""Create detailed improvement tasks for repository scanning."""

from database.database import SessionLocal
from database.models.governance_task import GovernanceTask
from datetime import datetime, timezone

def main():
    db = SessionLocal()
    
    improvement_tasks = [
        {
            'title': 'Add Input Validation for LLM Settings API Endpoint',
            'description': '''## Priority: HIGH
## Category: Code Quality & Security

### Current Issue:
The POST /api/llm/settings endpoint in routers/llm_admin.py (line 139-195) lacks comprehensive input validation.

### Required Implementation:
1. Add validation for max_tokens: must be > 0 and <= 4096
2. Add whitelist validation for model names (claude-3-5-sonnet-20241022, etc.)
3. Return detailed error messages for each validation failure
4. Add unit tests for boundary conditions (6+ cases)

### Files to Modify:
- routers/llm_admin.py (lines 139-195)
- services/llm_config.py (add validation function)
- tests/test_llm_admin_endpoints.py (create new)

### Acceptance Criteria:
✓ Separate validation function in services/llm_config.py
✓ All invalid inputs rejected with 400 status
✓ Detailed error messages in response
✓ 6+ test cases covering edge cases
✓ No breaking changes to valid requests''',
            'source_type': 'code_review',
            'source_module': 'llm_admin',
            'priority': 'high',
        },
        {
            'title': '[CRITICAL SECURITY] Complete LLM Admin API Authorization Checks',
            'description': '''## Priority: CRITICAL
## Category: Security & Access Control

### Current Issue:
LLM admin endpoints have TODO markers for incomplete authorization checks in routers/llm_admin.py.

### Security Gaps:
- Any authenticated user can trigger LLM completions for ANY company's tasks
- Any user can update global LLM settings (should be super-admin only)
- No company_id scoping validation
- No role-based access control

### TODO Locations:
- Line 52: manually_trigger_llm_completion() - missing auth check
- Line 166: update_llm_settings() - missing super-admin check  
- Line 203: get_llm_task_history() - missing auth check

### Required Implementation:
1. manually_trigger_llm_completion:
   - Verify current_user.company_id == company_id parameter
   - Check current_user.role in ['admin', 'organization_admin']
   - Reject with 403 if unauthorized

2. update_llm_settings:
   - Require current_user.role == 'super_admin'
   - Add audit logging for all config changes
   - Reject with 403 if unauthorized

3. get_llm_status:
   - Verify current_user has access to company_id
   - Enforce company scoping

### Files to Modify:
- routers/llm_admin.py (complete all TODO markers)
- tests/test_llm_api_authorization.py (create new, 8+ cases)

### Acceptance Criteria:
✓ All TODO markers removed with proper implementation
✓ Unauthorized requests return 403 Forbidden
✓ All config changes logged in activity trail
✓ 8+ authorization test cases pass
✓ Security audit approved''',
            'source_type': 'security_audit',
            'source_module': 'llm_admin',
            'priority': 'critical',
        },
        {
            'title': 'Implement LLM Cost Tracking and Budget Enforcement',
            'description': '''## Priority: MEDIUM
## Category: Feature Implementation & Cost Management

### Current Issue:
No mechanism to track LLM API costs or enforce budget limits. System can make unlimited Claude API calls.

### Cost Metrics Needed:
1. Tokens used per task from Claude API response
2. Cost calculation: (input_tokens × $0.003 + output_tokens × $0.015) / 1M
3. Daily/monthly cost rollup
4. Budget threshold alerts and enforcement

### Implementation:
1. Extract token_usage from Claude response (messages.usage fields)
2. Calculate and store cost in task metadata:
   - llm_cost_usd: 0.00125
   - input_tokens: 200
   - output_tokens: 300

3. Before calling Claude API, check:
   - Daily budget spent so far
   - If at limit, return 429 Too Many Requests

4. Update status endpoint to show:
   - total_tokens_used_today
   - estimated_cost_today
   - budget_remaining
   - success_rate

### Database Storage:
- Store costs in activity_log event_metadata
- Metadata JSON: {llm_cost_usd, tokens_used, completion_source}

### Files to Create:
- services/llm_cost_tracker.py (cost calculation & tracking)
- tests/test_llm_cost_tracking.py (5+ test cases)

### Files to Modify:
- services/llm_completion_service.py (capture token usage)
- services/task_llm_completion_service.py (store costs)
- routers/llm_admin.py (metrics endpoint)

### Configuration:
- Add env var: LLM_DAILY_BUDGET_USD (default: 10.00)
- Add env var: LLM_WARN_THRESHOLD_PCT (default: 80)

### Acceptance Criteria:
✓ Cost tracking implemented and accurate
✓ Budget enforcement prevents API calls when exceeded
✓ Status endpoint shows all cost metrics
✓ 5+ unit tests with mock costs
✓ Documentation updated with budget config parameters''',
            'source_type': 'feature_request',
            'source_module': 'llm_services',
            'priority': 'medium',
        },
        {
            'title': 'Fix Syntax Error and Add Error Handling in AWS Config Connector',
            'description': '''## Priority: HIGH
## Category: Bug Fix & Reliability

### Current Issue:
File: connectors/aws_config.py, lines 22-33

**Syntax Error on Line 32:**
```python
except(BotoCoreError, ClientError) as e:  # Missing space!
```

Should be:
```python
except (BotoCoreError, ClientError) as e:
```

### Additional Issues Found:
1. No logging before re-raising exception
2. No timeout handling for AWS API calls
3. Generic RuntimeError doesn't preserve exception chain (should use `raise ... from e`)
4. No retry logic for transient failures (500, 503)
5. Error message doesn't include AWS operation context
6. Code formatting issues: inconsistent spacing

### Required Changes:
1. Fix syntax error (add space before parenthesis)
2. Add logging.error() with full context
3. Preserve exception chain: `raise RuntimeError(...) from e`
4. Add timeout parameter to AWS client calls
5. Implement exponential backoff for retries (max 3 attempts)
6. Improve error messages with operation/resource context
7. Clean up formatting (remove extra spaces in kwargs)

### Files to Modify:
- connectors/aws_config.py

### Acceptance Criteria:
✓ Syntax error fixed - code passes linting
✓ All tests pass
✓ Proper exception chaining maintained
✓ Logging includes full operational context
✓ 4+ error scenario test cases pass
✓ Code formatting consistent with project standards''',
            'source_type': 'bug_report',
            'source_module': 'connectors',
            'priority': 'high',
        },
        {
            'title': 'Complete LLM Task Generation History with Activity Log Retrieval',
            'description': '''## Priority: MEDIUM
## Category: Feature Completion & Observability

### Current Issue:
GET /api/llm/task-history/{task_id} endpoint (routers/llm_admin.py lines 202-241) has placeholder TODO:

```python
# TODO: Retrieve full generation history from activity logs
# For now, return current state from metadata
```

### Problem:
- Only shows CURRENT LLM metadata, not historical attempts
- If task regenerated multiple times, only latest visible
- No audit trail showing who triggered each generation
- Missing timestamps per generation attempt
- No success/failure tracking per attempt

### Required Implementation:
Query activity_log table for complete history:
```sql
SELECT * FROM activity_log 
WHERE action = 'llm_completion_generated'
AND target_id = {task_id}
ORDER BY created_at DESC
```

For each activity record, extract and return:
- attempt_number (sequence)
- timestamp (created_at)
- triggered_by (actor_label/actor_email)
- model (from event_metadata)
- status (success/failed from event_metadata)
- tokens_used (from event_metadata)
- cost_usd (from event_metadata)
- error_message (if failed)

### Response Format:
```json
{
  "task_id": 123,
  "llm_attempted": true,
  "llm_successful": true,
  "generations": [
    {
      "attempt_number": 2,
      "timestamp": "2024-01-15T10:35:00Z",
      "triggered_by": "claude_auto OR admin@company.com",
      "model": "claude-3-5-sonnet-20241022",
      "status": "success",
      "tokens_used": 450,
      "cost_usd": 0.00135,
      "error": null
    }
  ]
}
```

### Files to Modify:
- routers/llm_admin.py (lines 202-241)
- tests/test_llm_admin_endpoints.py (add test cases)

### Acceptance Criteria:
✓ Full generation history retrieved from activity log
✓ All metadata fields populated correctly
✓ Sorted by timestamp DESC (newest first)
✓ 4+ test cases covering multiple generations
✓ Performance acceptable for large histories
✓ Handles tasks with no LLM attempts gracefully''',
            'source_type': 'code_review',
            'source_module': 'llm_admin',
            'priority': 'medium',
        },
        {
            'title': 'Calculate Actual LLM Status Metrics from Activity Logs',
            'description': '''## Priority: MEDIUM
## Category: Observability & Monitoring

### Current Issue:
GET /api/llm/status endpoint (routers/llm_admin.py lines 98-137) has hardcoded placeholder values:

```python
"avg_generation_time_seconds": 8.5,  # TODO: Calculate from activity logs
"last_error": None  # TODO: Retrieve from recent activity logs with errors
```

### Missing Calculations:

**1. avg_generation_time_seconds:**
- Query activity_log for completed llm_completion_generated actions
- Calculate duration: EXTRACT(EPOCH FROM (updated_at - created_at))
- Average durations for last 24 hours only
- Handle NULL completed_at gracefully

**2. last_error:**
- Find most recent failed LLM attempt
- Include: error message, timestamp, task_id
- Show which task failed

**3. Additional metrics to add:**
- success_rate (% of generations that succeeded)
- total_tokens_used_today (from activity log metadata)
- estimated_cost_today (sum of llm_cost_usd)
- failure_count_24h
- average_tokens_per_generation

### Database Queries:
```sql
-- Success rate and duration
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN metadata->>'llm_completion_failed' = 'true' THEN 1 END) as failed,
  AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration
FROM activity_log
WHERE company_id = {company_id}
AND action = 'llm_completion_generated'
AND created_at > NOW() - INTERVAL '24 hours'
```

### Files to Modify:
- routers/llm_admin.py (lines 98-137, replace hardcoded values)
- tests/test_llm_admin_endpoints.py (add mock activity log tests)

### Acceptance Criteria:
✓ No hardcoded placeholder values
✓ All metrics calculated from actual activity logs
✓ 24-hour rolling window for recent metrics
✓ 5+ test cases with mock activity data
✓ Query performance acceptable
✓ Handles empty history gracefully''',
            'source_type': 'code_review',
            'source_module': 'llm_admin',
            'priority': 'medium',
        },
        {
            'title': 'Add Comprehensive Error Handling & Retry Logic for LLM API Failures',
            'description': '''## Priority: HIGH
## Category: Reliability & Resilience

### Current Issue:
services/llm_completion_service.py (lines 56-90) has broad, undifferentiated error handling:

```python
except (APIError, APIConnectionError) as e:
    logger.error(...)
    raise LLMAnalysisError(...)
except Exception as e:  # Too broad!
    logger.error(...)
    raise LLMAnalysisError(...)
```

### Problems:
1. Generic Exception catch masks bugs in our code
2. No distinction between retryable vs permanent failures
3. No rate limiting error handling (429 Too Many Requests)
4. No timeout handling (should retry vs fail)
5. Incomplete error details stored in metadata
6. No backoff strategy for transient failures

### Error Categories & Handling:

| Error | Type | Action |
|-------|------|--------|
| 429 Too Many Requests | Retryable | Exponential backoff (1s, 2s, 4s) |
| 500 Internal Error | Retryable | Exponential backoff (1s, 2s, 4s) |
| 503 Service Unavailable | Retryable | Exponential backoff (1s, 2s, 4s) |
| 401 Unauthorized | Permanent | Log alert, disable feature |
| 400 Bad Request | Permanent | Log error, fail immediately |
| 413 Payload Too Large | Retryable | Truncate input, retry |
| timeout | Retryable | Increase timeout, retry once |

### Implementation:
1. Create error classification function:
   - classify_error(exception) -> {retryable, category, code}

2. Implement exponential backoff:
   - Max 3 attempts total
   - Delays: 1s, 2s, 4s
   - Add jitter to prevent thundering herd

3. Store detailed error in metadata:
   ```python
   metadata: {
       llm_error_category: "rate_limited",
       llm_attempt_count: 2,
       llm_last_error_code: 429,
       llm_last_error_message: "...",
       llm_last_attempt_timestamp: "...",
       llm_completion_failed: true
   }
   ```

4. Metrics & Alerting:
   - Log retry attempts
   - Alert on permanent failures (401, 403)
   - Track failure rate

### Files to Modify:
- services/llm_completion_service.py (add error handling)
- services/task_llm_completion_service.py (store error details)
- tests/test_llm_error_handling.py (create, 8+ cases)

### Test Scenarios:
- Mock 429 error, verify retry happens
- Mock 401 error, verify no retry
- Mock timeout, verify once retry
- Verify exponential backoff delays
- Verify metadata populated correctly

### Acceptance Criteria:
✓ Error categories properly classified
✓ Retryable errors retry with backoff (max 3)
✓ Permanent errors fail immediately
✓ Detailed error info stored in metadata
✓ 8+ test cases for different failure modes
✓ No silent failures (all errors logged)''',
            'source_type': 'code_quality',
            'source_module': 'llm_services',
            'priority': 'high',
        },
        {
            'title': 'Implement Custom LLM Prompts & Company-Specific Fine-Tuning',
            'description': '''## Priority: MEDIUM
## Category: Feature Enhancement & ML Operations

### Current Issue:
All tasks use the same generic system prompt (services/llm_completion_service.py line 25).

### Opportunity:
- Per-company customized system prompts
- Per-task-type optimized templates
- Collect training data from human edits
- A/B test different models
- Improve prompt effectiveness over time

### Implementation:

**1. Create prompt_templates table (migration):**
```sql
CREATE TABLE llm_prompt_templates (
    id SERIAL PRIMARY KEY,
    company_id INTEGER,  -- NULL = global default
    task_type VARCHAR(100),  -- "backlog_improvement", "security"
    system_prompt TEXT,
    model VARCHAR(100),  -- claude version
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(company_id, task_type)
)
```

**2. Modify analyzer to load company-specific prompts:**
- Query template for (company_id, task_type)
- Fall back to (NULL, task_type) if no company-specific
- Fall back to hardcoded default

**3. Collect feedback data:**
Track when humans edit AI-generated content:
```python
# When task moves to review, calculate edit distance
human_edits = {
    implementation_summary: 45% changed,
    review_notes: 10% changed,
    execution_notes: 20% changed
}
# Store in separate llm_feedback table for analysis
```

**4. Create admin API endpoints:**
- GET /api/llm/prompt-templates - list all
- POST /api/llm/prompt-templates - create new
- PUT /api/llm/prompt-templates/{id} - update
- DELETE /api/llm/prompt-templates/{id} - delete
- GET /api/llm/feedback - view human editing patterns

### Files to Create:
- migrations/versions/*_add_llm_prompt_templates.py
- models/llm_prompt_template.py
- tests/test_llm_prompt_templates.py

### Files to Modify:
- services/llm_completion_service.py (load dynamic prompts)
- services/task_llm_completion_service.py (collect feedback)
- routers/llm_admin.py (add API endpoints)

### Acceptance Criteria:
✓ Prompt template table created
✓ Dynamic prompt loading working
✓ CRUD APIs fully functional
✓ Company scoping enforced
✓ Feedback collection logging
✓ 6+ test cases
✓ Default fallback working properly''',
            'source_type': 'feature_request',
            'source_module': 'llm_services',
            'priority': 'medium',
        },
        {
            'title': 'Build Comprehensive E2E Integration Tests for LLM Workflow',
            'description': '''## Priority: HIGH
## Category: Testing & Quality Assurance

### Current Status:
- test_llm_completion.py: 14 unit tests ✓
- test_llm_integration_workflow.py: 6 integration tests ✓
- **Missing**: Real end-to-end workflow tests

### E2E Scenarios to Add:

**Scenario 1: Happy Path (Complete Success)**
```
1. Create automation task → status=todo
2. Move to in_progress
3. LLM trigger fires (non-blocking)
4. Claude API called (mocked as success)
5. Task moves to ready_for_review
6. LLM metadata populated:
   - implementation_summary
   - review_notes
   - execution_notes
7. Activity log entry created
8. All database writes verified
```

**Scenario 2: Error Recovery & Retry**
```
1. Create task
2. Move to in_progress
3. LLM trigger fires
4. Claude API returns 429 (rate limit)
5. Retry logic triggered (1s delay)
6. Second attempt succeeds
7. Task reaches ready_for_review
8. Verify both attempts recorded in activity log
```

**Scenario 3: Concurrent LLM Calls**
```
1. Create 5 tasks
2. Move all to in_progress simultaneously
3. 5 LLM calls queued in rapid succession
4. Verify no database conflicts/race conditions
5. All tasks eventually reach ready_for_review
6. Verify all completed successfully
```

**Scenario 4: Large Input Handling**
```
1. Create task with 50KB description
2. LLM triggered
3. Claude API returns 413 (payload too large)
4. Input truncated appropriately
5. Retry with smaller payload succeeds
6. Task completes normally
```

**Scenario 5: Task with Edits Before LLM Runs**
```
1. Create task
2. Move to in_progress
3. Human edits task while LLM runs
4. Verify no data conflicts
5. Task still completes successfully
```

### Test Infrastructure Needed:
- Mock Claude API with configurable responses
- Mock database for transaction testing
- Background task queue simulator
- Activity log verification utilities

### Files to Create:
- tests/test_llm_e2e_workflow.py (100+ lines, 5+ scenarios)

### Files to Modify:
- tests/conftest.py (add E2E fixtures)

### Test Execution:
```bash
pytest tests/test_llm_e2e_workflow.py -v --tb=short
```

### Acceptance Criteria:
✓ 5+ E2E test scenarios implemented
✓ Happy path completely covered
✓ Error scenarios with retry working
✓ Concurrent execution handling tested
✓ Database state verified after each scenario
✓ Activity log entries verified
✓ 100% pass rate required
✓ < 30 seconds total execution time''',
            'source_type': 'quality_assurance',
            'source_module': 'llm_services',
            'priority': 'high',
        },
        {
            'title': '[LLM TEST] Fix Frontend TaskDetailDrawer Fragment & Rendering Issues',
            'description': '''## Priority: MEDIUM  
## Category: Frontend Bug Fix

### Current Issue:
frontend/src/components/compliance/tasks/TaskDetailDrawer.js uses React fragments with conditional nesting that could cause rendering issues.

### Code Location:
Lines around LLMGeneratedBadge display and automation form section.

### Potential Problems:
1. Fragment with conditional children may not render consistently
2. Key prop might be missing on list items in rendering
3. Nested conditionals could be optimized for readability
4. No error boundary if LLM metadata is malformed/incomplete
5. No defensive null checks for deep object properties

### Required Changes:

**1. Refactor conditional rendering:**
- Separate LLM display from form rendering
- Use proper React Fragment with clear structure
- Add inline comments for complex conditions

**2. Add error handling:**
- Wrap LLM metadata display in error boundary
- Show user-friendly error if metadata malformed
- Graceful fallback for missing fields

**3. Performance optimization:**
- Memoize LLM metadata parsing
- Prevent re-parsing on every render
- Use useMemo() for expensive operations

**4. Defensive programming:**
- Check for null/undefined at each level
- Provide default values for missing fields
- Handle edge cases (empty strings, NaN, etc.)

### Test Cases to Cover:
1. **Task with no LLM metadata**
   - Should show automation form ONLY
   - No LLM section visible

2. **Task with corrupted/malformed metadata**
   - Should show error message gracefully
   - Form should still be editable

3. **Task with complete LLM data**
   - Show LLM summary section
   - Show form with pre-populated data
   - Both render without errors

4. **Task with partial LLM data**
   - Some fields populated, others missing
   - Should show available fields
   - Missing fields show "(Not available)"

5. **Task transitioning between states**
   - Rapid status changes should not break rendering
   - Concurrent updates should handle gracefully

### Component Changes:
- Update LLMGeneratedBadge component logic
- Add defensive checks in render
- Improve conditional rendering clarity
- Add error boundary wrapper

### Files to Modify:
- frontend/src/components/compliance/tasks/TaskDetailDrawer.js

### Files to Create:
- frontend/src/components/compliance/tasks/__tests__/TaskDetailDrawer.test.js

### Acceptance Criteria:
✓ No console errors in React DevTools
✓ All 5 test cases pass
✓ No layout shifts or flash of content
✓ Graceful error handling working
✓ Error messages helpful to users
✓ Code review approved
✓ Performance acceptable (< 50ms render)

### NOTE:
This is a TEST TASK to validate that the LLM automation system can identify, analyze, and provide solutions for real frontend issues!''',
            'source_type': 'bug_fix',
            'source_module': 'frontend',
            'priority': 'medium',
        }
    ]
    
    # Create tasks
    created_count = 0
    for task_data in improvement_tasks:
        try:
            task = GovernanceTask(
                title=task_data['title'],
                description=task_data['description'],
                source_type=task_data['source_type'],
                source_module=task_data['source_module'],
                priority=task_data['priority'],
                company_id=1,
                status='todo',
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
    
    print(f'\n✅ Successfully created {created_count}/{len(improvement_tasks)} improvement tasks!')
    print('🚀 Tasks are now ready in the automation system!')

if __name__ == '__main__':
    main()
