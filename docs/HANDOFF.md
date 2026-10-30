# Cross-system handoff — Batches 6 and 7

Updated **30 October 2026 (Asia/Kolkata)**. Read this, BATCH-6.md, BATCH-7.md, PAYTM-INTEGRATION.md, AI-EVALUATION.md and AI-DATA-HANDLING.md before continuing. Inspect actual source/tests and Git status; historical guides are descriptions, not proof.

## Git / authorization / scope

- Repository: `https://github.com/hemishsrichandra/Munafa.git`; current macOS checkout `/Users/hemish/Sem-3/Munafa`, branch `main`.
- Pulled GitHub Batch 5 completion **cba2166** by fast-forward, preserving the local whitespace-only report edit in a stash. The report was later normalized for formatting; no substantive owner content was removed. The local stash remains as a backup, not application state.
- Batch 6 checkpoint: **9408088** (`Implement Batch 6: deterministic reconciliation and evidence-linked daily brief`). Batch 7 follows it; `git log -2 --oneline` identifies the final published revision.
- Owner explicitly requested pulling, completing Batches 6 **and** 7 sequentially, a cross-system handoff and committing/pushing before exit. The pasted Batch 8 specification was treated as future context because the request named Batches 6–7. **Do not implement Batch 8 without explicit approval.**
- Preserve PostgreSQL-only persistence, existing six-stage supplier invariants, approvals/idempotency, scoped sessions and IndexedDB conflict handling. No SQLite import/reset, destructive migration, demo reset, real-document upload, automatic messaging or external live provider call was performed.

## Current implementation / boundaries

React 19/Vite and FastAPI/Pydantic remain. PostgreSQL 17, SQLAlchemy Core/Psycopg and Alembic remain the only server persistence path. Migration head **c6ec82a178d3** (following **ec82825043aa** payment tables and **67e38dd313f8** purchase/stock). Startup checks the head; it does not create/seed/import tables.

Batch 5 purchase review, physical receiving, exact append-only inventory and original supplier recovery UI/offline workflow are preserved. Invoice acceptance never adds stock; accepted undamaged physical receiving does. A promise is not recovery; unique proof/reference, applied-confirmed, approval digest/version and remaining-balance checks remain enforced.

Batch 6: immutable payment observations and settlement components; typed internal fixture adapter; demo/live discriminators and store-scoped queries; deterministic net/difference and incomplete/stale/timing/cutoff/correlation explanations; source-linked brief over supplier claims, ledger thresholds, actual expiry and reconciliation exceptions. LIVE is disabled with no webhook ingestion route. Demo import is explicit and administrator/demo-store only. No bank verification, statement import, payment export, customer debt inference or SKU sales inference exists.

Batch 7: narrow provider interfaces, strict billed-field extraction and persistent two-invalid-output budget; minimal AI telemetry; opt-in speech note preview; source/translation review and numeric checks; deterministic cited help with explicitly selected scoped read sources and non-executing follow-up drafts. Manual capture and deterministic retrieval remain defaults. Twelve synthetic invoice fixtures and evaluator are committed. Dedicated OCR options are researched candidates, not integrated or measured providers. No live-provider or human-performance benchmark is claimed.

Key new files: `backend/payments.py`, `brief.py`, `providers.py`, `extraction_schema.py`, `ai_api.py`, `help.py`, `knowledge/product-v1.json`; React `BusinessBrief.jsx`, `Assistant.jsx`; new payment/assistant tests; `evaluation/`, `scripts/evaluate_ai.py`, `build_eval_corpus.py`, `render_eval.cjs`. Existing app/commerce/legacy AI/share/voice screens were adapted incrementally. No new runtime dependency/framework/state library was added in these batches.

## Fresh machine setup

```sh
git clone https://github.com/hemishsrichandra/Munafa.git
cd Munafa
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
npm ci
cp .env.example .env
# Supply private PostgreSQL URLs/credentials and exact APP_ORIGINS in .env.
# Keep APP_ENV=development locally; development demo access is explicit only.
# Provision a new PostgreSQL database (README Docker Compose is supported).
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.manage create-owner
npm run dev
```

On Windows use `.venv/Scripts/python.exe` / `alembic.exe`; npm scripts choose Python cross-platform through `scripts/python.cjs`. Use PostgreSQL, never a fallback database. Configure TEST_DATABASE_URL for a separate test database/schema permission. No credentials, private DB, local draft, APK, SDK, signing key or merchant attachment is in Git. Transfer private data only through an explicit separately approved backup/restore process. Code can be rebuilt without it.

No AI key is required for manual purchase/receiving/stock/recovery, deterministic help or explicit isolated payment demo. `SARVAM_API_KEY` is optional/server-only. `ENABLE_SPEECH_PREVIEW=0` is the safe default; languages remain unvalidated previews. Verify provider retention and terms before any real input. Source-document review dates expire 29 November 2026; maintain/reapprove versioned sources before making current-support claims.

The browser UI is `http://127.0.0.1:5173`; API/built PWA `http://127.0.0.1:8000`. `npm run build && npm start` serves the production PWA; first cache/install/sign-in requires connectivity. Backend static routes require startup after a build. Service worker never broadly caches authenticated API responses. The existing eight-hour verified offline grant, private cache cleanup, durable outbox, leases and explicit conflicts are unchanged. Public product guide can be read with the offline workspace.

## This Mac's local state (not portable)

