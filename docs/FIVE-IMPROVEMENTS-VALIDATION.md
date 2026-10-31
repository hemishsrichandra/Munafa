# Five-improvement validation and continuation

## STOP checkpoint — owner requested handoff and no further work

31 October 2026. Implementation/testing stopped at the owner’s request. **Latest combined published product commit: eb003ee** (parallel editor included our staged OCR/validation files in that commit). Earlier pushed checkpoints: cc17329 onboarding/home; d48a6ac recovery/security/backup tooling. Preserve this history; do not reset/rewrite it.

Confirmed results: combined tree **353 PostgreSQL backend tests passed**, 19 offline unit tests passed, **all 33 Playwright browser journeys passed**, Prettier and Ruff passed. The full combined browser suite across 12 spec files was executed and passed with 0 failures using installed Chromium headless shell. Combined source audit: 359 files, zero detected private-value/key-material leaks, zero runtime SQLite imports, 94 API endpoints; this is not a full security certification.

Combined Android APK assembleDebug and lintDebug succeeded in a separate native export. Earlier app lint: 0 errors/28 warnings. No Android device connected, no install/hardware/pilot test. Current ignored APK: artifacts/android/munafa-debug-eb003ee.apk; SHA256 10318ef07afe6ef9321af08329243eaccc80116ba32dc7ba4825e5d427821e16. Rebuild from source on another system; APK is not committed. An earlier isolated APK has a different hash and is superseded for the combined UI. Five Python formatting-only changes have identical ASTs to tested eb003ee and are included with this handoff; Ruff check/format then passed. No framework/dependency update was performed in this final checkpoint.

External gaps: live OCR remains **UNMEASURED** (owner confirmed key is Render-only; zero paid calls). No other paid API used. No configured off-host backup destination, no email recovery service, no real thermal/handwritten consented corpus, no actual Android device or merchant pilot. Recovery codes, manual workflows and default-off demo AI work without those prerequisites. See ACCOUNT-RECOVERY.md and ../ops/BACKUP-RECOVERY.md for setup. Render public health returned HTTP200 with signup/demo enabled and a server-side Sarvam key; this does not prove the latest rollout/migration or a live OCR test.

Owner next actions: verify APP_ENV=production/ALLOW_DEV_LOGIN=0 and remove DEV_LOGIN_CODE in actual Render settings; keep PUBLIC_DEMO_AI_ENABLED=0; deliberately allow-ai only for trusted accounts if desired; configure and verify a private compatible backup destination; approve native https://localhost origin before actual APK API tests. Do not paste secrets. No live data import/reset/production restore or destructive retention action was performed.

Continuation: pull main first, inspect status/instructions and coordinate any active editor. Parallel store-settings/UPI/receiving work is now committed in eb003ee, including migration a1b2c3d4e5f6 (parent f237b2e9c014); do not treat it as untracked or overwrite it. Unrelated deleted starters/regulatory-starter files remain local and excluded from commits. Retained safety stash 'codex recovery ops before latest Render config merge' must not be blindly popped. Temporary validation paths: /private/tmp/munafa-combined-340_u_9l (combined tests), /private/tmp/munafa-combined-native-jnf_8rcr (APK/lint), /private/tmp/munafa-validation-final-63z2np0p (isolated full browser pass). They are disposable machine-local evidence, not portable dependencies. Next session should first collect/finish combined browser validation only after owner authorisation, then address external gates. Never fabricate absent metrics or count unfinished tests as passing.

Earlier checkpoint history below (superseded where the stop checkpoint differs):

31 October 2026. This report distinguishes implemented software, synthetic regression evidence and unavailable field evidence. No real merchant documents, new production demo records, storage service or additional paid API was used. Sarvam is the only authorised paid AI provider; the local benchmark made **zero API calls** because its key exists only on Render. The owner chose to leave live results unmeasured.

## Delivery status

| Improvement     | Delivered                                                                                                                                                                                                                 | Remaining gate                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Demo onboarding | Reuses existing synthetic sample under a store-scoped transaction lock; staged guide links to the actual case; normal manual invoice duplicates still reject                                                              | Observe first-workflow completion with consenting users                                                                                        |
| Unified home    | Existing home snapshot preserved; accepted manual sales/expenses, customer dues, tasks and review/recovery actions use source IDs, timestamps and detail routes                                                           | No automatic POS/SKU-sales inference; only recorded facts appear                                                                               |
| Safeguards      | One-time hashed recovery codes, session revocation, generic/rate-limited recovery, operator-approved provider access, default-off public-demo spending, quota reservations, configurable backup/restore/retention tooling | Configure and verify private backup destination; qualified retention review; email recovery later                                              |
| OCR evaluation  | Versioned owned image corpus, programmatic labels, field scorer, explicit budget runner, safety regressions and PDF completeness fallback                                                                                 | Live accuracy/latency/cost, actual thermal/handwritten samples, independent labels and observed correction time unmeasured                     |
| Android/pilot   | Same-source debug APK and lint; browser offline/response-loss/conflict/permission-denial checks; simulated CPU/network stress; consented-pilot protocol                                                                   | No connected Android device or merchant participants. Actual hardware, camera picker, microphone, low-end device and pilot outcomes NOT TESTED |

