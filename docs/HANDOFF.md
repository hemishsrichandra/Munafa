# Cross-system handoff — merchant UI polish

**Latest: [UI-POLISH.md](UI-POLISH.md)** documents the merchant-facing cleanup. Home/More/Connections/Stock planning/Exports now show task information without build diagnostics; bill inputs use rupees and still submit integer paise. P2 API gates and approvals are unchanged. Latest verification: 246 backend, 23 browser and 18 frontend tests pass; the final desktop More-route refinement also has a focused browser check. Read UI-POLISH.md for APK evidence and current screen names.

## Previous final checklist review

**Latest: [FINAL-CHECKLIST-REVIEW.md](FINAL-CHECKLIST-REVIEW.md)** checks all 31 owner checklist items, records the synthetic data now on the website and lists required access/decisions. Latest run: 246 backend, 22 browser and 17 frontend tests pass. Three exact-money audit/evidence formatting conversions were repaired; no schema/dependency changes. Existing merchant data was preserved.

## Extension handoff

**Read [EXTENSION-HANDOFF.md](EXTENSION-HANDOFF.md) first for the latest state**, then [POST-PLAYBOOK-STATUS.md](POST-PLAYBOOK-STATUS.md) for all 47 extension acceptance gates. The historical Batch 10 snapshot below remains useful for local setup and earlier release evidence; its counts/APK hash are superseded by the extension report.

## Historical Batch 10 demo candidate

Updated **30 October 2026, Asia/Kolkata**. Start with BATCH-10.md and DEMO.md, then inspect actual source/tests and Git status. Historical batch guides are descriptions, not proof of current implementation.

## Git, scope and release decision

- Repository: `https://github.com/hemishsrichandra/Munafa.git`; this checkout `/Users/hemish/Sem-3/Munafa`, branch `main`.
- Batch 10 follows **4e7fcb9** (Batch 9 gates), **85eaefb** (Batch 7), **9408088** (Batch 6) and **cba2166** (Batch 5 completion). `git log -1 --oneline` identifies the final published Batch 10 commit.
- Owner authorised integration/hardening/testing/documentation only, no new merchant product features. Standing instruction: update this handoff, commit and push before exiting so another machine/chat can continue.
- **Local synthetic demo candidate only.** No production readiness, live Paytm, real bank verification, real-provider performance, revenue uplift, fraud prevention or legal certification is claimed.
- Preserve exact paise/decimal math, store scope, approval digest/version, append-only history, duplicate guards and offline conflict handling. Never reset/import/delete existing merchant data or downgrade populated schemas without verified backup, reviewed plan and explicit approval.
- No future batch is implicitly authorised. **Batch 8/P1 remains absent.** P2 business capabilities remain disabled/blocked; their readiness checks are working safeguards, not order/lending/peer engines.

## Actual implementation and Batch 10 changes

React **19.2.6** + Vite **6.4.5**, FastAPI/Pydantic, SQLAlchemy Core/Psycopg, PostgreSQL only; Alembic head remains **c6ec82a178d3**. No schema migration/dependency framework replacement in Batch 10. Startup checks migrations and never create-all/seeds/resets/imports. Browser offline state is scoped IndexedDB, not SQL.

Working: reviewed purchase intake, independent partial/final physical receiving, exact append-only inventory, SKU thresholds/actual expiry, original six-stage supplier recovery, durable outbox, PWA shell, deterministic labelled settlement fixtures and source-linked brief, curated-source help, optional unverified cloud proposal adapters, P2 readiness gates. Invoice acceptance does not add stock; accepted undamaged physical receiving does. Supplier promises do not count as recovery. Actual SKU sale data requires explicit merchant/POS evidence; payments do not imply sales or debt.

Batch 10 fixes:

- Bounded chunked request reads (9 MB API / 16 KB auth) before full allocation/DB work; safe malformed-length rejection.
- Redacted validation inputs, nested safe 422 and caught invalid decimal conversion.
- Repeatable-read export snapshot, formula escaping and exact paise rendering; real request operation ID on accepted inventory/receipt events.
- Obvious active/embedded PDF rejection on new uploads; this is not antivirus/content disarm or retroactive scanning.
- Complete-build check before mounting static assets; build/test sequence remains explicit.
- Small text/focus contrast and phone form readability, reverse-tab containment, disabled busy close controls, actual store initials and missing/large-money display fixes.
- Vite **6.4.1→6.4.5**, source-map-js **1.2.1→1.2.2** patched; clean lockfile install and npm audit show zero known findings at this check. Python dependency compatibility passes; Python CVE scanning is not performed because pip-audit is absent.
- Expanded release security matrix, image/manual-fallback corpus tests, complete phone purchase-to-partial/full recovery and throttled/offline/keyboard checks. Browser builds force a same-origin API so tests cannot target a configured live host. Test server forces cloud keys off and has graceful cleanup confined to its own child/schema.

