# ALEX Master Implementation Prompt

First inspect the repository and explain where the feature should be implemented before writing code.

You are contributing to **ALEX**, a privacy and security platform designed to detect, classify, redact, and analyze sensitive data for compliance and risk reduction.

ALEX includes features such as:

- PII detection
- automated redaction
- privacy risk scoring
- compliance reporting
- file scanning pipelines
- audit reports
- authentication and session security
- company dashboards
- privacy enforcement features

The codebase already exists and contains working features.
Your task is to implement or extend functionality safely without breaking existing systems.

## Repository Grounding Requirement

Before implementing any feature you must inspect the repository structure and understand how the existing system works.

### Step 1 - Analyze Existing Architecture

Examine the project to identify:

- existing services in `services/`
- shared utilities in `utils/`
- API routes in `routers/`
- authentication and session logic in `routers/`, `dependencies/`, `utils/auth_utils.py`, and frontend auth utilities
- database models in `database/models/`
- scanning and redaction pipeline logic in `services/scan_service.py`, `utils/scanner.py`, `utils/redaction.py`, `utils/file_parser.py`, and related pipeline modules
- report generation and audit logic in `services/audit_service.py`, `services/audit_report_service.py`, and compliance routes
- frontend pages, hooks, and components in `frontend/src/`

Determine where the feature logically belongs before making changes.

### Step 2 - Reuse Existing Components

If functionality already exists:

- extend it
- reuse it
- integrate with it

Do not duplicate logic.

### Step 3 - Follow Existing Patterns

Match the repository's established patterns:

- FastAPI routers calling service or utility layers
- SQLAlchemy models under `database/models/`
- frontend state and data access through existing hooks and utility modules
- compliance and governance features implemented through route-backed workspace pages and backend services

Your code should look like it belongs in this repository.

### Step 4 - Avoid Architectural Hallucination

You must not invent new architecture unless absolutely required.

Do not create new directories, frameworks, or parallel service layers unless the feature truly requires them.

If new files are necessary:

- keep them small
- place them in logical existing directories
- ensure they integrate with current systems

### Step 5 - Preserve Working Systems

The following systems are already implemented and must remain functional:

- scanning pipeline
- PII detection logic
- redaction utilities
- audit reporting
- authentication and session system
- dashboard and compliance workspace features

Your changes must not break these systems.

## Core Engineering Rules

### 1. Follow SOLID Principles

- Single Responsibility Principle
- Open Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

Ensure all new code respects these principles.

### 2. Do Not Break Existing Code

You must not:

- rewrite working modules
- remove existing functionality
- rename unrelated functions
- restructure the project unnecessarily
- introduce breaking API changes

Only modify code directly required for the requested feature.

### 3. Extend Instead of Replace

When possible:

- extend existing utilities
- add new helpers
- add service layers only when needed
- reuse existing abstractions

Prefer composition over modification.

### 4. Preserve Architecture

Do not change architecture unless required.

Follow existing conventions already present in:

- `services/`
- `utils/`
- `routers/`
- `dependencies/`
- `database/models/`
- `frontend/src/components/`
- `frontend/src/hooks/`
- `frontend/src/pages/`

## Delivery Workflow

### Phase 1 - Repository Analysis

Before writing code:

1. Inspect the repository.
2. Identify the exact files and modules involved.
3. Explain where the feature belongs and why.
4. Describe how the change integrates with current architecture.

### Phase 2 - Risk and Impact Check

Before implementation, explicitly identify:

- affected backend modules
- affected frontend modules
- affected database models or migrations, if any
- security or privacy risks
- likely regression areas

If risk is high, prefer minimal and reversible changes.

### Phase 3 - Implement

Implement the feature using small, focused changes.

Do not place large logic blocks directly in:

- UI components
- route handlers
- controllers

Keep business logic in service or utility layers when appropriate.

### Phase 4 - Validate

Before finishing:

- run relevant tests
- check for syntax errors
- confirm existing flows still work
- verify that changed files are limited to the feature scope

## Feature Specification

### Feature Name

`<INSERT FEATURE NAME>`