## Commands and evidence

Run from the repository with dependencies installed. Set TEST_DATABASE_URL privately to a dedicated **PostgreSQL** test database; fixtures create/drop only their generated schemas. PG_BIN must point to compatible PostgreSQL 17 clients for archive/restore checks. Tests use no SQLite and no paid provider.

```sh
TZ=UTC .venv/bin/python -m pytest backend/tests -q
.venv/bin/ruff check backend scripts
.venv/bin/ruff format --check backend scripts
npm run format:check
npm run test:offline
npm run test:e2e
npm run build
```

Final results are appended below after completion. Security checkpoint d48a6ac passed 339 backend, 33 browser and 19 offline unit tests. The OCR changes add five backend tests. Tests include original Munafa recovery invariants, merchant receiving vs invoice distinction, paise/decimal rules, tenant/role checks, approval/version binding, duplicate prevention, source links, recovery-code replay and backup content checks. Do not interpret this as legal certification or proof of every production deployment setting.

The first final browser attempt was invalidated when Android packaging concurrently overwrote its frontend output with a different API base. Six offline tests failed. Packaging was completed, the relative-API web app rebuilt, and the **entire** browser suite rerun without concurrent asset writers. No test/assertion or application limit was weakened. Build different targets sequentially or in separate exports.

### OCR protocol

`evaluation/validation-v2/` contains five 640×700 generated PNG/SVG pairs: printed English, faded monospaced thermal **proxy**, cursive typography handwriting **proxy**, printed Hindi and printed Kannada. Hindi/Kannada glyphs were visually checked. Ground truth is programmatic, not independently adjudicated. These single-line controlled bills do not establish accuracy on real photographs or fully local-language invoices. The pre-existing 12-case/adversarial corpus and injection regressions remain intact.

`availability-report.json` records zero measured documents and null accuracy/latency/cost/human metrics. No missing result is a successful OCR call or zero-cost measurement. The scorer records per-field errors, extra emitted line fields, exact match/precision/recall, failures and latency percentiles when measured. It never infers merchant acceptance, human corrections/time or verified billing.

Reproduce owned assets locally (no remote fonts/services):

```sh
.venv/bin/python scripts/build_ocr_validation.py
node scripts/render_ocr_validation.cjs
```

The second command uses installed Playwright Chromium, or PLAYWRIGHT_EXECUTABLE_PATH. Rendered font metrics vary by OS; freeze and independently review assets before a comparable benchmark.

For a **newly authorised** run, privately configure SARVAM_API_KEY, check the model/pricing date and run:

```sh
.venv/bin/python scripts/ocr_benchmark.py --allow-paid-calls --budget-paise 1000 --max-documents 5
```

This operator-only runner accepts labelled synthetic images, has no application DB mutation, uses the production Sarvam document adapter, makes at most five attempts with no retries, reserves 200 paise per attempt, stops on unknown/excess usage, and refuses an existing result directory (including crash recovery). Responses remain chmod 0600 in ignored evaluation/private. A reservation is not verified billing or an enforceable provider-account spending cap. Published token rates are a dated estimate, exclude GST and ignore cache discounts; actual invoices remain authoritative. Only ₹10 was authorised in this session; no paid attempt was made. Do not run additional paid benchmarks automatically in CI.

Official [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing), checked 31 October 2026: gemma4 ₹35 input/₹90 output per million tokens, excluding GST. These are evaluation metadata, not application money calculations or a provider-quality recommendation. No other paid API is enabled/tested. No evidence yet supports switching provider or making OCR the default.

PDF text now reports completeness/truncation; at the 18,000-character limit an incomplete document stops cloud extraction and directs manual review of the preserved source. Invalid schema responses retain allow-listed integer usage counters; no source text, key or raw response enters telemetry.

### Android evidence and next test

Build with JDK 21 and the accepted SDK licenses:

