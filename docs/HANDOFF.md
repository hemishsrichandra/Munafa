# Next-chat handoff · Batches 2–5

Updated **30 October 2026** (Batch 5 backend commit). Start here after the usage window/chat ends. Read BATCH-5.md first, then BATCH-4.md, SYNC-PROTOCOL.md, BATCH-2.md, BATCH-3.md and the actual source/tests before editing.

## Authorization and repository state

> **Batch 5 backend committed.** Frontend UI, offline outbox guard and `test_commerce.py` remain. See `docs/BATCH-5.md`.

- Workspace: `/Users/hemish/Sem-3/Munafa`; branch **main**; owner repo `https://github.com/hemishsrichandra/Munafa.git`.
- Initial committed baseline was **9f426e4**. This handoff includes the previously uncommitted Batch 2/3 implementation plus Batch 4. The owner explicitly requested a proper commit and push before exit; use `git log -1`, `git status --short --branch` and the remote to identify the exact published revision.
- **Batch 4 is the last authorized implementation batch. Wait for the owner’s Batch 5 prompt.** Do not infer the remaining master-playbook details. The owner also approved Google's Android SDK license during Batch 3.
- Do not reset/clean the checkout, overwrite work with the old initial commit, import legacy `.data/*.db`, reset demo records, delete DB volumes or downgrade populated schemas. Real-data import/destructive change requires verified backup and explicit approval.

## What exists

React 19/Vite + FastAPI/Pydantic, PostgreSQL only through SQLAlchemy Core/Psycopg. Four Alembic migrations, current head **67e38dd313f8** (Batch 5: products, purchases, receiving, inventory events). Server startup checks the exact head and performs no DDL/seed/import.

Supplier invariants: invoice capture → merchant physical receiving and unit/delivery/pricing checks → exact paise calculation/approval snapshot → explicit manual sharing confirmation → promise → evidence-backed recovery. Promise is never recovery. Preserve deduplication, immutable snapshots/audit/financial history, expected versions, principal-derived store scope and exact approval payload binding.

Phone UI: Home/Purchases/More, existing-record brief, mobile case cards, PWA shell/install/update/offline cache. Capacitor wraps the **same React build**.

Batch 4: Drafts & sync uses version-1 IndexedDB for scoped identity-only grant, minimal unapproved receiving cache, manual invoice/receiving drafts, attachment blobs, outbox and status. State transitions and exact wire requests persist. Batches have at most 3 operations, 12s request timeout, 45s claim lease, exponential backoff/jitter and 5 automatic attempts. A fresh server membership check precedes every batch. Repeated operation UUID/body returns the original PostgreSQL receipt; conflicts never overwrite accepted history. See SYNC-PROTOCOL.md for contracts/retention/threat model.

No stock ledger, sale/customer-credit module, forecast, live analytics, automatic supplier sending or live Paytm connection exists. Inventory drafts are ineligible until the relevant server ledger exists. No IndexedDB token storage, device-level encryption, guaranteed background delivery or recovery of evicted unsynced drafts is claimed. Sarvam providers are mocked in tests; live account access remains unverified.

## Local environment and startup

- PostgreSQL **17.11 (Homebrew)**, fresh dev cluster `/private/tmp/munafa-pg-b23-20261030`; log `/private/tmp/munafa-pg-b23.log`; listen **127.0.0.1:55432**, database **munafa_b23**. Loopback-only trust authentication is a local test setup, not production security.
- Ignored `.env` mode 0600 holds URLs and a random private demo access code. Do not print/commit it. TEST*DATABASE_URL uses this local database, but fixtures create unique `test*...`/`e2e\_...` schemas, never public application tables.
- A labelled synthetic A-104 demo case was explicitly seeded only if the isolated demo store was empty. No existing/legacy record was reset or imported.
- Run `npm run dev` if UI/API are not already listening. UI **http://127.0.0.1:5173**; API **http://127.0.0.1:8000**. Use Development demo access with the private code in `.env`, or provision an owner through `backend.manage create-owner`.
- To test PWA installation/offline worker behavior, use the built app at port **8000**, not Vite. Production build exists locally; `npm run build` refreshes it.

