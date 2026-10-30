# Batch 2: PostgreSQL data and trust foundation

## Implemented

The existing FastAPI/React supplier workflow is preserved. All application and automated-test persistence uses PostgreSQL through SQLAlchemy Core and Psycopg 3. Alembic owns schema creation. No SQLite file is opened, imported, deleted or used as a fallback. The old reset command now refuses to reset records.

Normalized entities cover merchants, stores, users, store memberships, hashed sessions, suppliers, invoices/lines, shortage cases, attachments, resolutions, financial events, audit events, assistant actions and idempotency receipts. No inventory or new merchant feature is introduced.

Money uses BIGINT paise. Quantities use NUMERIC(20,6), accepted as exact decimal strings or integers; binary floating quantities and excess precision are rejected. Shortage amounts round HALF_UP to a whole paise once per line. Dates use the verified store timezone; instants are TIMESTAMPTZ and serialize in UTC.

Financial/resolution/audit rows reject UPDATE and DELETE using PostgreSQL triggers. Recovery totals can be rebuilt from the `case_recovery_balances` SQL view over financial events. Runtime DB roles must not own tables or have permission to disable triggers; database administrators remain trusted operators.

## Authentication and approvals

Password login uses scrypt and opaque random 12-hour sessions, stored as SHA-256 token hashes. Cookie sessions are HttpOnly, SameSite=Strict, and Secure in production. Unsafe authenticated requests require the session-bound X-CSRF-Token. Origin policy uses APP_ORIGINS; native origins must be deliberately added when native connectivity is tested.

Owner can read/write/approve/message/export/admin. Staff can read/write. Viewer can read only. Tenant identity comes from session membership, never request JSON. Development login requires APP_ENV=development/test, ALLOW_DEV_LOGIN=1 and a private 16+ character access code. Production refuses to start with development login enabled. No Paytm SSO, OTP or live payment connection exists.

Every authenticated mutation requires Idempotency-Key. A PostgreSQL transaction advisory lock serializes a store-scoped key. Blocking authentication/connection/lock operations run off the async event loop; an eight-request per-loop bound keeps connection and worker capacity available for commits. A 12-request same-event-loop regression verifies duplicate retries complete once rather than blocking the server. The accepted response and business changes commit atomically. Different payloads/actors cannot reuse a key. Expected versions still reject stale edits. Failed requests roll back and are not recorded as accepted operations.

The central action primitive supports case approval and ledger export. Proposals carry source/version, payload digest, risk, expiry and actor. Approval binds the current proposal version/digest. Revisions clear approval. Execution rechecks permission, source version, expiry and payload. Direct merchant case approval passes through the same primitive. A ledger download now requires a separately approved/executed export action, bound to the exact sorted case IDs and versions. A changed ledger invalidates the export. Native clients can obtain a memory-only bearer session after verified login; logout revokes it server-side.

## Local setup

Install Python dependencies from `backend/requirements-dev.txt`, run `npm ci`, and create a private `.env` from `.env.example`. Generate your own local Postgres password; no actual credential belongs in version control.

Docker option:

```sh
docker compose up -d postgres
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.manage create-owner
npm run dev
```

Alternatively, install PostgreSQL 17 locally and supply a `postgresql+psycopg://...` DATABASE_URL. Use a separate TEST_DATABASE_URL with a role permitted to create disposable schemas. Tests never use the default application schema or another database engine.

Optional synthetic demo: configure explicit development access, then run `.venv/bin/python -m backend.manage seed-demo`. It creates an isolated demo store and seeds A-104 only if empty; it never resets records. All records entered in that demo store remain labelled synthetic. Live stores cannot call the synthetic invoice endpoint.

## Migrations, backup and legacy records

Application startup checks for the current Alembic head; it never runs DDL or seeds data. Apply reviewed migrations before starting a deployment. Down migrations remove schema objects and must only run on an empty disposable test schema or after verified backup and explicit owner approval.

Before a real cutover: stop writes, use `pg_dump --format=custom` into a private backup, compute its SHA-256, and restore with `pg_restore` into a separate verification database. Compare counts, state/version distribution, paise totals, audit snapshots and attachment digests. Never run `pg_restore --clean` against a live database without a separately reviewed plan and approval. A rollback means disabling traffic/restoring PostgreSQL, never enabling another database fallback.

Legacy `.data/*.db` files remain untouched archival artifacts. No importer is provided because their real-data status and import permission have not been established. If preservation is requested, design a separately invoked read-only archival extractor after backup/explicit approval, with rejected-record reporting and count/checksum reconciliation. Do not run the previous SQLite application to migrate records automatically.

## Validation and limitations

The converted supplier regression suite runs on PostgreSQL. Added checks cover isolation, role denial, CSRF, duplicate operations, approval digest/revision/expiry, exact quantities, schema types, rollback and append-only audit protection. Migration downgrade/upgrade runs only on a fresh empty test schema. Verified on PostgreSQL **17.11 (Homebrew)**: **52 backend tests pass**, including the original 36 supplier tests. The test run includes fresh-schema upgrade, empty-schema down/up, metadata drift check, rollback, concurrent identical operations, native session revocation, exact fractional workflow/message and invoice supplier-source preservation. Ruff checks pass. One non-failing Starlette HTTPX test-client deprecation warning remains.

Rate limiting currently uses bounded per-process memory. Use one API worker initially and an ingress rate limiter before a multi-worker deployment. Upload signatures and size bounds remain; antivirus scanning, retention automation and deployment secret management require operational infrastructure. Live Sarvam calls remain unverified. No real documents were imported.

## Completion report

- **Scope:** Batch 2 only added data/trust foundations to the existing supplier workflow. Batch 3 followed separately as authorized.
- **Files:** `backend/{db,models,auth,security,actions,store,manage}.py`, existing `app.py`/`domain.py`/fixtures, `backend/migrations`, PostgreSQL fixtures/trust tests, `compose.yaml`, `.env.example`, requirements locks and `.github/workflows/checks.yml`.
- **Schema:** baseline `8eb2b55dbe9b`, append-only triggers/recovery projection `2a6b45d80201`, invoice supplier identity `37c45f100e71` (head).
- **API:** authenticated existing case API; `/api/auth/{login,dev-login,me,logout}`; `/api/actions` proposal, revision, approval and execution; approved `/api/export?action_id=...`. No client-provided store switch or tenant identifier is trusted.
- **Environment:** DATABASE_URL, TEST_DATABASE_URL, DATABASE_SCHEMA, APP_ENV, APP_ORIGINS; explicit ALLOW_DEV_LOGIN/DEV_LOGIN_CODE only outside production. Safe examples contain placeholders.
- **Data:** a fresh isolated local PostgreSQL cluster was created on loopback port 55432. No legacy records imported, reset or deleted; import counts/checksums are not applicable. Disposable test-schema teardown and empty test rollback are isolated from application records.
- **Validation:** `npm test` → 52 pass; `.venv/bin/ruff check backend` and format check pass. Production build and browser regression results are in Batch 3. CI is configured but has not run on GitHub.
- **Operational gaps:** no password-reset/SSO flow, no membership-management UI, no shared rate limiter, no antivirus/retention jobs, no deployed least-privilege database role or automated backup verification. These limit production readiness; local tests do not establish a secure production deployment.
- **Approval boundary:** any legacy real-data import, destructive rollback/reset or production cutover still requires a verified backup and explicit approval. No such action was performed.