Key new files: `backend/tests/test_release.py`, `frontend/tests/money.test.mjs`, `tests/e2e/release.spec.js`, `scripts/audit_release.py`, `docs/BATCH-10.md`. Existing small core fixes are in app/security/domain, money/UI helpers and verification scripts. No real messages/orders/credit applications/tax submissions were sent.

## Reproduce on another system

```sh
git clone https://github.com/hemishsrichandra/Munafa.git
cd Munafa
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
npm ci
cp .env.example .env
# Fill private PostgreSQL URLs/credentials and exact APP_ORIGINS.
# Provision PostgreSQL using README/Compose; never use a fallback database.
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.manage create-owner
npm run dev
```

Use `.venv/Scripts/python.exe` / `alembic.exe` on Windows. npm Python scripts select the platform path. No API key is needed for manual workflows, deterministic help or explicitly loaded synthetic settlement demo. Production must not enable development login. Keep speech preview/P2 flags off until their acceptance requirements are actually satisfied.

For a resettable **disposable synthetic rehearsal**, see DEMO.md: `npm run build`, then `node scripts/python.cjs scripts/serve_e2e.py`, browse `http://127.0.0.1:8001` and use its explicitly public test-only account. This creates a new random schema in TEST_DATABASE_URL, not the application schema. Ctrl+C/graceful stop cleans only that runner's own schema/child. Abrupt kill may leave a disposable namespace; do not guess/drop existing namespaces. Start a fresh one. `backend.reset_demo` intentionally refuses to delete data.

The final review servers were left running by `npm run dev` in local exec session 90186 (session IDs are not portable). Health was checked without signing in/seeding. On another system run your own setup; inspect ports before starting a duplicate. Normal UI: `http://127.0.0.1:5173`; API/built PWA: `http://127.0.0.1:8000`. PWA tests use the production build. Build before API startup/collection, never rebuild the same dist concurrently with serving. First connected cache/sign-in is required; offline dynamic APIs/AI and a first sign-in are unavailable. Verified local workspace grant is eight hours. No interactive store selector exists: session selects the active store; spoofed client store fields/headers cannot switch it.

## Final verified commands / pass versus skipped

Execute sequentially around frontend builds:

```sh
npm ci
npm run build
# PG_BIN is optional tool location, not an application DB mode.
PG_BIN=/opt/homebrew/opt/postgresql@17/bin RELEASE_EVIDENCE_DIR=artifacts/test-evidence npm test
npm run test:offline
PLAYWRIGHT_EXECUTABLE_PATH=/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell npm run test:e2e
.venv/bin/alembic check
.venv/bin/ruff check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py scripts/audit_release.py
.venv/bin/ruff format --check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py scripts/audit_release.py
npm run format:check
.venv/bin/python scripts/audit_release.py
.venv/bin/python -m pip check
npm audit --json
npm run android:check
```

**PASS:** 210 backend tests, 21 browser journeys (2 commerce + 3 partner + 2 release + 14 legacy/offline/PWA), 17 frontend unit tests (14 IndexedDB/outbox + 3 exact money formatting). No skips in these final runs. Backend has one existing Starlette/HTTPX deprecation warning. Build, lockfile install, lint/format/syntax/compile, PostgreSQL drift, source audit and Capacitor doctor/build/lint pass. JS/JSX project has no configured TypeScript semantic checker; syntax/build is not type-safety certification. CI is configured, including source audit; remote job result is not claimed without checking it.

**SKIPPED/UNAVAILABLE:** actual Android/emulator (adb found none), physical camera/OS PWA installation, native process-kill/storage-pressure/update and assistive-technology sessions, broad Safari/Firefox testing, actual Paytm/Sarvam/messaging/lender contracts and measured real language/merchant trials. Python CVE scan (`pip_audit` module missing) is not replaced by pip check. Store selector and Batch 8 modules are not implemented. These are not counted as passing tests.

Release checks cover all **57 private API operations** for anonymous denial (60 API operations total), valid-body cross-store entity families, intentional same-store collaborative reads by role, actor-bound receipts/export denial, source versions/digests, CSRF/session/rate limits, streamed size limits, obvious malicious uploads, CSV formula/concurrency, actual idempotency provenance and offline account purge/conflict/exact retry. Local source/bundle scan found zero known private-config/key matches and zero SQLite imports; no full history/semantic PII/malware/security certification claim.

One local Chromium simulated-network sample is recorded in ignored `artifacts/test-evidence/batch10-browser-performance.json`; BATCH-10.md gives its exact timing values and limitations. It includes scripted login and no CPU throttle, not a field task-time study or Web Vitals/FMP score. Selected key text contrast is ~6.35/8.99:1, phone nav ≥44px and dialog forward/reverse focus checks pass; full WCAG/screen-reader certification did not run.

## PostgreSQL / local state / restore

