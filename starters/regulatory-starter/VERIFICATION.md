# Starter verification and handoff

Date: 30 October 2026. Source: Munafa commit
`aa8d097ad9e8b39c916212f5b9e3696a04315cce`. This package is inherited pre-event
infrastructure plus extraction/glue prepared on that date, **not event-built core**.

## Actual scope

Live working foundation: six PostgreSQL identity/session/idempotency tables,
explicit migrations/provisioning, login/me/logout, CSRF/session scopes, bounded
middleware/rate limiting, React shell/controls/API client, static PWA manifest and
worker. No application data or credentials included. No model/provider call, official
source fetch, regulatory extraction/rule/diff/match/answer/task exists. The neutral
shell's unavailable messages describe that absence and are not fake legal output.

The extracted `Modal.jsx` is provided for later use, not currently displayed. Inert
`reference/` copies include invoice-specific identifiers and dependencies; do not
wire them without a narrow adaptation. No audit-event table, approval execution,
AI telemetry or offline private outbox is enabled in the runnable starter.

## Checks actually run

| Check                                           | Result                                                                                                                                                                          |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Standalone `npm ci` with this folder's lockfile | PASS, local node_modules installed only in this starter; npm reported 0 known findings at installation                                                                          |
| `npm run build` from this folder                | PASS; React/Vite bundle and 5 public shell assets generated; no dependency on Munafa frontend source                                                                            |
| Isolated PostgreSQL tests                       | 8 passed, 0 skipped; existing Starlette/HTTPX deprecation warning                                                                                                               |
| Clean Alembic upgrade and `command.check`       | PASS in disposable schemas; six application tables plus alembic_version; no schema drift                                                                                        |
| Initial migration downgrade/re-upgrade          | PASS only inside a newly generated `starter_test_…` test schema; no real records/reset/import                                                                                   |
| Playwright foundation journey                   | 1 passed: sign-in, all four honest empty-state routes, 320/360/390/430/1280px overflow, sign-out, worker registration, private API excluded from cache and warmed offline shell |
| Ruff lint/format and JS/format checks           | PASS for packaged source                                                                                                                                                        |
| Secret/private-data/package audit               | Explicit allowlisted packaging; no .env/DB/upload/SDK/dependency/build/Git directories; archive integrity/hash inventory checked                                                |

Test PostgreSQL: 17.11 Homebrew. Tests used a dedicated existing local TEST_DATABASE_URL
with newly generated isolated schemas, no fallback. The original `.env` value was
read privately by the verification orchestrator to connect to the dedicated test
service; it was not copied into this starter or archive or printed. Running the
starter on a different machine requires your own new application/test databases.
Tests create explicit synthetic accounts only, never synthetic regulations or alerts.

Local verification used the already-installed parent virtualenv Python 3.13 for
convenience; the test process working directory/Python import root was THIS starter.
The new dependency lock was installed independently. Follow README to create a new
`.venv` after copying out. Nothing in packaged source requires a parent checkout,
parent .env, global credentials or a particular user's filesystem path.

Reproducible commands after configuring the independent environment:

```sh
npm ci
npm run build
npm test
npm run test:e2e
.venv/bin/ruff check backend scripts/serve_e2e.py
.venv/bin/ruff format --check backend scripts/serve_e2e.py
```

Playwright requires Chromium; install through its normal supported process if not
present. Optional `PLAYWRIGHT_EXECUTABLE_PATH` selects an installed binary. Browser
test runner uses local port 8011 and its own `starter_e2e_…` schema; no existing
server reuse. Optional `STARTER_TEST_PYTHON` selects an interpreter for tests, not
provider credentials. Abrupt OS kill can leave a disposable schema; do not guess
objects to drop. Graceful runner shutdown removes only its own namespace/child.

An expanded idempotency test initially hit the SPA mount because its test-only probe
was registered after static routes. The fixture now explicitly places that test route
before the mount; all eight checks then passed. No runtime permission, middleware,
rate limit or test assertion was weakened.

## Untested / not claimed

- No deployed app, real legal corpus, provider account, regulatory performance or
  legal-review result. No claim of hackathon eligibility/acceptance.
- No physical Android/OS PWA install, native wrapper, screen-reader audit or broad
  browser support. SVG icon is a foundation asset; verify real platform install
  metadata/icons before claiming installation readiness.
- No production identity/account lifecycle, password reset/signup/OTP/SSO,
  distributed rate limiter, compliance certification, external notifications or
  legal document malware/SSRF pipeline. Source handling belongs to the new build.
- No new owner account, application database, public deployment or GitHub repo was
  created automatically. No credentials, screenshots of private data or backup file
  included. Source has no top-level project licence chosen by this package.

## Where the next agent should start

1. Open the COPIED standalone folder as the new workspace root. Read README,
   REUSE-MANIFEST and MASTER-PROMPT. Preserve original Munafa unchanged.
2. Establish event window and organiser reuse interpretation; disclose all inherited
   and packaging work. This package contains no event-only regulatory implementation.
3. Confirm narrow activity/state. Create new PostgreSQL app/test DBs and account;
   verify the foundation with the provided commands.
4. During the authorised event window build Phase A→G in MASTER-PROMPT sequentially.
   First tangible domain result should be a real official-source fetch persisted
   with original bytes/hash/date/provenance, not a generated dashboard.
5. Record gaps honestly; maintain handoff/checkpoints. Do not expose personal profile
   data to providers without purpose/permission or invent legal facts/measurements.
