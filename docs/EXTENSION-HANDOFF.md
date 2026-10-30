# Cross-system handoff — post-playbook extensions

**Latest continuation:** read `docs/FINAL-CHECKLIST-REVIEW.md` first. The final owner checklist review now has 246 backend tests (one added exact-money audit/evidence regression), 22 browser and 17 frontend tests passing. Three float-format strings in `backend/app.py` now use the existing Decimal `rupees()` formatter. The current development demo store has a synthetic reviewed ₹200 invoice, explicit 2 kg receipt, ₹40 open approved claim, ₹0 recovery and isolated settlement fixture. No messages sent; no existing records reset. The website seed lives only in local PostgreSQL and must be recreated safely on another machine. No new migrations/dependencies. Current provider/data/device gates remain unchanged.

Updated 30 October 2026, Asia/Kolkata. Repository `hemishsrichandra/Munafa`, branch
`main`. Read actual source/Git status before changing anything. The owner explicitly
authorised all three attached extension batches sequentially. No further external
messaging, real-data import/reset, submissions or pilot recruitment is authorised
by the existence of this handoff.

## Read first

1. `docs/POST-PLAYBOOK-PLAN.md`: archived complete owner-supplied extension plan.
2. `docs/POST-PLAYBOOK-STATUS.md`: **all 47 acceptance gates**, actual pass/blocker
   scope, commands and final evidence. These are three _extension_ batches, not a
   rerun of the master ten batches.
3. `docs/EXTENSION-1.md`, `EXTENSION-2.md`, `EXTENSION-3.md`: per-batch completion
   reports. `docs/EVALUATION-AND-PILOT.md`: measurement protocol/metric sheet.
4. `docs/HANDOFF.md`: historical Batch 10/local setup details; current test counts
   and APK supersede that historical release. `docs/DEMO.md` still describes the
   existing synthetic outcome-centred demo.

## Actual status and Git checkpoints

- Previous published Batch 10: `84a6ecf`.
- Extension 1: `573470c` — internal contracts, honest authenticated connection
  readiness, phone UI, exact rupee parsing/device unavailable semantics/tests.
- Extension 2: `083945d` — accepted-source local preparation, source hashes,
  deterministic purchase totals, central exact-payload local-export approval.
- Extension 3/final verification: use `git log -1 --oneline` for its published
  checkpoint; report/tools/readiness plus final export retry/exact preview fixes.
- Owner explicitly answered **no** to authorised Paytm/device/WABA/lender/GST access,
  qualified CA reviewer or consented kirana pilot. Do not keep asking the same
  question or invent successful integration. No live provider connection exists.
- Existing master-playbook discrepancy: Batch 8 P1 modules remain absent and P2
  execution is readiness-only. Do not describe the master ten as fully accepted.
  Scope the smallest source-ledger/consent repair separately before dependencies.

Implemented: More → **Connections & readiness**, source-linked local preparation
with exact JSON preview and merchant approval before export, SKU data readiness,
private offline forecasting-baseline/pilot analysis and protocols/tests. No new
tables/dependencies/migrations. Alembic head remains `c6ec82a178d3`.

Blocked: all live connectors, real WABA delivery receipts, lender/filing consent
and submission, CA review, real AI quality/cost comparison, forecasts, cohort
releases and real merchant outcomes. Do not mark suppression as a working model.

## Implementation boundaries

- `backend/integrations.py`: **internal**, versioned types, not verified provider
  wire schemas. No public webhooks/sends; connector fails closed. Existing
  `payments.py` remains the only payment ingestion/reconciliation path.
- `backend/preparation.py`: immutable accepted purchase snapshots only, selected
  source IDs/versions/document hashes, up to 367 days/100 records, explicit missing
  tax-field exceptions. No inferred unpaid balance, GST applicability or lender
  checklist. JSON local export; no document bytes/customer phones/provider secrets.
- `backend/actions.py`, `app.py`: added `export_preparation`; exact digest/version,
  existing 15-minute expiry, permissions and creator/approver rechecked. Download
  uses repeatable-read and current source validation. Keep new handler or expire
  outstanding proposals if rolling back UI/backend. Never delete audit snapshots.
- `backend/intelligence.py`: own-store accepted source counts, observed sales days
  explicitly incomplete, unknown gaps/stockouts, threshold labelled a rule. No
  forecasting activation, universal readiness threshold or cross-store query.
- `scripts/evaluate_forecast.py`: one-unit contiguous confirmed daily data,
  explicit training length/holdout, frozen predictions, exact-decimal baseline
  MAE, stockout/gap rejection. Does not promote models/place orders.
- `scripts/analyse_pilot.py`: private pseudonymous inputs, purpose/version/window,
  duplicates/replays/withdrawal/expiry handling, correction time, negatives and
  follow-up-qualified repeat use. No inputs → unavailable, not zero impact.
  Structural consent validation is not legal evidence. Outputs mode 0600,
  exclusive creation, no raw values in validation errors. No server consent or
  deletion/collection service exists; human-controlled private analysis only.
- Frontend uses existing React/Vite/components/CSS, PWA and native same build.
  No new private offline cache; preparation/readiness require connection. Existing
  offline purchase/receiving/evidence drafts and outbox remain authoritative.

## Reproduction and latest verification