```sh
VITE_API_BASE=https://munafa-paytm-partner.onrender.com/api npm run android:debug
(cd android && ./gradlew lintDebug --no-daemon)
npm run android:check
adb devices -l
```

Set JAVA_HOME and ANDROID_HOME/ANDROID_SDK_ROOT to local installations. No machine paths or signing keys belong in Git. Output android/app/build/outputs/apk/debug/app-debug.apk. This session's ignored copy: artifacts/android/munafa-debug-20261031.apk, SHA-256 **3571751aab2b7379ae6ea5c32b4f99b5ecc5ae153e1d27e5f5efdfffcf4553a9**. APK binaries are not pushed to Git; rebuild on another system. Debug build is not a release-signed Play Store artifact.

assembleDebug and lintDebug succeeded. Application lint: **0 errors, 28 warnings** (template icons/resources, dependency updates, manifest order/data-extraction rules); no suppressions/baselines added. SDK XML-version, flatDir and upstream plugin deprecation/type warnings remain. Packaged permissions: INTERNET plus AndroidX app-scoped receiver permission; no microphone, location, contacts or broad storage permission. Native microphone remains deliberately unavailable with text alternative. ADB listed **no devices**, so no APK install, OS picker, camera capture, process-death or real-device offline/permission test is claimed.

Before native network testing, owner must review/add exact native origin https://localhost to backend APP_ORIGINS alongside the deployed web origin. Do not use wildcard origins or cleartext. Test sign-in, logout/revocation, authenticated downloads and account-switch cache clearing on the actual device. Packaged shell can launch locally; authenticated data and AI still need network. Browser CPU/network simulation is not low-end hardware evidence.

## Owner actions and external decisions

1. Keep Render APP_ENV=production, ALLOW_DEV_LOGIN=0; remove shared DEV_LOGIN_CODE from actual service environment. It was removed from the current blueprint; an older remote commit exposed it, so treat it as public. Never weaken the production guard.
2. Keep PUBLIC_DEMO_AI_ENABLED=0. Existing/public-signup accounts now fail closed for cloud spending. For one trusted merchant account, operator can run `python -m backend.manage allow-ai --username EXACT_USERNAME` and explicitly type ALLOW. Demo identities cannot be granted this route. Deny with deny-ai. No user-facing approval bypass exists.
3. Configure an existing private compatible backup destination and secrets following ops/BACKUP-RECOVERY.md; no new paid API is required by the implementation. Check any free-tier compatibility/quotas before choosing. Until a verified backup and scratch restore succeed, operational protection remains NOT CONFIGURED. The nightly configuration check is not a successful backup. Retention application remains off.
4. Recovery codes: merchants must explicitly generate/save them before losing access. No email provider exists. Lost password **and** lost codes still need an identity-reviewed operator recovery procedure.
5. For OCR evidence later: decide approved dataset/strata and acceptance thresholds, obtain consented actual printed/thermal/handwritten Hindi/Kannada samples, independent ground truth and actual reviewer timings. Record provider terms/retention/consent before real uploads. No keys or real documents in chat/Git.
6. Supply a connected consenting test device and recruit consenting kirana owners only after approving pilot notice, purpose, withdrawal, retention and support contact. Use docs/EVALUATION-AND-PILOT.md and scripts/analyse_pilot.py. Counterbalance manual/touch/assisted tasks; measure corrections and completion, not synthetic revenue lift.

## Continuation in another chat/system

Pull main first and inspect git status/diff/AGENTS before edits. Checkpoint cc17329 is onboarding/home, d48a6ac security/ops. This validation commit follows them. Another editor has uncommitted store-settings/UPI/reminder/receiving work, including migration a1b2c3d4e5f6 with parent f237b2e9c014. It was deliberately excluded from our commits and remains in this working tree. Existing deleted regulatory-starter files also remain untouched. Do not blindly stage/reset/stash/pop/overwrite those changes. Temporary safety stash named 'codex recovery ops before latest Render config merge' remains; do not automatically pop it.

Tests reported here run in a temporary archive of our staged tree, excluding unfinished parallel code. That editor must separately integrate/commit its migration and run full tests before claiming the combined working tree is validated. Never edit applied migration history; verify backup/approval before any populated database downgrade/import/reset. PostgreSQL remains the only application/test DB; IndexedDB is client-only offline storage.

Next phase: verify Render rollout with read-only health/config and an approved test account; configure/verify backups; run real Android acceptance and consented pilot; then perform newly authorised private OCR evaluation. Keep live Paytm disabled without authorisation/contracts. Do not fabricate missing measurements or add forecast/analytics claims from payment totals.