- Existing PostgreSQL **17.11 Homebrew**, cluster `/private/tmp/munafa-pg-b23-20261030`, log `/private/tmp/munafa-pg-b23.log`, listen `127.0.0.1:55432`, database `munafa_b23`. It was already running; a sandboxed status check falsely could not see it. Elevated verification confirmed its PID/version. No lock file was deleted, new cluster initialized or data reset.
- Ignored private `.env` retains local URLs/demo code. Do not print/commit it. Test suites create fresh random `test_...` / `e2e_...` schemas and clean only their own schemas.
- Private backup `artifacts/private/pre-batch6-postgres.dump`, mode 0600; archive list checked, **restore not tested**. SHA-256 `bc0ea9013ee2b7d1b161671cde5ea2216d96a45f502dc119c35e593b6ca73b53`. It is excluded from Git. Existing Batches 2–5 backups/legacy data remain untouched.
- Current migrations were additive and applied to the development schema. Never downgrade populated tables/import old databases without verified backup and explicit owner approval.

## Verified checks / exact commands

Final backend suite **101 passed** (one existing Starlette/HTTPX deprecation warning); all browser groups **18 passed** (2 commerce + 2 partner + 14 legacy/offline/PWA); IndexedDB **14 passed**. Full backend suite includes empty-schema migration down/up, exact paise/decimal rules, source/stock/recovery regressions, tenant/mode/role isolation, duplicate/out-of-order components, approval/idempotency, invalid AI attempts, timeouts/429, cited/stale/contradictory help, draft permissions and no financial/inventory AI authority.

```sh
npm test
npm run test:offline
npm run test:e2e
.venv/bin/alembic check
.venv/bin/ruff check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py
.venv/bin/ruff format --check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py
npm run format:check
npm run build
```

Production/PWA build, Alembic drift check, Ruff/format, Prettier and diff whitespace checks passed. Remote CI is configured, including evaluator-script lint, but its result has not been claimed. Chromium fallback on this Mac:

```sh
PLAYWRIGHT_EXECUTABLE_PATH=/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell npm run test:e2e
```

Browser evidence checks 320/360/390/430px plus the existing viewport/rotation/PWA tests. New helper cases simulate microphone permission denial and a noisy transcript with explicit start/stop and track disposal; **they are not real microphone/device/provider tests**. Screenshots: ignored `artifacts/test-evidence/batch6-brief-phone.png`, `batch7-help-phone.png`; visually inspected. Public synthetic corpus SVG/PNG files are committed; fixture parser matches 132 annotated slots, not merchant OCR performance. See AI-EVALUATION.md for unmeasured metrics and how to score private provider responses.

## Android / artifacts

Same React frontend, no duplicate domain implementation. `npm run android:sync` and `assembleDebug lintDebug --no-daemon` pass; lint **0 errors / 28 pre-existing warnings**, with Gradle flatDir/SDK XML warnings. Debug APK signature verifies (standard META-INF coverage warnings); packaged public assets byte-match frontend/dist. Debug signing only. No emulator/device or release signing claim.

```sh
npm run android:sync
cd android
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home ANDROID_HOME=/private/tmp/munafa-android-sdk ./gradlew assembleDebug lintDebug --no-daemon
```

Tool paths are temporary and may disappear: Java 21.0.13+9, Gradle 8.11.1, SDK 35. Install permanent tools on another system. Owner previously authorised Google SDK licence acceptance. No additional microphone/location/contact permission is introduced. Native voice is unavailable; use text/touch.

Current APK location `artifacts/munafa-debug.apk` (ignored) and `android/app/build/outputs/apk/debug/app-debug.apk`; final size/checksum is recorded in BATCH-7.md after verification. There is **no hosted HTTPS API configured**. For connected APK testing provide an approved public `VITE_API_BASE=https://HOST/api` and backend exact `APP_ORIGINS=https://localhost`; never put credentials in VITE variables. Without it the bundled shell opens but connected sign-in/AI cannot work.

## Remaining acceptance / next phase dependencies

1. **Live Paytm gate:** official merchant authorisation, API environment entitlement, verified signature/schema/pagination/timezone contract and real E2E. Public settlement APIs state no staging availability. No guessed integration should be enabled.
2. **AI evaluation gate:** authorised credentials, configured provider retention/terms, independently checked consented real-image ground truth, held-out runs for current and dedicated providers, billing evidence and merchant acceptance/correction/time trials. Synthetic/mocked results cannot satisfy these claims.
3. **Voice/language gate:** actual devices, speakers, noise/accents/code-mix/network tests, correction-adjusted touch comparison and consent review. Keep speech disabled until acceptance; no speed claim.
4. **Android gate:** real device install/login/offline cold-start/file/share/Back/process-kill/low-storage/update tests and approved HTTPS backend. Current build is a debug artifact only.
5. **Production gate:** identity/account operations, least-privilege database roles, verified restore, retention/purge, upload scanning and privacy/support review. Source queries are prototype-sized; paginate/profile before scale. AI telemetry has no automatic purge; records persist until approved maintenance.
6. **Batch 8 needs separate approval.** Customer-credit/consent/events, CRM audience permissions, and CA-reviewed accounting exports do not yet exist. Reliable SKU sales history is not supplied by payments; forecast sufficiency/baselines cannot be invented. Staff roles exist but store tasks/checklists do not. Future modules must meet their data/UX prerequisites or show honest disabled states. No P2 procurement/lending/benchmark agents are authorised.
7. Hackathon merchant field validation, presentation and demo video remain separate deliverables. No causal growth, stock accuracy, time-saving or recovery uplift metric is fabricated.

Suggested continuation prompt:

> Pull origin/main, read docs/HANDOFF.md, BATCH-6.md, BATCH-7.md and inspect actual source/tests/Git status. Batches 6–7 prototype code is implemented; live Paytm, empirical provider comparisons, language/device trials and production acceptance remain gated. Preserve all supplier, paise/decimal, audit, approval, tenant and offline invariants. Do not import/reset data. I now authorise [specific next batch or acceptance work]; list files/schema/dependencies/risks/tests before editing. Commit/push and update this handoff before exit.
