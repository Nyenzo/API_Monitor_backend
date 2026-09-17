# API Monitor Backend

API Monitor is a release-verification and API reliability service for B2B SaaS teams. It turns selected OpenAPI operations into monitored API contracts, runs a bounded verification immediately after a deployment, and stores the result and evidence needed to make a release decision.

The backend is a FastAPI application backed by Supabase Postgres. User-owned data is protected by Postgres row-level security (RLS); the service-role key is used only on the server.

## Capabilities

- Scheduled uptime monitoring with latency, status, and response evidence.
- Contract monitors that check expected status codes and required JSON paths.
- OpenAPI 3.x JSON preview and batch creation of selected contract monitors.
- Named release verifications with `passed`, `regressed`, and `incomplete` decisions.
- Alert rules and email notifications for monitor failures.
- Internal activation metrics for operational use only.

## Repository Layout

```text
app/                    FastAPI routers, schemas, services, and configuration
supabase/migrations/    Ordered Postgres migrations and RLS policies
tests/                  Unit and integration coverage
main.py                 Vercel-compatible ASGI entry point
Dockerfile              Production container image
```

## Prerequisites

- Python 3.12 or later.
- Node.js 20 or later for the Supabase CLI.
- Docker, if running Supabase locally or building the container image.
- A Supabase project for shared or production environments.

## Local Development

Create an isolated Python environment and install the development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

Create local configuration from the example file. Do not commit `.env`.

```bash
cp .env.example .env
```

For a local Supabase stack, start the CLI and apply all migrations from a clean database:

```bash
npx supabase start
npx supabase db reset --local
```

Copy the local API URL, anonymous key, and service-role key reported by `npx supabase status -o env` into `.env`. Generate a strong value for `INTERNAL_API_KEY`; it is used only by trusted internal callers.

Start the API:

```bash
uvicorn main:app --reload --port 8000
```

The health endpoint is available at `GET /health`. Interactive API documentation is available at `/docs` when the app is running.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_URL` | Yes | Supabase project URL. |
| `SUPABASE_ANON_KEY` | Yes | Anonymous key used to validate user requests. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Server-only key for trusted database operations. Never expose it to a browser. |
| `INTERNAL_API_KEY` | Yes in production | Shared secret required by internal metrics and scheduler-facing endpoints. |
| `CORS_ORIGINS` | Yes in production | Comma-separated allow-list of the deployed frontend origins. |
| `RATE_LIMIT_PER_MINUTE` | No | Per-client request limit; defaults are defined in application settings. |
| `MAX_CONCURRENT_CHECKS` | No | Upper bound for concurrent outbound health checks. |
| `MAX_CHECKS_PER_RUN` | No | Upper bound for one scheduled check batch. |
| `SMTP_*` | No | Optional SMTP transport for monitor-alert email. |

Use production secrets only in the deployment provider's encrypted environment-variable store. Do not place keys, passwords, reset URLs, or customer payloads in logs, issues, or frontend build variables.

## Database Migrations

Migrations are source-controlled in `supabase/migrations` and must be applied in order. Make every schema change through a new migration rather than editing an applied migration.

Create and validate a migration locally:

```bash
npx supabase migration new concise_change_name
npx supabase db reset --local
npx supabase db lint --local
```

To apply migrations to a confirmed remote project, export a valid Supabase personal access token with an `sbp_` prefix. Run the dry run first and verify the listed files and project reference before writing anything:

```bash
export SUPABASE_ACCESS_TOKEN=sbp_your_personal_access_token
npx supabase db push --project-ref your-project-ref --dry-run --yes
npx supabase db push --project-ref your-project-ref --yes
npx supabase migration list --project-ref your-project-ref
```

The current release-verification schema is contained in migrations `011_contract_release_verification.sql` and `012_activation_events.sql`. After a remote push, run the Supabase Security Advisor. Any unexpected RLS or function-security warning is a release blocker.

## API Surface

All user-facing routes are prefixed with `/api/v1` and require a Supabase bearer token unless identified as internal.

| Area | Representative routes |
| --- | --- |
| Monitors | `GET, POST /monitors`, `POST /monitors/{id}/test` |
| Check evidence | `GET /monitors/{id}/results` |
| Contracts | `POST /contracts/openapi/preview`, `POST /contracts/monitors` |
| Release decisions | `POST /release-verifications`, `GET /release-verifications`, `GET /release-verifications/{id}` |
| Dashboard and alerts | `GET /dashboard/*`, `GET, POST /alerts/*` |
| Internal operations | `GET /internal/activation-metrics` with `X-Internal-Key` |

Release verification is intentionally bounded: a request accepts one to 25 user-owned contract monitors and uses bounded concurrency. A failed check records precise evidence such as an unexpected status or a missing required JSON path.

## Validation

Run the following before opening a pull request or deploying a backend change:

```bash
pytest -q
npx supabase db lint --local
pip-audit -r requirements.txt
docker build -t api-monitor-backend:local .
```

`requirements.txt` contains production dependencies only. `requirements-dev.txt` adds test tooling. If `pip-audit` is not installed in the active environment, install it outside the runtime requirements or run it in CI.

## Deployment

The repository includes a `Dockerfile` and a Vercel-compatible `main.py` entry point. Deploy the backend before the frontend so the frontend can be configured with its stable API base URL.

For every production deployment:

1. Apply and verify migrations using the dry-run process above.
2. Set all required backend variables in the deployment platform; set `DEBUG=false`.
3. Set `CORS_ORIGINS` to the exact stable frontend origin, for example `https://api-monitor-frontend.vercel.app`.
4. Deploy and confirm `GET /health` returns a healthy response.
5. Use a disposable account to import a public non-sensitive OpenAPI document, create a contract monitor, and run both a passing and controlled failing verification.
6. Confirm evidence remains visible after signing in again and that a separate account cannot access it.

The synchronous release-verification flow can take as long as the bounded monitor set and per-monitor timeout allow. Confirm the deployed Vercel function duration supports that worst case before release. The full release gate, smoke test, and rollback procedure are in [the production release runbook](../docs/PRODUCTION_RELEASE_RUNBOOK.md).

## Security Model

- Supabase RLS restricts monitors, check results, release verifications, and product events to their owning user.
- The backend validates ownership on user-facing mutations and does not rely on the frontend for authorization.
- Outbound monitor targets are validated to reduce server-side request forgery risk.
- Service-role, internal, SMTP, and monitoring credentials remain server-side.
- Internal endpoints require `X-Internal-Key` and must not be called from the frontend.

Review the security guidance in `AGENTS.md`, preserve additive migrations during rollback, and use the Supabase Security Advisor as part of each database release.