See historical handoff for installing PostgreSQL/Python/Node. Use PostgreSQL only,
safe `.env.example` and explicit migrations; never SQLite fallback/startup create-all.
Private `.env`, databases, build SDKs, reports and APK are **not in Git**.

Local PostgreSQL **17.11**, `127.0.0.1:55432`, database `munafa_b23`; temporary cluster
`/private/tmp/munafa-pg-b23-20261030`. Do not reset it. Test fixture creates/drops only
random `test_*`/`e2e_*` schemas; restore test creates only its new scratch database.
Use a disposable test role/database, never grant production roles CREATE DATABASE.

```sh
npm ci
.venv/bin/pip install -r backend/requirements-dev.txt
npm run build
PG_BIN=/opt/homebrew/opt/postgresql@17/bin RELEASE_EVIDENCE_DIR=artifacts/test-evidence npm test
npm run test:offline
npm run test:e2e
.venv/bin/alembic check
npm run format:check
.venv/bin/ruff check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py scripts/audit_release.py scripts/analyse_pilot.py scripts/evaluate_forecast.py
.venv/bin/python scripts/audit_release.py
```

Build **before** backend collection/server startup; don't run builds concurrently
with backend import/serving. Browser helper rebuilds with same-origin API, disables
cloud keys/P2 flags and uses disposable PostgreSQL namespaces. On this machine set
`PLAYWRIGHT_EXECUTABLE_PATH` to
`/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell`;
other machines should install Playwright Chromium. No live provider tests are run.

Latest complete run: **245 backend / 22 browser / 17 frontend tests PASS**, 0 skipped.
After the full browser run, a final full-payload preview enhancement also passed
the focused `npx playwright test tests/e2e/extension.spec.js` case. Ruff, formatting,
build, schema drift, compile, Node syntax and dependency compatibility pass. npm
audit: zero known findings at check; Python CVE scanner unavailable/not run.
Existing Starlette warning remains. Remote CI status is not assumed.

Ignored local evidence: `artifacts/test-evidence/extension-readiness.png`,
`extension-android.json`, `extension-ai-unmeasured.json`,
`extension-pilot-not-run.json`, release source audit, existing restore/performance
artifacts. Six held-out synthetic invoices have **zero provider-measured runs**;
human timings/precision/recall/costs remain null. No merchant pilot data exists.

## Android and device gates

`npm run android:sync` packages the same frontend. Licensed SDK already accepted by
owner. Temporary JDK/SDK may disappear; install equivalents on a new machine:

```sh
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home ANDROID_HOME=/private/tmp/munafa-android-sdk ./android/gradlew -p android assembleDebug lintDebug --no-daemon
```

Build/lint/signature verification and packaged-public-asset equality passed. Current
APK details are in `POST-PLAYBOOK-STATUS.md` and the ignored JSON evidence. Debug APK
at `artifacts/munafa-debug.apk`, not committed or release-signed. Lint has 0 errors,
0 fatal issues and 28 existing warnings. Signature tool reports existing META-INF
coverage warnings. Capacitor doctor succeeds for installed 7.6.10; latest-version
lookup is unknown, not proof of current upstream version. No device/emulator was
connected. No real OS installation/native camera/share/process-lifecycle claim.

Configure an authorised HTTPS `VITE_API_BASE=https://HOST/api` and matching backend
origins before native sign-in. This is a public URL, never a provider secret. With
no backend configured the bundled shell opens offline but cannot sign in. Do not
bundle a temporary loopback development URL as a working mobile backend.

## Next work, in dependency order

1. Obtain authorised exact provider packs and assign integration owner. Confirm
   merchant/product/device identities, environments, scopes, versions, signing,
   retry/pagination and rate limits before code. Complete typed verified mappings,
   durable authenticated inbox, polling cursors and contract tests. No guessed URLs.
2. For WABA implement purpose-bound contact permission/revocation, exact recipient/
   content approval, ambiguous timeout and real status-history handling before send.
   Current manual WhatsApp handoff is not delivery evidence.
3. Have a qualified CA review the preparation format. Scope source-field repairs
   (GSTIN/HSN/place-of-supply/tax components) with provenance, review and migration
   tests. Identify lender/product/checklist and approved disclosures/consent/
   retention; application/filing remain disabled until official contracts/tests.
4. Repair missing relevant P1 sources only under a scoped plan; do not infer debt
   or SKU sales from payment totals, accepted bills or merchant names.
5. Appoint pilot/data/privacy leads; approve notices, representative permissioned
   corpus, annotation/adjudication and numerical holdout thresholds before tests.
   Run actual kirana baseline/comparison, capture correction effort, negative
   outcomes and qualified follow-up. Reports must retain null/unavailable unknowns.
6. Forecast only after reliable SKU observation calendar/units/censoring and
   baseline evidence. Peer comparison requires a separate approved analytical
   path, legal purpose, cohort suppression and re-identification review. No client
   claim of cohort size/consent can bypass it.
7. Test real Android hardware, accessibility and authorised HTTPS deployment;
   production identity/account ops, encryption/retention/deletion, malware scanning,
   distributed limits, backups, release signing and security/legal review remain.

Preserve append-only inventory/finance, exact paise/fractional arithmetic, tenant
scope, snapshot approvals, idempotency and six-stage Munafa. Stop for explicit owner
approval before any destructive real-data migration/import/reset with verified
backup and a concrete plan. Commit/push useful checkpoints and update this handoff
before leaving the usage window; never fabricate completion to meet a deadline.
