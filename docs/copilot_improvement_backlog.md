# Copilot Improvement Backlog

This backlog is the source of truth for governed automated changes in ALEX.

## ALEX-IMP-001
- Title: Improve task filter control clarity
- Area: Governance Tasks UI
- Priority: High
- Risk: Low
- Status: Open
- Eligible for Automation: Yes
- Dependencies: None
- Suggested Branch: improvement/alex-imp-001-task-filter-clarity
- Description: Expand the task filter controls so operators can understand assignment and open-task scope at a glance.
- Suggested Improvement: Use larger segmented controls and cleaner spacing for task filters without changing the existing filtering behavior.
- Notes: Safe UI polish within the existing tasks workspace.

## ALEX-IMP-002
- Title: Harden automation activity summaries
- Area: Governance Tasks Backend
- Priority: Medium
- Risk: Low
- Status: Open
- Eligible for Automation: Yes
- Dependencies: None
- Suggested Branch: improvement/alex-imp-002-automation-history-summaries
- Description: Ensure automation-owned tasks produce readable activity entries for operators and reviewers.
- Suggested Improvement: Add clearer automation history labels and metadata rendering in task detail.
- Notes: Backend and UI work should remain additive.

## ALEX-IMP-003
- Title: Refine testing workspace empty states
- Area: Compliance Testing UI
- Priority: Medium
- Risk: Low
- Status: Blocked
- Eligible for Automation: Yes
- Dependencies: Await confirmation on final product copy
- Suggested Branch: improvement/alex-imp-003-testing-empty-states
- Description: Improve empty states in the testing workspace so operators know what to do when no cases or runs are present.
- Suggested Improvement: Add clearer copy and next-step actions that reuse the established governance design language.
- Notes: Keep the current routing and testing APIs intact.

## ALEX-IMP-004
- Title: Rework compliance auth boundaries
- Area: Platform Security
- Priority: Critical
- Risk: High
- Status: Open
- Eligible for Automation: No
- Dependencies: Security architecture review
- Suggested Branch: improvement/alex-imp-004-auth-boundaries
- Description: Revisit workspace authorization boundaries across compliance and dashboard modules.
- Suggested Improvement: Audit and redesign the broader auth model with explicit security review.
- Notes: Too risky for unattended automation.

## ALEX-IMP-005
- Title: Archive obsolete governance prompts
- Area: Developer Experience
- Priority: Low
- Risk: Low
- Status: Deferred
- Eligible for Automation: No
- Dependencies: None
- Suggested Branch: improvement/alex-imp-005-archive-prompts
- Description: Organize outdated prompt notes after the automation workflow stabilizes.
- Suggested Improvement: Clean up old planning artifacts once the current governance workflow is merged.
- Notes: Deferred until the automated changes workflow is in production.