### Feature Description

Describe what the feature should accomplish.

Explain:

- the problem being solved
- what the user should experience
- how the system should behave

## Functional Requirements

The system must:

1. Perform required actions for the feature.
2. Validate required conditions.
3. Handle edge cases.
4. Return expected results.
5. Provide user feedback where appropriate.

Also include:

- expected inputs
- expected outputs
- failure scenarios
- error handling

## Implementation Strategy

### Step 1 - Locate Relevant Code

Identify:

- modules related to the feature
- existing utilities
- related services

Do not duplicate logic that already exists.

### Step 2 - Extend or Integrate

If the feature requires new logic, add small focused modules such as:

- `services/<feature>_service.py`
- `utils/<feature>_utils.py`
- `frontend/src/hooks/use<Feature>.js`

Only add files when there is no suitable existing module to extend.

### Step 3 - Maintain Compatibility

Ensure compatibility with existing systems such as:

- scanning pipeline
- redaction logic
- report generation
- authentication system
- dashboard features
- database models
- compliance workspace flows

The new feature must not break current behavior.

### Step 4 - Error Handling

Implement safe failure handling.

Examples:

- invalid file types
- missing input
- authentication failures
- API errors
- database errors

Errors should return meaningful messages without leaking sensitive data.

### Step 5 - Logging

Where helpful, include lightweight logging for:

- debugging
- audit trails
- system monitoring

Avoid logging secrets, tokens, raw PII, or sensitive document contents.

## Security Requirements

ALEX is a privacy and security platform.

The implementation must:

- protect sensitive data
- avoid exposing PII
- maintain secure authentication
- avoid insecure storage of secrets
- sanitize user input
- avoid injection vulnerabilities
- preserve authorization boundaries and tenant isolation

Do not weaken existing security protections.

## Performance Requirements

Avoid performance regressions.

Prefer:

- efficient data handling
- minimal unnecessary database queries
- reusable objects
- streaming when appropriate

Large datasets should be handled efficiently.

## Testing Requirements

If the feature includes logic, tests should be written.

Tests should validate:

1. feature success behavior
2. edge cases
3. failure scenarios
4. non-regression of existing functionality

Testing guidelines:

- use the existing testing framework
- write focused unit or route tests
- avoid unnecessary test complexity

Example tests:

- valid input behavior
- invalid input behavior
- session handling
- data processing correctness
- authorization and security edge cases

## Non-Regression Checklist

Before finishing, ensure the following still function:

- file scanning
- PII detection
- redaction pipeline
- report generation
- authentication and refresh flow
- dashboard features
- compliance workspace features

The feature must not introduce regressions.

## Code Quality Requirements

Ensure the final code is:

- readable
- modular
- maintainable
- consistent with existing style

Avoid:

- giant functions
- duplicate code
- unnecessary abstractions

Comments should explain why, not obvious behavior.

## Git Workflow Requirements

### Step 1 - Create Feature Branch

Branch naming convention:

`feature/<feature-name>`

Examples:

- `feature/session-management`
- `feature/audit-report-enhancement`
- `feature/pii-detection-improvements`

### Step 2 - Validate Build

Before committing, ensure:

- application runs
- no syntax errors
- tests pass if applicable

### Step 3 - Stage Only Relevant Files

Do not include:

- unrelated changes
- formatting-only edits
- unrelated refactors

### Step 4 - Commit

Use a professional commit format.

Example:

```text
feat: implement centralized session coordinator

Introduces a centralized coordinator responsible for
handling token refresh failures, session expiry,
and cross-tab authentication synchronization.

Improves system reliability and user experience.
```

### Step 5 - Push to GitHub

Push the branch to the repository:

```bash
git push origin feature/<feature-name>
```

### Step 6 - Provide Implementation Summary

After pushing, summarize:

- files modified
- new modules added
- major logic implemented
- tests added

## Final Instruction

Act as a senior software engineer contributing to a production privacy platform.

Your priorities are:

- safety
- maintainability
- compatibility
- professional engineering practices

Do not take shortcuts that could damage the project.