Check the existing PostgreSQL cluster before starting it; never initialize a replacement:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /private/tmp/munafa-pg-b23-20261030 status
# Only if stopped:
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /private/tmp/munafa-pg-b23-20261030 -l /private/tmp/munafa-pg-b23.log -o '-h 127.0.0.1 -p 55432' start
```

For another machine use README/Compose with private credentials and a separate test database. No database fallback is allowed if access is blocked.

## Checks and known warnings

From the repository root:

```sh
npm test
npm run test:offline
.venv/bin/alembic check
.venv/bin/ruff check backend scripts/serve_e2e.py
.venv/bin/ruff format --check backend scripts/serve_e2e.py
npm run format:check
npm run test:e2e
```

Verified: **57 PostgreSQL backend tests, 12 IndexedDB tests and 14 browser tests pass**. Metadata drift check, format/lint and production build pass. The browser suite uses isolated synthetic identities/stores and checks an actual 12s timeout after server acceptance, exact duplicate-proof replay, offline reload, attachments, quota, expired auth and receiving conflict.

If the pinned Playwright browser is unavailable, this cached executable worked locally:

```sh
PLAYWRIGHT_EXECUTABLE_PATH=/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell npm run test:e2e
```

PostgreSQL/network/local server access required sandbox escalation in this session. Use the authorized safe path; never replace tests with SQLite. One non-failing Starlette HTTPX test-client deprecation warning remains. CI is configured; do not claim its remote status without checking GitHub.

## Android and artifacts

Current ignored APK: `artifacts/munafa-debug.apk`, also `android/app/build/outputs/apk/debug/app-debug.apk`; **4,333,280 bytes**, SHA-256:

```text
f385c75e9a39f1b2b0dcfe4c737cd29e009b4a8de724c43bce7f950409a829a5
```

Signature verified; every packaged public asset byte-matches current frontend/dist. Build/lint succeeds (0 errors, 28 existing warnings). This is **debug signing only**. Instrumented package assertion matches `in.munafa.businesspartner`; no device tests ran.

```sh
npm run android:sync
cd android
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home ANDROID_HOME=/private/tmp/munafa-android-sdk ./gradlew assembleDebug lintDebug --no-daemon
```

Temporary tools: Temurin **21.0.13+9**, Gradle **8.11.1**, SDK **35** with build tools 34/35. Installed Java 25 was incompatible. Temporary SDK/JDK paths may disappear; install permanent tools for ongoing development.

**No hosted HTTPS backend is configured in this APK.** First connected sign-in requires an owner-approved endpoint, public VITE_API_BASE URL and exact native APP_ORIGINS `https://localhost` on the backend. Never bundle a credential in VITE variables. Without configuration the APK only opens the public shell and explains the missing backend. Private offline drafts require a previous verified sign-in on that installation.

Screenshots: ignored `test-results/offline-draft-phone.png` (390px, visually inspected) plus existing phone/rotation/workflow screenshots. APKs, environment files, `.data`, screenshots/test output, signing keys and SDKs remain excluded from Git.

## Remaining acceptance and next phase

1. Review the delivered batches. Provide HTTPS hosting only if a connected APK demo is desired. Run real Android installation/login/file/share/Back/offline cold-start/process-kill/storage-pressure/app-update checks. None has been claimed as tested.
2. Before real merchant data: production identity/account operations, least-privilege DB role, verified backups/restores, deployment protections, file scanning/retention and privacy/support procedures. No production pilot readiness is claimed.
3. Before live AI claims: authorised Sarvam contract/model checks and correction-adjusted task time/accuracy/cost/latency evaluation. No live Paytm access or fabricated operational events.
4. **Batch 5 backend is committed.** Remaining Batch 5 work: 9 frontend UI screens, offline outbox guard lift (remove `sync.js` stock-ledger error), `backend/tests/test_commerce.py` (~19 test cases), and final `BATCH-5.md` / HANDOFF update. See `docs/BATCH-5.md` for the complete checklist.
5. Final merchant validation, presentation and demo video are still outstanding. Business impact must be measured, not asserted.

Suggested next-chat prompt:

> Read docs/HANDOFF.md and docs/BATCH-5.md, inspect Git status/history and the actual source/tests. The Batch 5 backend (schema, services, API) is complete and committed. Continue with: (1) frontend UI screens for purchases/receiving/stock/expiry, (2) lifting the offline outbox guard in sync.js, (3) writing backend/tests/test_commerce.py, (4) updating HANDOFF.md and pushing before exit. Preserve store isolation, exact-money rules, append-only history, approval binding and conflict handling. Do not import/reset legacy data.
