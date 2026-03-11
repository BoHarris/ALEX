# ALEX

ALEX is a privacy-focused SaaS application for detecting sensitive information in files and datasets, applying redactions, and operating privacy workflows with auditability.

The project combines:

- a FastAPI backend for authentication, scanning, reporting, audit logging, and internal governance APIs
- a React frontend for customer-facing product workflows and the internal Compliance Workspace
- a growing internal control layer for security, governance, retention, incident handling, testing visibility, and release review

## Current Architecture

- Backend: FastAPI, SQLAlchemy, WebAuthn-based authentication, structured security/audit logging
- Frontend: React, React Router, Tailwind-style utility classes
- Database: SQLAlchemy-backed `DATABASE_URL` with local SQLite fallback for development
- Auth model: passkeys/WebAuthn plus bearer access tokens and refresh cookies
- Internal operations: route-backed Compliance Workspace for employees, policies, vendors, incidents, risks, access reviews, training, testing, audit logs, and code review

## Project Structure

```text
main.py                       FastAPI application entrypoint
routers/                      API route modules
services/                     business logic, security, compliance, reporting
database/                     database setup and SQLAlchemy models
dependencies/                 FastAPI dependency guards
utils/                        shared helpers and feature gating
frontend/                     React application
tests/                        backend test coverage
models/                       ML/training-related code and local model asset location
uploads/                      local upload storage in development
redacted/                     generated redacted outputs in development
logs/                         runtime logs in development
```

## Key Implemented Areas

- WebAuthn authentication and token-based session flow
- File upload, scanning, redaction, and downloadable reports
- Tenant-aware access controls and plan-aware limits
- Immutable-style audit logging and security alerts
- Scan retention and archive lifecycle controls
- Admin reporting and security dashboard APIs
- Internal Compliance Workspace with route-backed modules
- Pre-production Code Review workflow for release/change review
- Public product pages including Trust, Pricing, About, Careers, and Privacy

## Required Runtime Assets

ALEX currently expects these runtime assets:

- `DejaVuSans.ttf`
  - versioned in the repository
  - required for report generation/startup validation
- `models/xgboost_model.pkl`
  - required for scan startup/runtime
  - not committed to the repository
  - must be generated or supplied locally before full scan functionality will work

Legacy/generated font cache pickles and archived model pickles are intentionally not tracked.

## Getting Started

### 1. Create a Python environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install backend dependencies

This repository currently does not include a pinned root `requirements.txt` or `pyproject.toml`, so backend dependencies need to be installed into your local virtual environment based on the application stack.

At minimum, the environment should include packages used by the codebase such as:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `alembic`
- `python-dotenv`
- `webauthn`
- `reportlab` or `weasyprint`
- the ML/data-processing dependencies needed by the scan pipeline

If you are preparing this repository for broader external use, adding a pinned backend dependency manifest would be the next cleanup step.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configure environment variables

Create a local `.env` file in the repository root.

Important variables include:

- `SECRET_KEY`
- `ENV`
- `DATABASE_URL`
- `ORIGIN`
- `RP_ID`
- `RP_NAME`
- `CORS_ORIGINS`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_MINUTES`
- `CHALLENGE_TTL_MINUTES`

For local development, `ORIGIN` and `RP_ID` should align with your local frontend host. If `ENV=production`, startup validation still enforces HTTPS except for explicit localhost development usage.

### 5. Ensure required local assets exist

Before full startup:

- keep `DejaVuSans.ttf` in the repository root
- place or generate `models/xgboost_model.pkl`

### 6. Run database migrations

Apply the versioned schema before starting the backend:

```bash
alembic upgrade head
```

If startup reports a schema version mismatch, migrate the database before retrying.

### 7. Start the backend

Either of these reflects the current app entrypoint:

```bash
python main.py
```

or

```bash
uvicorn main:app --reload
```

The backend runs on `http://127.0.0.1:8000` by default.

### 8. Start the frontend

```bash
cd frontend
npm start
```

The frontend is configured to proxy API calls to `http://127.0.0.1:8000`.

## Startup Behavior

On startup, ALEX validates:

- environment configuration
- database connectivity
- current migration/schema revision
- required schema state
- writable runtime directories (`uploads`, `redacted`, `logs`)
- required report/font assets
- PDF report dependency availability

This is intentional: startup should fail fast when the runtime is incomplete or the database has not been migrated.

## Useful Endpoints

- `GET /health`
- `GET /ready`
- `POST /predict/`
- `GET /protected/me`
- `GET /scans`
- `GET /admin/overview`
- `GET /admin/audit-events`
- `GET /admin/security-dashboard`
- `GET /compliance/overview`
- `GET /compliance/code-reviews`

## Internal Compliance Workspace

The internal workspace is route-backed and currently includes:

- Overview
- Employees
- Policies
- Vendors
- Incidents
- Risks
- Access Reviews
- Training
- Code Review
- Testing & Validation
- Audit Log

This area is intended to support operational maturity and enterprise-readiness work without claiming certification.

## Repository Notes

- Local runtime directories such as `uploads/`, `redacted/`, and `logs/` are intentionally ignored.
- Local databases, caches, and generated build output are ignored.
- Generated font cache files and archived pickle artifacts are not part of the public source of truth.

## Testing

Backend tests:

```bash
python -m pytest tests
```

Database migrations:

```bash
alembic upgrade head
alembic downgrade -1
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Public Repo Status

This repository is an active product codebase, not a polished SDK or template. Some startup dependencies, especially the local scan model artifact, still require developer setup. The codebase is production-minded, but the repository remains under active refinement as the platform evolves.
