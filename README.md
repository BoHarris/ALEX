# ALEX Privacy Scanning Platform

ALEX is a FastAPI + React application for scanning uploaded datasets, detecting PII, redacting sensitive values, and providing downloadable outputs and audit-style reports.

## Current Capabilities

- WebAuthn passkey authentication
- Access token + refresh token session flow (refresh token in `HttpOnly` cookie)
- File upload and scan pipeline:
  - parse data
  - detect PII
  - redact sensitive values
  - compute risk score
  - persist scan metadata
- Tenant-aware scan access control
- Download endpoints for redacted files and HTML/PDF reports
- Admin company overview endpoint with analytics summaries
- Company settings endpoint (plan-gated)
- Audit event feed endpoint (plan-gated)
- Public product pages: Home, Trust, About, Careers, Pricing

## Architecture

- Backend: FastAPI + SQLAlchemy
- Frontend: React + Tailwind CSS
- Database: SQLAlchemy `DATABASE_URL` (SQLite fallback for local development)

## Security Notes

- Passkeys are used for authentication (no password login flow in current implementation).
- Refresh tokens are stored in `HttpOnly` cookies with `SameSite=strict`.
- Cookie `secure` flag is enabled in production and disabled in local development.
- Protected routes require bearer access tokens.
- Scan/report download routes enforce tenant-aware authorization checks.

## Rate Limits and Quotas

- Tier-based scan limits are enforced server-side.
- Plan-based defaults:
  - Free: `1` scan/day, `5MB` upload limit
  - Pro: `100` scans/day, `10MB` upload limit
  - Business: `500` scans/day, `25MB` upload limit

## Runtime Requirements

Required environment variables:

- `SECRET_KEY`

Production-only required variables:

- `DATABASE_URL`

Recommended environment variables:

- `ENV` (`development` or `production`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_MINUTES`
- `CHALLENGE_TTL_MINUTES`
- `ORIGIN`
- `RP_ID`
- `RP_NAME`
- `CORS_ORIGINS`
- `LOG_LEVEL`
- `LOG_MAX_BYTES`
- `LOG_BACKUP_COUNT`
- `ENABLE_STARTUP_SCHEMA_BOOTSTRAP` (set to `true` only for explicit local bootstrap)

## Startup Validation

On startup, ALEX validates:

- environment/auth settings
- database connectivity
- required schema state
- writable directories (`uploads`, `redacted`, `logs`)
- required assets (including report font)
- PDF report dependency availability

If required schema/tables/columns are missing, startup fails fast with a clear error.

## Local Development

1. Install dependencies for backend and frontend.
2. Configure `.env` for local development.
3. Start backend:

```bash
uvicorn main:app --reload
```

4. Start frontend:

```bash
cd frontend
npm start
```

## API Notes

- Upload/scan route: `POST /predict/`
- Current user route: `GET /protected/me`
- Scan list route: `GET /scans`
- Admin overview route: `GET /admin/overview`
- Admin audit feed route: `GET /admin/audit-events`
- Security dashboard route: `GET /admin/security-dashboard`
- Incident feed route: `GET /admin/incidents`
- Company settings routes:
  - `GET /admin/company-settings`
  - `PUT /admin/company-settings`
- Protected asset routes:
  - `GET /scans/{scan_id}/download`
  - `GET /scans/{scan_id}/report/html`
  - `GET /scans/{scan_id}/report/pdf`

## Scope Clarification

This repository currently focuses on a production-minded beta foundation and does not yet include:

- billing/subscription management
- full audit log explorer UI

## Security Controls

The current architecture includes additive enterprise security controls intended to support audit readiness without claiming certification:

- Centralized immutable-style audit logging via `audit_logs`
- Role-aware authorization with `user`, `organization_admin`, and `security_admin` access controls
- Scan lifecycle retention fields on `scan_results` for active, archived, and expired states
- Security alert generation for suspicious login activity, token abuse patterns, and excessive scan activity
- Global request IDs, structured request logging, HTTPS enforcement in production, and standard web security headers
- Basic incident tracking via `security_incidents`
- distributed background worker processing
- globally distributed rate limiting infrastructure