- This Mac: PostgreSQL **17.11 Homebrew**, existing cluster `/private/tmp/munafa-pg-b23-20261030`, log `/private/tmp/munafa-pg-b23.log`, loopback `127.0.0.1:55432`, DB `munafa_b23`. Ignore sandboxed process-visibility failures; elevated verification showed the actual server. Never initialise over or delete its lock files.
- Private ignored `.env` holds local URLs/demo code; never print/commit it. Local loopback trust/superuser setup is test convenience, not production security. Use least-privilege application roles in deployment.
- Tests use generated `test_...` / `e2e_...` schemas. Release restore needs supported pg_dump/pg_restore via PATH or PG_BIN and a **disposable test role** with CREATE DATABASE rights; do not grant production roles extra rights for tests. Missing/older tools produce an explicit skip, not successful restore evidence.
- **PASS synthetic restore:** backup of an owned random synthetic fixture schema, archive TOC verification before import, restore to a newly created `release_restore_...` database, matching counts/canonical content hashes across 32 app tables. Synthetic 8000 paise recovery and 2 kg stock plus indexes/constraint validation match. Only generated test objects were cleaned. The configured application database was not restored over.
- Result: ignored `artifacts/test-evidence/postgres-restore.json`; archive is private in pytest temp output. This does not prove recovery of any real merchant backup. Earlier private backup `artifacts/private/pre-batch6-postgres.dump` remains untouched and excluded from Git; no real-data import/reset was performed. Legacy `.data` files were never opened/imported by the app/tests.

## Android and evidence artifacts

Same React build and business rules, Capacitor 7.6.10, no duplicate native screens. Debug APK `artifacts/munafa-debug.apk` and `android/app/build/outputs/apk/debug/app-debug.apk` are **ignored**, not in Git. Final size/SHA-256 is in BATCH-10.md and ignored `artifacts/test-evidence/batch10-android.json`; it supersedes prior local artifacts. Signature verifies and every packaged public asset matches frontend/dist. Debug signing only; standard META-INF/Gradle flatDir/SDK XML warnings remain. Lint: **0 errors / 0 fatal / 28 existing warnings**.

```sh
npm run android:sync
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home ANDROID_HOME=/private/tmp/munafa-android-sdk ./android/gradlew -p android assembleDebug lintDebug --no-daemon
```

Temporary Java **21.0.13+9**, Gradle **8.11.1**, SDK **35** paths may disappear; install permanent tools elsewhere. Owner previously authorised the Android SDK licence. No microphone/location/contacts permission was introduced. `adb devices -l` found no device/emulator; no real-device test ran. No hosted HTTPS API is configured in this APK: provide an approved public VITE_API_BASE and exact native APP_ORIGINS before connected device login; never put a credential in VITE values. Bundled public shell can open without backend, private offline drafts require a previous verified sign-in.

Ignored screenshots include `artifacts/test-evidence/batch10-integrated-recovery.png` (visually inspected), previous partner/readiness captures and PWA/offline outputs. Public corpus images under evaluation/ are synthetic and committed. No private documents, credentials, backups, keys, logs or APKs should be added to Git.

## Remaining risks / next work (separate authorisation)

1. Real device/browser/OS install/camera/share/Back/update/process-kill/eviction and assistive-technology testing; approved HTTPS hosting, native origin setup and release signing.
2. Authorised Paytm merchant/environment entitlement, official signature/schema/timezone contract, real bank/settlement feed and authorised E2E; no staging assumption. WhatsApp handoff is not a delivery receipt. No automatic supplier/customer messages exist.
3. Real consented/redacted invoice ground truth, held-out provider comparisons, actual billing and correction-adjusted merchant trials; actual voice/language/noise matrix. Synthetic parser/mocks are not OCR/merchant outcome metrics. Verify provider retention/DPA/region before real documents/audio; account defaults were not inspected.
4. Production account/store operations, least-privilege DB roles, real backup/restore objectives, file scanning/retention/deletion and distributed rate limiting/log/security/privacy review. Original documents/audits have no full deletion administration; do not claim compliance. Python dependency CVE review/full history-secret/PII/penetration testing remains.
5. Batch 8/P1 source models and quality evaluation need explicit scope. P2 ordering/lending/peer results remain gated until real evidence, consent/contracts/methodology and fresh central approvals exist. No creditworthiness or sales should be inferred from unrelated records.
6. Record the demo video/presentation from DEMO.md and validate with actual merchants. No outcome uplift or time-saved claim is justified by synthetic rehearsal timings.

Suggested continuation:

> Pull origin/main, inspect Git status/history, read docs/HANDOFF.md, BATCH-10.md and DEMO.md. Batch 10 is a tested local synthetic demo candidate with explicit skipped/external checks; no live Paytm/real device/provider performance or production/legal readiness is established. Preserve exact-money, source, tenant, approval, append-only and offline invariants; do not reset/import data. I authorise [specific remaining acceptance or separately scoped implementation]. Update docs/this handoff and commit/push before exit.
