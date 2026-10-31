# Munafa — Antigravity continuation context

## User constraints

Hackathon deadline: favour small, finished improvements. User requested roughly 20 minutes of work, preserved UI and existing flows, working code only, Git push, and a handoff. Do not start all seven roadmap items at once or present unavailable integrations as implemented.

## This increment

Selected roadmap item 1: connect existing Daily records to the home dashboard. `frontend/src/components/DailyRecordsSummary.jsx` adds a read-only home snapshot using existing `/api/records/summary` and `/api/records/tasks`. `frontend/src/App.jsx` mounts it immediately after the existing business brief.

- All-recorded-date sales, outstanding customer dues, expenses and open tasks.
- Cash drawer uses the server's cash-only calculation; opening cash absent means unknown, not zero.
- Labels explain manual source, incomplete business coverage, synthetic demo mode and exclusion of unsynced device drafts. These are not profit, bank verification or today's sales.
- Open daily records navigates to the existing workflow.
- Loading/error/retry states; disconnect clears displayed totals; reconnect and server-change events reload. Pending reads are cancelled when the component unmounts or reloads. No new cache, database migration, dependencies or financial writes.
- Uses existing visual components and styles. Main navigation and supplier/purchase workflows are preserved.

## Existing foundation (already delivered before this increment)

More → Daily records includes merchant-reviewed customers, opening dues/credit sales, explicit partial collections, paid sales, expenses, payables/payment channels, append-only reversals, staff tasks, conditional cash scenarios, local reminder/marketing drafts and eligible offline financial drafts. PostgreSQL is server truth; IndexedDB drafts are provisional. Head migration: `19b0c9cc7712`. See `docs/MANUAL-RECORDS.md`, `docs/FEATURE-CHECKLIST-AUDIT.md` and `docs/HANDOFF.md` for limits.

Supplier invoice acceptance never adds stock. Actual accepted undamaged receiving does. Supplier promises never count as recovery. Exact integer paise, quantities, tenant scope, roles, idempotency and retained conflicts must remain intact. Financial sales entries do not decrement SKU stock.

## Environment and commands

- Workspace: `C:/Users/tharu/OneDrive/Documents/munafa`, Windows PowerShell.
- Remote: `https://github.com/hemishsrichandra/Munafa.git`, branch `main`. Check current HEAD and remote before editing; Hemish may push concurrently. Merge without force pushes and retain both authors' work.
- App: `npm start`, `http://127.0.0.1:8000/`; build: `npm run build`.
- Python: `.venv/Scripts/python.exe`. PostgreSQL is required; never fall back to SQLite or reset merchant data.
- Local private `.env` contains provider configuration: never print, copy into this handoff or commit secrets.
- Local test PostgreSQL runtime: `$env:TEMP/munafa-pg-test-runtime/pgsql/bin`; cluster `$env:TEMP/munafa-batch5-pgdata`; test DB `postgresql+psycopg://munafa@127.0.0.1:5432/munafa_test`. Confirm readiness before tests. Do not remove a postmaster lock while its server exists.
- Backend: set `TEST_DATABASE_URL`, then `.venv/Scripts/python.exe -m pytest backend/tests/test_records.py -q`.
- Frontend storage/money: `npm run test:offline`.
- Browser: set `TEST_DATABASE_URL`, `PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe`, optionally `E2E_SPEC_FILTER=records|header|workflow`, then `npm run test:e2e -- --reporter=list --trace=off`. Runner builds once and isolates each spec's disposable schema/server; Windows background-rendering flags prevent known element-stability stalls.
- Source audit: `.venv/Scripts/python.exe scripts/audit_release.py`.

## Deferred, deliberately not started here

Supplier performance scorecards, CSV imports, stock-adjustment exceptions, reminder acknowledgement/snooze and sales-observation calendar. Physical Android and merchant pilot validation remain outstanding. No skeleton routes or placeholder feature screens were added for these.

Paytm/WABA/lender/CA access is unavailable. Do not claim live reconciliation, message delivery/payment links, lending, GST filing, evaluated forecasting, real visit-based dormancy or measurable merchant uplift. Sarvam speech remains online; an offline speech model has not been implemented.

## File hygiene

Pre-existing local research/generated items: `docs/PRE_HACKATHON_PROPOSAL.md`, `output/`, `tmp/`. `docs/LOCAL-FIX-REPORT.md` may show only line-ending changes. Exclude these unrelated items from commits. Generated test evidence is local under `artifacts/test-evidence/`.

## Final verification

Completed: 17 ledger backend tests, 19 offline/exact-money tests, and 12 browser journeys (header 1, records 3, workflow 8) passed. Browser coverage includes the real ledger-to-home totals, navigation, unknown opening cash, failed reads/retry, offline clearing/reconnect, phone widths and existing supplier recovery/navigation. The final production build passed. Prettier and diff checks passed; source audit scanned 318 files with zero detected configured secrets and zero SQLite imports. Homepage returned HTTP 200. Snapshot image `artifacts/test-evidence/home-business-snapshot.png` was visually inspected.

The first browser run found two test assertion errors (whole-rupee formatting and a mobile-only navigation label used at desktop width); those tests were corrected and all selected specs passed on the final build. No tests were skipped or forced through. No full backend-suite pass is claimed for this UI-only increment. No selected feature remains partial: the home snapshot is complete within the explicit manual-data scope. Other roadmap items above were not started.
