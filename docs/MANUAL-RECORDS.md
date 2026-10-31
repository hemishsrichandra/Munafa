# Reviewed manual business records — 31 October 2026

## Scope and access

User confirmed no Paytm/WABA/lending/CA access, chose merchant-reviewed manual records with CSV later, and requested additive changes that preserve existing screens. Open **More → Daily records**. There are no new top-level navigation items or changes to purchase, receiving, supplier recovery, speech or external integration rules. Existing design components are reused; new CSS is scoped to `.daily-records`.

## Delivered workflows

- Customer register with unique store references, optional phone, optimistic versions and a recorded choice for local marketing draft selection. Contact information is private store data. Do not interpret a recorded choice as a third-party marketing legal contract.
- Explicit opening customer dues and credit sales create obligations. A received payment must target one specific obligation for the same customer. Multiple partial payments are supported; splitting across obligations requires separate reviewed records. Overpayment is rejected rather than assigned speculatively.
- Paid sales, expenses, opening cash, upcoming payables and their payments. Payment channel is recorded as cash, bank, UPI or other. Noncash receipts can reduce customer dues without increasing cash in the drawer. None of these entries are provider/bank verified. Financial sales records do not change SKU stock; use existing approved stock movements for physical depletion.
- Append-only financial history; corrections append owner-authorised reversals and retain originals. Allocated payments must be reversed before cancelling their obligation. All amounts remain strict integer paise. Store serialisation protects simultaneous allocation/reversal writes, while existing middleware owns request idempotency/CSRF/authentication.
- Customer reminder drafts show the current exact manually recorded balance. Nothing is sent; no payment link or bank receipt is invented.
- Opening, closing, follow-up, compliance and other tasks. Owner can assign existing owner/staff members in the current store; staff can self-assign and complete/reopen their own tasks. Changes require the exact current version and append an audit event. Dates are supplied by the merchant/adviser, not an inferred legal calendar.
- Manual cash outlook: a balance requires an explicit opening cash record. Customer collections, paid sales, expenses and payable payments affect cash only when their channel is cash. Credit sales and unpaid payables do not. A 7/30-day scenario is conditional on collections/payments and excludes undated obligations; all open undated items remain visible. This is not profit, bank balance, a complete cash forecast or lending eligibility.
- Local marketing drafts require explicit review and affirmative recorded customer choices. Recipient IDs and text are frozen in each saved draft. Withdrawal updates current eligibility and marks old drafts for recipient review. Repeated recorded sales and no-recorded-sale-in-30-days filters describe only the recorded history, not actual visits. There is no send API.
- Manual financial drafts can be saved in existing scoped IndexedDB and edited/queued in Drafts & sync. `business_entry_create` uses the existing immutable outbox, account/role purge, exact replay and server idempotency. Financial confirmation is required before queuing; new drafts cannot overwrite an existing entity. An offline duplicate/over-allocation remains a retained conflict. Customer creation, task updates, consent and campaigns currently require connectivity; the customer register is not cached into an unbounded offline directory.

## Schema and deployment

Forward migrations `82c5f712ac4d` (four tables), `0c7a1193f001` (immutable record/draft triggers), `19b0c9cc7712` (payment channel). Head: **19b0c9cc7712**. Apply `.venv/Scripts/alembic.exe upgrade head` before restarting on Windows (Unix uses `.venv/bin/alembic`). No legacy data imports/resets and no startup create-all/seed. Back up a populated database before any operator-initiated downgrade; do not downgrade merely to switch code versions.

Composite tenant FKs protect customer/allocation/reversal references and task membership. The shared immutable trigger protects financial entries and saved campaigns from UPDATE/DELETE. Customers/tasks are versioned, and consent choices have audit snapshots. Server truth remains PostgreSQL; device drafts are provisional.

Prototype bounds: review refuses balances above the 10,000-record or 10^15-paise gross-history capacity, rather than display incomplete/rounded totals. New normal entries stop at 9,990 records to reserve room for corrections. The screen shows the last 100 history entries while balances use all active records. Campaign list shows the last 100 saved drafts; one draft supports at most 100 recipients. This is not a production-scale accounting/CRM system.

## Verification

- New backend regression suite: 17 passed in targeted run (financial kinds, strict money, replay/reference guards, concurrent collections, reversals, tenant/role boundaries, consent withdrawal, task versions, reminders, offline operation and noncash handling).
- Frontend storage/exact-money suite: 19 passed, including business draft confirmation, operation mapping and persistence.
- Post-merge browser coverage: all 28 journeys passed across isolated spec runs (authentication 2, commerce 3, extension 1, offline 6, partner 3, polish 1, daily records 2, release 2, workflow 8). Two initial partner checks timed out waiting for element stability in Windows Chrome; both passed after disabling background rendering throttling for the test browser. The remaining specs also passed with that setting. No forced clicks or production rate-limit changes were used.
- Before merging the latest authentication/deployment changes, the full backend run had 276 passes and one failure caused by a UTC-versus-store-date test fixture. The fixture now uses tomorrow; the production date validation was retained. After merging, all 39 targeted checks passed (17 manual-record checks, the corrected cross-store check and 21 authentication checks). A complete backend rerun after that merge has not been claimed.
- Fresh forward migration and Alembic drift checks passed. Build, source lint, format and release audit are checked separately.

## Still unavailable

CSV/POS import, complete daily sales/zero-sales/stockout calendar, autonomous stock depletion from financial entries, automatic demand/dead-stock forecasts, evaluated fraud detection, current supplier offers/orders, live Paytm reconciliation, WhatsApp delivery, official payment links, automatic compliance deadlines/GST filing, lender workflows and peer benchmarking remain outside this release. No measured merchant profit/time-saving/recovery uplift is claimed; pilot validation and physical Android testing are still required.
