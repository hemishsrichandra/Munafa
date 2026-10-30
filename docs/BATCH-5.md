# Batch 5 - purchase receiving and inventory

Updated 30 October 2026. Completes the backend-only handoff at commit `9d23879`.

## Delivered

- Separate purchase register, reviewed invoice editor, manual/sample/text/photo/PDF intake.
- Explicit SKU mapping and review of printed/effective prices and header totals. UI shows prices in paise explicitly; no inferred tax allocations or unit conversions.
- Authenticated original-document download and on-demand image/PDF preview.
- Separate physical receiving editor, partial/final deliveries, damage, batch and expiry fields. Saved receiving drafts remain editable until accepted.
- Exact proposal -> approve -> execute workflow for invoice acceptance, receiving acceptance and manual stock movements.
- SKU create/edit, stock/reorder indicators, movement history with units and source linkage, recorded lot balances and a 30-day expiry view.
- Linked supplier recovery entry from accepted purchases; mobile Credit cases remains available through More.
- Commerce API helper functions in api.js.
- IndexedDB purchase, receiving and reviewed stock drafts; existing queue/status/retry controls now support purchase_create, dependent purchase_document_upload, purchase_receiving_capture and inventory_movement.
- Authenticated, expiring commerce snapshot for offline receiving capture. Offline values are clearly stale/provisional; stock changes only on accepted server events. Account/role changes retain the existing private-cache purge rules.
- Editable offline commerce forms; attachment dependencies preserve checksums and exact frozen wire requests. Version zero is preserved for new SKU stock operations.
- Portable Python launcher for npm scripts and Playwright, Windows dependency markers and an existing test's interpreter-path correction.

## Backend correction

Receiving previously rejected overdelivery, contrary to the supplied requirement. Physical overdelivery is now recorded in receiving and usable stock. The linked shortage calculator still flags overdelivery for separate review and never produces a negative monetary claim. Invoice acceptance alone still changes no stock; damaged goods never increase usable stock.

## Regression coverage

`backend/tests/test_commerce.py` exercises duplicate invoices, acceptance without stock, fractional quantities, exact six-place conversion, partial/final receiving, missing counts, unconfirmed/mismatched units, excess damage, overdelivery, ledger replay, idempotency, shortage arithmetic, tenant isolation, permissions, stale receiving and duplicate purchase-linked recovery proof.

IndexedDB tests cover commerce operation types, version zero and dependent document uploads in addition to the previous storage/lease/retry tests. New browser journeys cover purchase review -> acceptance -> physical receiving -> stock -> linked case, plus an attached offline purchase surviving reload and reopening in its editor. Existing desktop/mobile recovery and offline tests remain part of the full suite.

## Environment and boundaries

Use PostgreSQL only. Apply `alembic upgrade head`; head remains `67e38dd313f8`. No schema change was needed for this frontend completion. No legacy databases were imported, reset or deleted.

On Windows this session installed a temporary PostgreSQL 17.6 runtime under `%TEMP%/munafa-pg-test-runtime`, with isolated cluster `%TEMP%/munafa-batch5-pgdata` bound to 127.0.0.1:5432. Tests use database `munafa_test` and generated disposable schemas. This loopback-only trust-authenticated setup is for local tests, not production. Do not point tests at merchant data.

No live Paytm or Sarvam claims are made. The Linux PDF subprocess resource sandbox is not available on Windows; unsafe/unavailable text extraction falls back to a manual draft with the original preserved. Native Android installation, storage pressure and process-kill behavior still require a device test. AI-generated confidence is not invented when the provider gives none.

Verification: full backend run 74 passed; expanded Batch 5 backend suite 18 passed (including one additional test added after the full run); IndexedDB 14 passed; browser journeys 16 passed; production build, migration drift, Ruff and Prettier passed. Detailed environment and limits are recorded in HANDOFF.md. The user authorised committing and pushing this completion to origin/main. Local credentials and generated output are excluded.

