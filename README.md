# Paytm Business Partner · Munafa

A phone-first kirana supplier-credit assistant built incrementally from the original Munafa prototype. React 19 + Vite, FastAPI + Pydantic, **PostgreSQL only**, an installable offline app shell, and a Capacitor Android wrapper built from the same frontend.

**AI reads. Rules calculate. The merchant approves.** No live Paytm connection or measured merchant outcomes are claimed.

## Start locally

Requirements: Python 3.11–3.13, Node 20.19+ (or supported Node 22), and PostgreSQL 17. Docker Compose is optional.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
npm ci
cp .env.example .env
```

Fill in private PostgreSQL values and a `postgresql+psycopg://...` DATABASE_URL. Use a dedicated TEST_DATABASE_URL for testing. Generate your own credentials; never commit `.env`. For local HTTP development, set APP_ENV=development and APP_ORIGINS=http://127.0.0.1:5173,http://127.0.0.1:8000; keep ALLOW_DEV_LOGIN=0 unless deliberately using the isolated demo.

For Compose, set POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in `.env`, then:

```sh
docker compose up -d postgres
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.manage create-owner
npm run dev
```

Open [the development UI](http://127.0.0.1:5173). Sign in using the owner account created by the CLI. API contracts are available at [the local API documentation](http://127.0.0.1:8000/docs). Browsers need APP_ORIGINS to include the actual frontend origin.

PWA/service-worker behavior is tested on the **production build**, not the Vite development server:

```sh
npm run build
npm start
```

Open [the built application](http://127.0.0.1:8000). Restart the backend after the first build so it registers static assets.

### Explicit development demo

Only for development: set APP_ENV=development, ALLOW_DEV_LOGIN=1, and a private DEV_LOGIN_CODE with at least 16 characters. Run `.venv/bin/python -m backend.manage seed-demo`, then use **Development demo access** on the login screen and enter that code. This creates a separate demo store and a synthetic A-104 case if empty. It does not reset anything. All input in that store remains synthetic.

Production refuses to enable development login. Production cookies require HTTPS. There is no Paytm SSO or OTP integration.

## Current product

- Home: deterministic, source-linked daily brief over recorded supplier claims, merchant SKU thresholds, actual expiries and labelled reconciliation exceptions. Unavailable payment data is not zero activity.
- Purchases & stock: reviewed purchase records, independent partial/final physical receiving, exact stock ledger, SKU thresholds/batches/expiry and linked original supplier recovery. Invoice acceptance alone never changes stock.
- More: payments/reconciliation, cited merchant help and reviewed language drafts, supplier balances, recovery export, workflow guide and account controls.
- Drafts & sync: IndexedDB manual invoices/receiving notes/attachments, durable dependency-ordered outbox and explicit server-accepted/conflict states.
- Merchant-confirmed received quantities, units, delivery completeness and effective prices remain mandatory.
- Integer-paise claim calculation; exact decimal quantities use NUMERIC(20,6), HALF_UP rounding to paise per line. The phone editor preserves fractional quantity strings up to six decimal places; prices are converted from decimal input to paise without floating-point rounding.
- Partial/full credit and refund records require case-owned proof. Duplicate references and identical proof bytes cannot be counted twice.
- Immutable approval snapshots and append-only audit/financial/resolution records.
- Server-derived store scope, owner/staff/viewer permissions, CSRF-bound cookie sessions and transactionally idempotent writes.
- Ledger export requires a server-approved export action. WhatsApp sending remains manual.

Payments use explicitly loaded synthetic fixtures in isolated demo stores; live Paytm is disabled. Source-grounded help uses curated versioned product/technical material, with scoped optional merchant facts. No customer-credit, forecast or live analytics module exists. Manual stock/sale entry requires actual source records and approval; payments never imply SKU sales.

## PWA behavior

Choose **Install app** for supported-browser prompting or platform-specific guidance. First installation/cache warm-up needs connectivity. After warm-up, the static shell can reopen offline. First sign-in, server records and AI require a connection. A previously verified workspace can reopen device drafts offline for eight hours.

The service worker caches only the public shell and versioned assets. It does not cache `/api` responses, attachments, tokens or merchant records. Logout stops sync and clears private IndexedDB data after a warning, plus workspace memory and non-shell caches. Offline logout leaves server revocation pending until connectivity returns. Updates wait for explicit confirmation and warn about unsaved form input.

**IndexedDB drafts and sync are now available through Drafts & sync.** Save a local draft, then explicitly queue it. Purchase/receiving capture, attachment upload and eligible explicitly confirmed stock operations use the existing versioned outbox. Local values remain provisional until accepted; stale versions require review. Credits/refunds, exports and sending are not silently queued. Direct actions outside this workspace are never silently queued. Hindi/Kannada selection currently previews navigation labels; workflow text remains English and is explicitly labelled as not fully reviewed.

## Sarvam integration

Optional server-only settings:

```dotenv
SARVAM_API_KEY=your-private-key
SARVAM_CHAT_MODEL=sarvam-105b
SARVAM_VISION_MODEL=gemma4
```

Pasted-text extraction uses native Sarvam chat; image extraction uses Sarvam-hosted Gemma; Hindi/Kannada message translation uses Mayura. AI-proposed receiving counts are discarded. Provider endpoints and failure paths have mocked contract tests. **Live account access, credits, accuracy and latency remain unverified.** Manual entry is the default. Two invalid structured outputs stop extraction for that source; original documents are preserved. Speech is an opt-in unvalidated note preview (`ENABLE_SPEECH_PREVIEW=0` by default), never automatic physical quantity entry. Translation is reviewed before copy/share; help cannot mutate business truth. No API key is bundled in the PWA or Android assets.

## Tests

```sh
npm test
npm run test:offline
.venv/bin/ruff check backend
npm run format:check
npx playwright install chromium
npm run test:e2e
```

The Python fixtures create unique disposable PostgreSQL schemas. The browser server creates a separate `e2e_...` schema. Both require TEST_DATABASE_URL; neither falls back to another engine. Test teardown only removes its generated schema. Do not use a production database account for tests.

The browser suite additionally tests offline draft reload, actual client timeout after server acceptance, duplicate-proof attachment retry, quota failure, expired session, account switch and receiving conflicts. It also exercises the original shortage-to-recovery loop, phone manual intake, 360×800, 390×844, 430×932, 320px narrow screens, rotation, dialogs, bottom-nav touch targets, manifest/worker metadata, private-cache exclusion and offline shell launch. Physical-device installation and native behavior are separate validation steps.

## Android: same React application

Capacitor 7.6.10 wraps `frontend/dist`. The Android project contains no separate product screens or financial rules. Its development package identifier is `in.munafa.businesspartner`.

```sh
npm run android:sync
npm run android:check
npm run android:debug
```

A debug build requires **JDK 21**, Android SDK Platform 35, Build Tools 34/35 and accepted Android SDK licenses. Set JAVA_HOME and ANDROID_HOME to your local installations. The output is `android/app/build/outputs/apk/debug/app-debug.apk` after a successful build. Install with `adb install -r android/app/build/outputs/apk/debug/app-debug.apk` on an explicitly connected development device.

For a connected native build, set the public **VITE_API_BASE=https://YOUR_HOST/api** before building, and add the exact native origin `https://localhost` to the backend APP_ORIGINS after reviewing your deployment. Cleartext networking and Android backups are disabled. Native session tokens are memory-only and require sign-in after process restart. They are not stored in localStorage/IndexedDB or bundled assets.

Without a configured HTTPS backend, the APK deliberately presents the shell and a clear connectivity/configuration error; it does not invent records. The packaged shell opens offline without a service worker. No microphone/location/contacts permission is requested. Existing system file selection is retained; private downloads use authenticated requests and a temporary app-cache file with an explicit OS share sheet. Camera capture, sharing, downloads and native navigation still need real-device validation.

This is not a release-signed APK setup. No production signing key, deployment endpoint, emulator or physical-device coverage is claimed. See [Batch 4 report](docs/BATCH-4.md) for current build results; [Batch 3](docs/BATCH-3.md) records the initial wrapper validation.

## Data safety and architecture

See [Batch 2](docs/BATCH-2.md) for schema, authentication, migration and backup/restore details, and [architecture](docs/ARCHITECTURE.md) for module boundaries.

Legacy `.data/*.db` files are untouched archives. They are never opened by the current app/tests. There is no automatic importer and the former reset command refuses deletion. Any real-data import or destructive migration requires verified backup and explicit owner approval.

For a new session, start with [resume context](docs/HANDOFF.md). See [progress](docs/PROGRESS.md), [demo instructions](docs/DEMO.md) and [remaining roadmap](docs/ROADMAP.md). Batch 5 adds purchase capture, separate physical receiving, stock, expiry and offline commerce drafts; see [Batch 5](docs/BATCH-5.md). The owner authorised pushing this completion to origin/main; consult the handoff and `git status` for the current revision.

## Offline data safety

IndexedDB data is scoped by verified user/store/role. Cached receiving sources expire in 24 hours; accepted draft copies expire seven days after sync. Unsynced drafts are retained until explicit discard/sign-out; automatic retries pause after five attempts or 30 days. A timeout does not prove rejection: retries preserve the exact operation ID/body and PostgreSQL replays its receipt.

Browser/WebView storage is **not encrypted by this app** and can be evicted or cleared. Keep original documents and deliberately back up important drafts. JSON draft backups do not contain attachment bytes. No device-level encryption, guaranteed persistence, background delivery or cross-device recovery of unsynced drafts is claimed. See [sync protocol and threat model](docs/SYNC-PROTOCOL.md).

## Batches 6 and 7 / continuing on another system

Read [HANDOFF.md](docs/HANDOFF.md), [Batch 6](docs/BATCH-6.md), [Batch 7](docs/BATCH-7.md), [Paytm integration gate](docs/PAYTM-INTEGRATION.md), [AI evaluation](docs/AI-EVALUATION.md) and [AI data handling](docs/AI-DATA-HANDLING.md). Apply migrations with `alembic upgrade head`; no automatic import/reset is performed. No API key is needed for manual purchase/stock/recovery, deterministic help or the synthetic payment demo.

To demonstrate Batch 6, sign in to an isolated demo store, explicitly create a SKU with a merchant-defined threshold, then open More → Payments & reconciliation → Load isolated synthetic payment demo. Home then shows source-linked stock and reconciliation actions. Fixture amounts are deliberately inconsistent by ₹8.20 after documented fees/GST/refund components; review is required and no missing-money claim is made.

For Batch 7, open More → Merchant help & language, ask about receiving/offline/recovery and optionally select your own case/SKU/brief source. Source citations and database facts are separate. Missing/stale/unsupported questions abstain. Optional cloud extraction and translation are explicit drafts; the offline product guide remains bundled. Real providers, speech accuracy and Android hardware still require external acceptance tests.

## P2 readiness (Batch 9)

More → **Planning readiness** shows the three default-off P2 gates, current store-scoped source counts and links to your own SKU movement history. The optional `ENABLE_P2_PROCUREMENT`, `ENABLE_P2_FINANCIAL_PLANNING` and `ENABLE_P2_BENCHMARKING` flags default to `0`; setting `1` cannot supply missing prerequisites or enable external execution. No purchase order, financial/credit decision, lender checklist/application or peer result is generated. Read [the Batch 9 evidence status and risk register](docs/BATCH-9.md). Relevant P1 source quality, verified supplier offers, complete financial ledgers, an authorised lender process and approved cohort controls remain blocked prerequisites. Batch 8 has not been implemented.

## Final integration / demo candidate (Batch 10)

See [release verification and limitations](docs/BATCH-10.md), [four-minute demo and safe reset instructions](docs/DEMO.md) and [cross-system handoff](docs/HANDOFF.md). Batch 10 adds security fixes and integration coverage, not merchant features. Vite is patched to 6.4.5; use `npm ci` with the updated lockfile. Run builds before backend collection, then tests sequentially. `npm run test:e2e` builds with a forced same-origin API so a local live API setting cannot receive test traffic.

The optional restore rehearsal needs supported `pg_dump`/`pg_restore` on PATH or `PG_BIN` and a disposable PostgreSQL test role with CREATE DATABASE privileges. It backs up only its generated synthetic test schema, restores into a newly created scratch database, compares counts/content hashes and cleans only its own objects. Do not grant production application roles extra privileges for this test. Missing client binaries produce an explicit skip, not a successful restore claim.

No real Android device/emulator, OS install, live Paytm, measured cloud OCR/speech/translation or production legal/security certification is claimed. P1 modules remain absent and P2 execution stays gated. No application database reset or real-data import was performed.

## Post-playbook extension status

More → **Connections & readiness** now shows honest provider blockers, accepted-source preparation with exact-payload local export approval, and SKU data-readiness reports. Private offline pilot and forecast-baseline analysis tools are documented in [the evaluation protocol](docs/EVALUATION-AND-PILOT.md). All three extension batches were processed sequentially; live integrations, CA review, representative AI evaluation and a real kirana pilot remain blocked by unavailable access/participants. No external sending, submission, forecast or peer result is enabled. See [all 47 acceptance gates and test evidence](docs/POST-PLAYBOOK-STATUS.md) and [the current cross-system handoff](docs/EXTENSION-HANDOFF.md).

Latest: [final owner checklist review](docs/FINAL-CHECKLIST-REVIEW.md) — all 31 checks, fresh test results, synthetic website scenario, remaining gaps and required credentials/decisions.
