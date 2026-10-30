# Handoff - Batch 5 completion

Updated 30 October 2026. Read docs/BATCH-5.md, docs/SYNC-PROTOCOL.md and the current source/tests before changes.

## Repository and authorization

- Workspace: C:/Users/tharu/OneDrive/Documents/munafa. Remote: https://github.com/hemishsrichandra/Munafa.git. Base commit: 9d23879 on main.
- The current user explicitly authorised completion of Batch 5 and backend/browser testing. Earlier notes saying to wait for Batch 5 are superseded.
- The user authorised committing and pushing the completed Batch 5 work to origin/main. Local research artifacts are excluded from this implementation commit. Preserve the user's pre-existing docs/PRE_HACKATHON_PROPOSAL.md, output/ and tmp/ research artifacts.
- Do not reset/clean the checkout, import legacy .data databases, drop populated schemas, or overwrite merchant data. No such import/reset was performed.

## Current implementation

FastAPI/Pydantic + PostgreSQL/SQLAlchemy Core/Psycopg. Migration head 67e38dd313f8. Startup validates migrations and performs no automatic migration/seed/import. The React/Vite frontend has purchase register/review/intake, physical receiving, stock/SKU management, movement history, expiry and linked Munafa recovery screens.

Invoice acceptance creates no stock. Accepted receiving adds undamaged physical goods only. Partial delivery does not become a final shortage. Overdelivery is preserved as physical evidence/stock and flags the shortage case for review. Monetary calculations remain integer paise; quantities are exact decimal strings. Approvals bind source versions and payload digests. Store scope derives from the authenticated principal.

Offline commerce capture uses the existing scoped IndexedDB, immutable outbox, dependency ordering, leases and bounded retries. New purchases may carry a dependent original-document upload; acceptance is blocked until the expected document arrives. Receiving and stock operations bind the exact source version. Queued proposals do not immediately change confirmed stock. Commerce snapshots expire after 24 hours; identity/role switches purge private local storage as before. The offline grant still expires after eight hours.

The public shell may open offline only after installation/cache. Sign-in and financial acceptance need the backend. No guaranteed background sync, encryption of browser storage, or restoration of evicted unsynced data is claimed. No live Sarvam/Paytm access or native device testing is claimed.

## Windows local tooling

- Python: .venv/Scripts/python.exe. npm scripts now use scripts/python.cjs to select Scripts/python.exe on Windows or bin/python on Unix.
- Temporary PostgreSQL runtime: %TEMP%/munafa-pg-test-runtime/pgsql. Cluster: %TEMP%/munafa-batch5-pgdata; port 5432, loopback only; database munafa_test. Do not initialise a replacement over it. Check status with pg_ctl before starting.
- Local test URL: postgresql+psycopg://munafa@127.0.0.1:5432/munafa_test. This disposable local trust configuration is not a production credential scheme.
- Created an ignored local .env for development, with a separate migrated munafa_batch5_dev database and munafa_test for tests. The development login code is stored privately in that file. Preserve the old .data/munafa.db without importing it. The local app runs at http://127.0.0.1:8000.
- Playwright Chromium was downloaded. Full installed Chrome can be selected with PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe. Windows local browser shutdown stalled, so scripts/browser-tests.cjs owns an isolated browser server and uses remote test connections on Windows. It terminates only its own browser after each group. Commerce and legacy groups use separate disposable API servers to preserve the production login rate limit. Startup timeout is three minutes for local migration/account provisioning. Interrupted diagnostic runs are not counted as passes.

## Verification

- PostgreSQL full suite: 74 passed (251.55s). Batch 5 targeted suite: 18 passed (279.90s), including the added end-to-end offline-commerce/document/receiving/stock retry regression. Total backend cases now 75; the earlier full run covered 74 and the targeted run covers all 18 commerce cases. No backend implementation changed after the full run.
- Browser suite: 16 passed (2 commerce + 14 existing journeys), using isolated Windows browser servers.
- IndexedDB suite: 14 passed.
- Production build: passed.
- Alembic upgrade plus drift check in a fresh disposable PostgreSQL schema: passed (no new upgrade operations).
- Ruff lint/format and Prettier: passed after normalising checkout line endings.
- Existing Starlette/HTTPX test-client deprecation warning remains non-failing.

Commands (PowerShell):

    $env:TEST_DATABASE_URL='postgresql+psycopg://munafa@127.0.0.1:5432/munafa_test'
    npm test
    npm run test:offline
    npm run build
    npm run test:e2e
    .venv/Scripts/ruff.exe check backend scripts/serve_e2e.py
    .venv/Scripts/ruff.exe format --check backend scripts/serve_e2e.py
    npm run format:check

## Remaining external acceptance

Real Android install/login/file sharing/Back/process-kill/low-storage/update tests; authorised live Sarvam evaluation; deployment identity, least-privilege database roles, backups, upload scanning/retention and privacy review before real merchant data. Merchant field validation, presentation and video are still separate deliverables.
