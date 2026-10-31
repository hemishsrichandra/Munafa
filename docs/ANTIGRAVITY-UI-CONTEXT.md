# Copy this context into Antigravity

## Latest stop checkpoint — user explicitly stopped further features

User asked to wrap up because their weekly allowance is running low. Stop feature implementation. Preserve this tested checkpoint; no half-enabled feature is pending.

Final continuation added simpler secondary-screen/offline wording, final-delivery missing-item badges using exact BigInt decimal comparison for display, expiry pills, measured contrast repairs, and a dev-only @axe-core/playwright accessibility suite. No backend/model/outbox engine changes. A late four-line wording experiment in Planning.jsx was returned to the version used by the final browser build before commit.

**Final complete browser run: 35 passed, no failures** in `tmp/ui-complete-all.log` (14 isolated spec groups in one runner invocation). This supersedes earlier 34-test and split-run checkpoints. **20 offline/money/display unit tests passed.** Production build passed. Automated axe WCAG A/AA scans report **zero violations on four main destinations and bill dialog**; ignored local `artifacts/test-evidence/merchant-accessibility.json` contains `[]`. This is bounded automated coverage, not a formal whole-app accessibility certification or physical phone test. Production dependency audit: zero vulnerabilities. npm reports 4 moderate development-tool advisories; no forced dependency upgrade was applied.

Existing backend validation messages and gated advanced planning tools still contain some technical terminology. No hardware, full translation, certification or new native APK result is claimed. Those limits must remain explicit; do not restart broad work unless the user asks. The current frontend build is served at http://127.0.0.1:8002/; verify health when resuming. The final delivery message gives the push commit. Keep cookies.txt, .env and unrelated output/tmp/research files out of Git.

## Continuation update: broader regression migration

Final results: all 34 distinct browser journeys passed across isolated runs, including migrated purchase/receiving, financial records, supplier partial/full recovery, offline replay, onboarding, help and account recovery checks. The dedicated merchant-ui journey passed again on the final language-selector build. Production build and homepage HTTP 200 passed. Refer to docs/MERCHANT-UI.md; do not treat the previous-checkpoint limitations below as the latest regression status. Physical-device and formal accessibility certification remain unperformed. Backend rules were not changed to obtain passing tests.

The subsequent pass migrated legacy browser selectors to the new wording and replaced sidebar navigation with `tests/e2e/navigation.cjs`. Supplier cases, suppliers and reports are reached through More; header bounds now test bottom navigation rather than a hidden sidebar. Customer/expense assertions retain the same financial checks, with the home expense tile assertion replaced by the requested cash-in-Galla tile. Source-route and money assertions were retained. Current browser verification is documented in docs/MERCHANT-UI.md after completion; earlier statements below about unmigrated tests describe the previous checkpoint.

Continue Munafa's frontend redesign. Repository: https://github.com/hemishsrichandra/Munafa, branch main. Windows workspace: C:/Users/tharu/OneDrive/Documents/munafa. Fetch and inspect HEAD before editing: Hemish pushes concurrently. Do not force-push or overwrite local files. Read docs/MERCHANT-UI.md and this context first.

## User request and constraints

The user wants a simple Indian kirana UI with English/Hindi-friendly words, four bottom tabs, clear bill-versus-delivery steps, prominent sales/cash/udhaar, large controls, simple customer collections, and expandable detail. Time is short. Finish small working increments, test, commit/push, and report remaining work honestly. Never change backend calculations/models/security, integer-paise arithmetic, physical receipt rules or offline outbox semantics as part of a UI redesign. I cannot see the user's weekly allowance or guarantee warning before exhaustion.

## Delivered UI changes

- Four persistent destinations across phone/desktop: Today, Deliveries & Stock, Customer Khata, More. Old sidebar is hidden. Supplier/refund/report routes remain accessible through More.
- Today leads with today's recorded sales, customer dues and cash in Galla using existing /brief fields; unknown opening cash remains unknown. It does not claim full-shop sales or bank verification.
- Quick actions: New Bill opens existing bill modal; Customer Udhaar opens a blank credit-sale form; Settle Galla opens existing cash drawer. Actions do not post financial records automatically.
- Customer cards have Gave Credit and Received Payment shortcuts. They select the customer and operation type, retaining explicit allocation/confirmation requirements. Existing reviewed WhatsApp/UPI preparation is retained; no auto-send was added.
- Deliveries & Stock has a two-step explanation: bill contents, then physical count. Only accepted usable receiving adds stock. Stock alerts and product terminology are clearer.
- Case status labels and money-received confirmation copy are simpler. Confirmed item arithmetic is expandable. Proof fields and approval guards remain.
- Presentation styles include 52px form/buttons, 16px form inputs, four bottom targets, focus outlines, semantic colours, cards and responsive layouts. Primary labels include Hindi subtitles.

