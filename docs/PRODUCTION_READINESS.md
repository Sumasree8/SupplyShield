# Production-Readiness Changes

This document records the fixes applied to take SupplyShield AI from "scaffolded"
to "builds, runs, and is covered by real tests." Grouped by severity.

## Critical — the project did not build or run

| Issue | Fix |
|-------|-----|
| App is async (`create_async_engine` + `asyncpg://`) but only the sync `psycopg2-binary` driver was in `requirements.txt` — no `asyncpg`. | Replaced `psycopg2-binary` with `asyncpg` + `greenlet`. |
| `passlib[bcrypt]==1.7.4` with an unpinned `bcrypt` resolved to bcrypt 5.x, which removed `bcrypt.__about__` — **all password hashing/login broke at runtime**. | Pinned `bcrypt==4.0.1`. |
| `docker-compose` ran `celery -A src.tasks.celery_app`, but no `celery_app` **module** existed (only a variable inside `ingestion.py`) — workers crash-looped, so no ingestion ever ran. | Added `src/tasks/celery_app.py` re-exporting the configured Celery app. |
| Backend `Dockerfile` never copied `migrations/` (so `alembic upgrade head` failed) and `pip install --user` into `/root/.local` was unreadable by the `appuser` runtime user. | Copy `migrations/`; install into `/usr/local` prefix (world-readable, on PATH). |
| Frontend had no `package-lock.json`, so `npm ci` (Docker + CI) failed; `Dockerfile` used the bogus `--frozen-lockfile` npm flag. | Generated and committed `package-lock.json`; fixed the Dockerfile. |
| `vitest run` exited non-zero with no test files, failing CI. | Added `--passWithNoTests` and real tests. |
| `database.py` passed `pool_size`/`max_overflow` unconditionally — rejected by SQLite, blocking lightweight/local/test runs. | Pool args applied only for non-SQLite URLs. |

## High — features were silently broken

| Issue | Fix |
|-------|-----|
| **Auth bypass**: `get_current_user` accepted any token with a `sub`, so a 7-day **refresh token** authenticated every protected route. | Enforce `payload["type"] == "access"`. |
| `created_at` is a DB `server_default`; `register`/`/me` read it right after `flush()` when it was still `None`. | `await db.refresh(user)` after flush. |
| **`/me` 500'd**: it accessed `current_user.organization.name`, triggering an async lazy-load → `MissingGreenlet`. | Eager-load the organization via `selectinload`. |
| **Supplier create/list 500'd**: `SupplierResponse` had `id: str` but ORM attributes are `uuid.UUID`; Pydantic v2 won't coerce. | Coercing `StrId`/`OptStrId` annotated types on response models. |
| Alert status updates assigned a raw string to an enum column and compared `str == Enum` (always false) — lifecycle timestamps never set; **no way to create an alert at all**. | Coerce to `AlertStatus`, validate transitions (`ALERT_STATUS_TRANSITIONS`), and added `POST /api/v1/alerts`. |
| The "pure, tested" recommendation scorer was **not used** by the API — the service re-implemented (and had already drifted from) it. | Service now delegates to `recommendation_scoring.score_candidate`/`serialize_recommendation`. |
| Synchronous Neo4j calls (`session.run`, `verify_connectivity`) ran on the async event loop, blocking all requests. | Offloaded to threads via `asyncio.to_thread`. |
| Notifications (Slack/email) were entirely unimplemented despite settings and the `notifications_sent` column. | Added `notification_service.py` (Slack webhook + SMTP), wired into alert creation. |
| GDELT `_extract_countries` read a non-existent `mentions` field — `affected_countries` was always empty, so events never matched suppliers. | Read GDELT's actual `sourcecountry` field. |

## Medium — hardening & honesty

- Risk scoring no longer fabricates `data_sources` (`_score_climate` used to always claim both NOAA + OpenWeather); it records each event's real source.
- Prometheus `http_requests_total` / `http_request_duration_seconds` are now actually recorded (in `RequestLoggingMiddleware`, with route-template labels to bound cardinality); previously defined but never incremented. Removed the dead no-op `AuditMiddleware`.
- `Settings` fails fast in production on a weak/placeholder `SECRET_KEY` or wildcard `ALLOWED_HOSTS`; `ALLOWED_HOSTS` is now wired through `docker-compose`.
- nginx: added a Content-Security-Policy, used `always`, and repeated security headers in the static-asset block (a local `add_header` otherwise drops inherited ones).
- Frontend: added an `ErrorBoundary` (render throws no longer white-screen the SPA) and fixed the 401 refresh interceptor (single in-flight refresh, `_retry` guard against infinite loops).

## Tests

Replaced the previous suite — which re-implemented logic inline and asserted on the
copy (≈31 of 44 tests imported no `src` code) — with **44 real tests** (38 backend +
6 frontend) that drive the actual app, services, and ORM. Writing them surfaced the
`/me` lazy-load crash and the `SupplierResponse` UUID-serialization bug above.

Models use dialect-portable column types (`src/models/types.py`) so the suite runs on
in-memory SQLite with no Postgres dependency, while production keeps native `UUID`/`JSONB`.

## Local toolchain note

The pinned dependencies target **Python 3.12** (as do CI and the Docker images). On a
machine with only Python 3.14, create the venv with a pinned interpreter, e.g.
`uv venv --python 3.12` before `pip install -r requirements.txt`.
