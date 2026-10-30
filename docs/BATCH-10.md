# Batch 10 — integration, hardening and demo candidate

30 October 2026 · baseline `4e7fcb9` · PostgreSQL head unchanged: `c6ec82a178d3`.

## Release decision / standard completion report

**Local synthetic demo candidate, with explicit external acceptance gaps. No new merchant product feature was added.** Purchase/physical receiving/stock/supplier recovery, IndexedDB/outbox, deterministic settlement simulation, manual AI fallback, cited help and P2 safety gates are integrated. Batch 8/P1 modules and interactive store selection remain absent; live Paytm, provider field evaluation and actual Android device acceptance are not supplied. This is not a production-ready, live-integrated, revenue-lifting, fraud-preventing or legally certified release.

### What changed and why

- Stream request bodies with a hard bound before allocating the full payload/database work; retain the existing 9 MB API limit and apply a 16 KB auth-body limit. Invalid declared lengths fail safely. Multipart originals still use 8 MB and offline attachments 4 MB limits. Chunked/no-Content-Length oversize requests are tested.
- Redact submitted values from FastAPI/Pydantic validation errors; nested invalid proposals receive a safe 422. Catch malformed decimal conversion as validation failure instead of an unhandled exception. Existing exact decimal/paise rules remain.
- Keep CSV source checking and rendering in a PostgreSQL repeatable-read snapshot, preventing a concurrent new/edited case from mixing into an approved export. Escape formula prefixes including whitespace/control prefixes; render paise through exact decimal formatting.
- Render missing amounts as Not recorded and format integer-paise cents without floating division, including large safe integers; invalid/out-of-range display inputs are explicit unavailable states. Backend ledger calculations are unchanged.
- Preserve the actual request idempotency key on accepted inventory/receipt events, rather than generating a separate provenance ID. Exact replay and approval guards remain server-side.
- Reject obvious active/embedded PDF tokens as unsupported on new uploads. This is **not antivirus, structural PDF validation or content disarm**; arbitrary/encoded malicious content is not proven safe. Originals are not silently rewritten. MIME/signature/size and malicious HTML/SVG/PDF cases are tested; production scanning remains required.
- Avoid mounting an incomplete Vite output directory at API import. Rehearsal builds/tests are still sequenced to avoid rebuilding assets while serving them.
- Improve contrast for small supporting labels/metrics, darken focus indication, and use 16px phone form text. Correct reverse-tab containment from the dialog root and disable close controls during protected busy operations rather than leaving an enabled no-op. Replace hard-coded profile initials with actual store initials. Existing UI/framework/CSS system remains.
- Patch **Vite 6.4.1 → 6.4.5** and transitive **source-map-js 1.2.1 → 1.2.2**; React/framework direction unchanged. Lockfile clean install verified. Initial npm audit reported two high package findings; final npm audit reports zero known findings as of this check. Sources: [Vite advisory](https://github.com/vitejs/vite/security/advisories/GHSA-p9ff-h696-f583), [patched release](https://github.com/vitejs/vite/releases/tag/v6.4.5), [source-map-js advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q). This is not a guarantee of vulnerability absence.
- Isolate browser test builds to a same-origin API (`VITE_API_BASE` empty) and explicitly force synthetic test-server flags/cloud keys off. Add a separate release test group so the existing real login limiter is preserved. New `scripts/audit_release.py` reports known-secret-value matches, SQLite imports, production debug controls and API inventory without printing secret values or file contents.

No migration, real-data import, application reset, framework/state-library replacement, provider credential, automatic message, order, credit application or tax filing was added. Scope is fixes, tests and documentation.

## A. Test matrix and exact commands

Final measured counts/results are also recorded in HANDOFF.md. Run builds before tests that import backend.app; never rebuild one dist concurrently with API startup/serving.

| Check                                              | Status / evidence                                                                   | Exact command                                                                                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Locked Node install                                | PASS; security patch versions pinned                                                | `npm ci`                                                                                                                                                                                 |
| Backend PostgreSQL suite, including restore        | PASS: 210 passed, 0 skipped; existing Starlette warning                             | `PG_BIN=/opt/homebrew/opt/postgresql@17/bin RELEASE_EVIDENCE_DIR=artifacts/test-evidence npm test`                                                                                       |
| IndexedDB/outbox unit tests                        | **17 passed**: 14 IndexedDB/outbox + 3 exact-money display tests                    | `npm run test:offline`                                                                                                                                                                   |
| Full browser/PWA/desktop/tablet/phone suite        | **21 passed, 0 skipped**; Chromium, synthetic stores                                | `PLAYWRIGHT_EXECUTABLE_PATH=/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell npm run test:e2e`              |
| Fresh migrations / rollback / restore              | PASS in disposable PostgreSQL only                                                  | Backend `test_migration_down_up_on_empty_disposable_schema` and `test_postgresql_backup_restore_rehearsal_only_disposable_objects`                                                       |
| Metadata drift                                     | PASS; no new DDL expected                                                           | `.venv/bin/alembic check`                                                                                                                                                                |
| Python lint / format                               | PASS on changed/relevant source                                                     | `.venv/bin/ruff check backend scripts/serve_e2e.py scripts/build_eval_corpus.py scripts/evaluate_ai.py scripts/audit_release.py`; same paths with `ruff format --check`                  |
| Frontend/docs format                               | PASS                                                                                | `npm run format:check`                                                                                                                                                                   |
| Python syntax / JS syntax / JSX build              | PASS; no configured TypeScript type checker                                         | `.venv/bin/python -m compileall -q backend scripts`; `node --check scripts/browser-tests.cjs`; `node --check scripts/build-pwa.cjs`; `node --check frontend/src/api.js`; `npm run build` |
| Python installed dependency compatibility          | PASS; not a vulnerability audit                                                     | `.venv/bin/python -m pip check`                                                                                                                                                          |
| Python vulnerability scanner                       | SKIPPED: pip-audit is not installed; do not treat compatibility as CVE verification | `.venv/bin/python -m pip_audit --version` reports module unavailable                                                                                                                     |
| npm advisory scan                                  | PASS at run time: zero known findings after patches                                 | `npm audit --json`                                                                                                                                                                       |
| Known-value secret / debug / SQLite import audit   | PASS; limited scope, see privacy section                                            | `.venv/bin/python scripts/audit_release.py`                                                                                                                                              |
| Android wrapper doctor/build/lint/signature/assets | Final artifact evidence below                                                       | `npm run android:check`; `npm run android:sync`; Gradle/signature commands below                                                                                                         |
| Actual Android/emulator tests                      | SKIPPED: `adb devices -l` returned no devices                                       | `/private/tmp/munafa-android-sdk/platform-tools/adb devices -l`                                                                                                                          |
| OS PWA installation / real camera / screen reader  | SKIPPED: no device/OS assistive-technology session                                  | Browser metadata/input-file/keyboard checks are not device acceptance                                                                                                                    |
| Live Paytm / real Sarvam / real messaging          | SKIPPED: no authorised end-to-end contracts/access                                  | Live gates remain closed; mocks are identified as mocks                                                                                                                                  |
| Interactive store selector                         | NOT IMPLEMENTED; no new feature added                                               | Verified session determines one active store; spoofed tenant inputs/headers cannot change it                                                                                             |
| P1 modules / P2 execution                          | ABSENT or safely BLOCKED, not passing business features                             | Module matrix below; Batch 9 gate tests remain                                                                                                                                           |

The new release suite enumerates every private API operation from OpenAPI (57 private operations out of 60 total at this baseline) for unauthenticated denial. The synthetic image matrix exercises all 12 labelled corpus images with keys absent: originals preserved, draft/manual fallback, no stock/financial acceptance. Good/malformed/adversarial provider schemas, timeout/429, review, translation mismatch, simulated speech denial/noisy transcript and grounded help are separately tested. Neither corpus fallback nor mocked responses measure live OCR accuracy.

The connected end-to-end journey also asserts no unexpected application console errors (expected unauthenticated `/auth/me` HTTP 401 diagnostics are distinguished from application failures); page-error checks cover unhandled frontend exceptions. This is not a whole-browser/OS logging audit.

Earlier new-test failures were investigated and corrected: incorrect UI selectors, a read issued before asynchronous approval completed, and selecting form labels before opening the manual-entry tab. Assertions/contrast thresholds were retained. The invalid-decimal error, streaming-body allocation risk and reverse-tab/busy-close issues were fixed in product code. No existing test was deleted or weakened. The restore test explicitly skips when suitable pg_dump/pg_restore tools are unavailable; this must never be reported as a successful restore.

## B. PWA and Android

PASS in Chromium: manifest/icons/worker metadata, cache warm-up, authenticated API exclusion from shell cache, saved-device invoice/receiving/attachments, offline reload, retries after lost acceptance, visible conflicts, quota/session errors, account/logout cleanup, phone viewports 320/360/390/430px and tablet/desktop/rotation cases. Service-worker shell needs a prior connected warm-up; dynamic API, remote AI and first sign-in do not work offline. OS installation acceptance, eviction/process-kill behavior and native background delivery are not established.

Android uses the same frontend build and domain rules. No microphone/location/contacts permissions were introduced. `adb devices -l` returned an empty list; **no real device or emulator test ran**. Debug signing only; no release signing, Play Store approval or hosted HTTPS API was configured. Without an approved public VITE_API_BASE and backend native origin configuration, the APK opens its shell but cannot perform connected sign-in.

```sh
npm run android:sync
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home ANDROID_HOME=/private/tmp/munafa-android-sdk ./android/gradlew -p android assembleDebug lintDebug --no-daemon
JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home /private/tmp/munafa-android-sdk/build-tools/35.0.0/apksigner verify android/app/build/outputs/apk/debug/app-debug.apk
```

These are this Mac's temporary SDK/JDK paths; install permanent tools on another system. Signature warnings and lint counts/checksum are captured with the final artifact evidence, not interpreted as release readiness.

## C. PostgreSQL only / migration and restore

Runtime driver is strictly `postgresql+psycopg`; no runtime/test/fallback SQLite import or local SQL database was introduced. Source AST audit reports zero SQLite imports. Application startup checks Alembic head and does not create-all, seed, reset or auto-import. Browser private offline data uses IndexedDB.

Fresh generated test schemas migrate to `c6ec82a178d3`; empty-schema downgrade/up and drift checks pass. The backup/restore rehearsal uses a randomly owned synthetic test schema, pg_dump archive, verified archive contents, and a separately created **new disposable database**. It compares row counts and canonical content hashes across **32 application tables**, verifies 8000 paise of synthetic recovery and 2 kg recorded stock, checks key indexes/validated constraints and cleans only its own generated objects. It never restores over the configured application database. Local archive is private; only non-sensitive result metadata is in ignored `artifacts/test-evidence/postgres-restore.json`.

This validates the synthetic restore path, **not restoration of a real merchant backup**. Before real production import/restore/downgrade/reset: verified backup, reviewed exact plan and explicit owner approval remain required. Least-privilege production roles, encrypted backups and restore-time objectives are still operational work.

## D. Security / tenancy / privacy

- Principal/store derives from verified session. All private endpoints reject anonymous access before body validation. Valid-body cross-store tests cover case review/approval/share/promise/proof/resolution/message/snapshot, purchase/document/receiving, SKU/conversion/movement, actions and export/payment details; collection/brief/usage/planning/sync isolation is also tested in the domain suites.
- Same-store users may read collaborative records according to role; this is intentional store scope, not per-user document ownership. Actor-bound operation receipts cannot be replayed by another user, and a private export approval cannot be downloaded by another user. Extra tenant fields and spoofed store headers grant no context switch. Interactive store switching remains unavailable.
- Role denial, CSRF/origin checks, expired sessions, actual HTTP login rate limit, payload-digest/version/expiry checks, idempotency/concurrent retry, immutable financial history, unique proof/reference and applied-confirmed recovery gates remain tested. Rate limits are in-process, not a distributed production quota service.
- Account/logout changes clear private IndexedDB/cache and stop old-context sync; tests cover both account/role scope purge and durable draft conflict/retry. Offline logout may defer server revocation; same-origin storage is not app-encrypted and eviction can lose unsynced drafts. No guaranteed Background Sync is claimed.
- Source/bundle audit checks current tracked/new source and production assets against actual private config values and key-material patterns; it reports zero matches and production sync-debug controls absent. This is not a full repository-history secret audit or semantic PII classifier. No analytics SDK was found in app source. Local test/provider mocks contain labelled dummy credentials; real `.env`, private backups/documents, APKs and logs remain ignored.
- Provider keys remain server-side. Rehearsals force cloud keys off and same-origin APIs. Raw audio is not retained by the app; provider-side retention must be verified in the actual account. Invoice originals, operation receipts and audit have no complete deletion/retention administration flow; do not promise deletion compliance. Supplier messages are reviewed manual handoffs, not delivered-message receipts; no customer CRM/consent ledger exists.
- MIME/signature/size and obvious active-PDF checks are limited defenses, not malware certification. Production file scanning, deployment TLS/CSP review, per-environment identity, breach/retention/consent procedures and qualified legal/security review remain required. No compliance certificate is claimed.

## E. Working / demo / disabled integration matrix

| Module                                            | Actual status / prerequisite                                                                                                                                                       |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Purchase capture/review                           | Working manual/text/file/sample intake; cloud extraction optional proposal, manual fallback; merchant confirmation required                                                        |
| Physical receiving / stock                        | Working partial/final receiving and exact append-only ledger; no stock from invoice alone; SKU sales require explicitly recorded merchant/POS evidence, no payment-sales inference |
| Supplier recovery                                 | Working six-stage workflow, deterministic shortage, immutable snapshot, manual share handoff/promise and evidence-backed partial/full application gates                            |
| Offline PWA/outbox                                | Working in tested Chromium; first cache/sign-in online, explicit server acceptance/conflicts; native durability/eviction not proven                                                |
| Payment/settlement reconciliation                 | Working deterministic **synthetic demo** adapter; unknown fields are not zero; LIVE disabled, no bank verification/statement-import feature                                        |
| Daily brief                                       | Working source-linked deterministic own-store queries; no padded recommendations or invented analytics                                                                             |
| AI extraction / translation                       | Optional server adapters and strict/mocked tests; real provider accuracy/cost/retention/contract evaluation unverified                                                             |
| Voice                                             | Disabled by default, optional unvalidated note preview; denial/noisy transcript tests simulated; actual device/language matrix not run                                             |
| Grounded help                                     | Working curated versioned source retrieval + scoped selected store facts; no direct model mutations; unsupported/stale sources abstain                                             |
| P1 receivables/CRM/forecast/fraud/GST/staff tasks | **Absent** (Batch 8 not executed); no fake active tiles or operational results. Membership roles alone do not implement staff operations                                           |
| P2 procurement / finance/lender / peer comparison | Readiness checks work; actual capabilities disabled/blocked by missing source quality, contracts, consent/cohort policy. No orders, underwriting, applications or peer results     |
| Paytm SSO/OTP/live settlement/webhooks            | Not integrated; public settlement endpoints lack staging per supplied technical docs; actual access/signature contract and authorised E2E remain external gates                    |
| Supplier messaging / POS / lender / tax filing    | No automatic sending/POS feed/lending or authority submission; explicit supported integrations would need separate approval                                                        |

## F. Performance / AI evaluation limits

The release browser test records one local headless Chromium sample with simulated 120 ms latency, 200,000 B/s download and 100,000 B/s upload; no CPU throttle. It measures navigation through scripted sign-in to the visible home/brief, and warmed offline launch to device drafts. The complete image-upload/receiving/recovery flow also runs under simulated 80 ms latency/limited throughput; separate offline tests simulate a lost response and exact retry. Raw output is ignored `artifacts/test-evidence/batch10-browser-performance.json`.

These are engineering smoke measurements, **not field task-time savings, Web Vitals/FMP certification, P50/P95 population estimates or real-radio/device benchmarks**. Actual camera capture, CPU/low-storage/process-kill/device-update, accessibility screen-reader and broad browser/device testing remain skipped. Selected field/metric/primary text computed contrasts exceed 4.5:1, keyboard forward/reverse focus containment and phone nav 44px targets are tested; this is not a full WCAG audit.

AI corpus: 12 public synthetic images/text annotations, calibration/held-out split and adversarial variants. Key-absent image fallback and mocked strict-output safety are verified; no real provider was evaluated. The fixture text parser's structural exact match is not OCR quality. Human correction/time/acceptance, live provider latency/billing, translation fidelity and speech language/noise metrics remain unmeasured. See AI-EVALUATION.md and AI-DATA-HANDLING.md.

## G. Demo and reset

Use [DEMO.md](DEMO.md) for the four-minute script, exact synthetic ₹200 rice bill / 2 kg receipt / ₹40 shortage / two ₹20 proofs, separate settlement fixture and offline demonstration. The disposable rehearsal runner creates a new namespace and cleans only its own synthetic schema. Never delete existing financial/audit history to reset a demo. No real message is sent by automated tests; the sharing step is explicitly simulated.

## H. Remaining risks / post-hackathon roadmap

1. Authorised Paytm environment/product entitlement, request/signature contract, bank evidence and real end-to-end tests before any live integration claim.
2. Real Android/iOS/browser/device/network/assistive-technology matrix; HTTPS backend and native origin setup; release signing and update/backup/eviction acceptance.
3. Independently labelled consented real invoices, held-out dedicated-provider comparisons, current billing and correction-adjusted merchant evaluation. Configure/review actual provider retention and terms before sharing real data.
4. Production identity/account/store selection, least-privilege DB roles, robust backup/restore/retention/scanning and deployment/rate-limit/error-log review; Python dependency CVE scan and full secret/history/PII/security review remain external checks.
5. Relevant P1 source models/consent/quality evaluation require explicit authorisation. P2 must remain gated until its real prerequisites and reviewed execution/approval contracts exist. No autonomous procurement, underwriting or identifiable-store benchmarking.
6. Merchant field validation, presentation/video recording and substantiated outcome measurement remain separate work. Do not infer sales from payments, debt from payer identities or growth from a synthetic demo.

No future feature batch or destructive operation is authorised by this report. Preserve the working product and exact invariants when continuing.

## Final artifact and measured local evidence

- Debug APK: `artifacts/munafa-debug.apk` (ignored; also `android/app/build/outputs/apk/debug/app-debug.apk`), **4,459,492 bytes**, SHA-256 `2549eb846f48c01e54f4ffa6d46ec67455999c5e0fea1d28fc862f67d2ec5c1f`. Signature verification exits successfully; standard META-INF coverage warnings remain. Packaged public assets byte-match the final React build. Lint: 0 errors, 0 fatal issues, 28 existing warnings; Gradle flatDir/SDK XML warnings remain.
- One local simulated-network sample: navigation/scripted sign-in to home/brief **3011 ms**; warmed offline launch to drafts **32 ms**. Computed text contrast for selected fields/metric text is ~6.35:1 and primary button ~8.99:1. These are not general performance/accessibility certification or merchant savings.
- Endpoint inventory: 60 API operations, including 57 private authentication-boundary checks. Local source audit: zero known private-config/key-material matches, zero SQLite imports, production sync-debug control absent. No whole-history/semantic-PII claim.
- PostgreSQL restore: 32 application tables matched counts/content hashes in a new disposable database; source and restored synthetic ledger show 8000 paise recovery and 2 kg stock. Original application database was never restored over.
- Final test runs: **210 backend + 21 browser + 17 frontend unit tests passed**, no pytest/browser/unit skips in those runs. Separate device/live-provider/OS-install/screen-reader/Python-CVE checks listed above remain skipped/unavailable, not passing.