Files changed: frontend/src/App.jsx, styles.css, components/Commerce.jsx, InvoiceIntake.jsx, DailyRecords.jsx, DailyRecordsSummary.jsx, CaseDetail.jsx, CaseActions.jsx, ui.jsx. New browser spec tests/e2e/merchant-ui.spec.js. See docs/MERCHANT-UI.md.

## Verification actually performed

- Production build passed.
- 19 offline/exact-money tests passed.
- New Playwright merchant-ui journey passed on the final merged build: navigation and quick actions, Galla, bill dialog, page-error collection, widths 320/390/844/1440, no horizontal overflow in the tested Khata screens, and bottom navigation heights >=48px.
- Prettier and git diff checks passed before the merge. Screenshots are local in artifacts/test-evidence/merchant-today.png and merchant-new-bill.png. Today screenshot was inspected; a subsequent hierarchy change moved the summary above the quick actions and attention brief.
- One intermediate run stalled in Windows Chrome while filling login; fresh reruns passed. No forced clicks or disabled production guards.
- Full legacy browser suite was NOT run for the redesign. Many old specs select removed sidebar controls/old wording and need migration. Do not claim complete regression coverage or WCAG certification.

The UI change itself did not edit backend, model, migration or outbox code. Before pushing, remote commits a08e250 and fb9f6be were merged, bringing Hemish's backend supplier-message fallback and resilient modal state changes. Final merchant-ui test passed after that merge. Do not describe those concurrent changes as authored by this redesign.

## Work still needed to fully satisfy the ambitious design request

This is a working core presentation increment, not proof that every screen is zero-jargon or production-certified. Finish the following without breaking existing behavior:

1. Migrate legacy browser selectors/navigation to the four-tab architecture, preserving financial end-to-end assertions, then run the entire browser suite. Add actual customer-credit/payment, purchasing/receiving and supplier proof verification coverage under new wording.
2. Audit remaining secondary/admin/offline/help screens for jargon and bilingual labels. Deep server validation messages retain technical words; preserve their meaning and safety. Some all-time supplier summary labels remain accounting-oriented.
3. Complete coverage of delivery-card missing-item badges and prominent expiry pills. Verify each summary uses recorded evidence and does not infer missing quantities before receiving is final.
4. Finish progressive disclosure and simplify large forms beyond the initial entry shortcuts. Keep required source, unique reference, explicit allocation and merchant approval; never hide essential financial confirmation.
5. Perform measured contrast and keyboard/dialog/screen-reader review, plus actual phone testing. Current CSS changes and one navigation test are not complete WCAG AA proof. Avoid claiming an S-tier rating as an objective test result.
6. Inspect current seeded demo and nonempty merchant screens. The new browser journey primarily validates empty-store navigation; real entry/recovery paths need further regression coverage.

## Setup and commands

Frontend React/Vite; backend FastAPI/Pydantic + SQLAlchemy Core/Psycopg + PostgreSQL/Alembic. Use .venv/Scripts/python.exe. Private .env contains credentials: never print or commit it. Existing local app is http://127.0.0.1:8002/; verify running process and static assets. Build with npm run build. Start with node scripts/python.cjs -m uvicorn backend.app:app --host 127.0.0.1 --port 8002. Never kill unrelated processes.

Tests: npm run test:offline. For browser tests set TEST_DATABASE_URL=postgresql+psycopg://munafa@127.0.0.1:5432/munafa_test and PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe. Set E2E_SPEC_FILTER=merchant-ui to run only the new journey; omit it for all specs after migrating them. Run npm run test:e2e -- --reporter=list --trace=off. The runner builds and uses disposable schemas; never reset merchant data. Temporary PostgreSQL runtime is under %TEMP%/munafa-pg-test-runtime/pgsql/bin and cluster %TEMP%/munafa-batch5-pgdata.

Keep exact money and fractional units, tenant/role/CSRF/idempotency, append-only reversals and offline conflicts. Supplier promises are not recovery. Invoice acceptance is not physical receipt. There is no authorised live Paytm/WABA/lender integration to invent.

Exclude unrelated local cookies.txt, docs/LOCAL-FIX-REPORT.md line-ending noise, docs/PRE_HACKATHON_PROPOSAL.md, output/ and tmp/ from commits. Never commit cookies, generated credentials or private evidence. Commit only relevant working source, tests and documentation. Report completion and remaining limits explicitly.
