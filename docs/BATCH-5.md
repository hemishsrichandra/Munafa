# BATCH 5 – Kirana core: purchase capture, physical receiving, inventory and Munafa recovery

**Committed:** 30 October 2026  
**Migration head:** `67e38dd313f8`  
**Tests:** 57 backend pass (unchanged from Batch 4; no new tests written yet — see Remaining Work)

---

## What Was Built

### Database Schema (additive migration `67e38dd313f8`)

Twelve new tables — all append-only, store-scoped, FK-guarded, no legacy records altered:

| Table | Purpose |
|---|---|
| `products` | SKU master — code, name, unit, barcode, reorder threshold, expiry-tracking flag |
| `unit_conversions` | Merchant-defined unit conversion rules with explicit provenance |
| `purchases` | Purchase draft / accepted header (no stock effect on accept) |
| `purchase_documents` | Original invoice files — PDF or image, ≤ 8 MB, SHA-256 verified |
| `purchase_revisions` | Full immutable audit trail of every draft edit |
| `purchase_acceptances` | Immutable snapshot at acceptance (supplier, totals, actor, time) |
| `purchase_lines` | Per-line billed quantities/prices, linked to accepted SKU |
| `receiving_drafts` | Draft physical receiving records linked to an accepted purchase |
| `inventory_sources` | Approved event metadata with source linkage and case ref |
| `inventory_events` | Append-only signed quantity deltas (NUMERIC 20,6) |
| `lots` | Batch / expiry-date tracking per product |
| `receipts` / `receipt_lines` | Immutable accepted receiving snapshots |

### New Backend Files

| File | Lines | Description |
|---|---|---|
| `backend/purchasing.py` | 757 | Purchase draft/accept/receive services |
| `backend/inventory.py` | 471 | SKU catalog and append-only stock events |
| `backend/purchase_extraction.py` | 187 | AI→draft extraction (never populates received qty) |
| `backend/pdf_text.py` | 39 | Sandboxed bounded PDF text-layer helper (no OCR) |
| `backend/commerce_models.py` | 94 | Pydantic v2 strict models for all commerce inputs |
| `backend/commerce_api.py` | 473 | 18 authenticated REST routes |
| `backend/migrations/versions/67e38dd313f8_…py` | 654 | Additive Alembic migration |

### Modified Backend Files

| File | Change |
|---|---|
| `backend/models.py` | +300 lines — SQLAlchemy Core table definitions for all 12 new tables |
| `backend/app.py` | +30 lines — `commerce_router` registered; `commerce_link` wired into case views |
| `backend/sync.py` | +26 lines — 5 new offline operation types; legacy-edit guard added |
| `backend/actions.py` | +16 lines — commerce action execution routed through approval pipeline |
| `backend/requirements.txt` / `requirements.lock.txt` | `pypdf` added for PDF text extraction |

### API Routes (all authenticated, store-scoped)

```
GET    /api/purchases
GET    /api/purchases/{pid}
POST   /api/purchases/manual
POST   /api/purchases/sample          (demo stores only)
PATCH  /api/purchases/{pid}
POST   /api/purchases/extract-text    (AI draft, review required)
POST   /api/purchases/document        (PDF / image upload, AI draft)
GET    /api/purchase-documents/{did}
POST   /api/purchases/{pid}/receivings
PATCH  /api/receivings/{rid}
POST   /api/commerce/proposals        (accept_purchase / accept_receiving / inventory_movement)
GET    /api/products
POST   /api/products
PATCH  /api/products/{pid}
GET    /api/products/{pid}/movements
GET    /api/products/{pid}/conversions
POST   /api/products/{pid}/conversions
GET    /api/inventory/expiry          (30-day expiry window)
```

### Offline / Sync Extensions

`backend/sync.py` now accepts five new operation types through the existing idempotency pipeline:
- `purchase_create` — offline manual purchase draft (with optional expected-document metadata)
- `purchase_document_upload` — attachment bound to a draft version
- `purchase_receiving_capture` — receiving draft bound to an accepted purchase version
- `inventory_movement` — stock adjustment (requires `approve` role + `merchant_confirmed: true`)
- `proof_upload` — Munafa case evidence (existing path preserved, re-routed through commerce module)

### Invariants Preserved

- **Invoice acceptance never changes stock** — enforced in `purchasing.accept()`.
- **Receiving acceptance writes undamaged quantity only** — enforced in `purchasing.accept_receiving()`.
- **Shortages never auto-decrement stock** — only through a separate approved `shortage_correction` event.
- All money in **integer paise**; all quantities as **NUMERIC(20,6)** strings, never floats.
- Every event carries: `source_entity_id`, `actor_id`, `operation_id`, `store_id`, `timestamp`.
- Approval pipeline: `propose → approve → execute` via existing `actions.py`.
- Tenant isolation: every query is `WHERE store_id = current_store_id`.
- Duplicate supplier/reference guard on purchases.
- Immutable snapshots: accepted purchase and accepted receiving cannot be mutated.
- PDF extraction sandboxed in a subprocess with CPU + memory limits; no OCR claimed.
- Sarvam AI extraction creates draft only; falls back gracefully; manual entry works without AI or internet.

---

## Remaining Work (Not Yet Done)

### 1. Frontend UI — 0% complete (Batch 5 req. 20–21)

No Batch 5 screens exist. The "Purchases" nav tab renders the existing Munafa case list. Screens needed:

1. **Purchase list** — `GET /api/purchases`, status badge (draft/accepted), supplier, reference, total, date; empty state; demo label
2. **Purchase detail** — line items, validation issues, document thumbnail, linked receivings list
3. **Invoice review / edit form** — merchant confirms supplier, reference, date, each line's qty / unit / price / SKU; confidence/review indicators for AI-extracted fields; manual entry must work offline
4. **Intake entry points** — bill photo, PDF upload, paste text, manual entry form, sample button (demo)
5. **Receiving screen** — actual qty, unit, damaged qty, batch ref, expiry date, delivery-complete toggle; shows draft / pending sync / accepted state
6. **SKU / stock list** — `GET /api/products`; unit, stock qty, reorder alert; below-threshold highlight
7. **Stock movement timeline** — `GET /api/products/{pid}/movements`; append-only event list; unit on every row
8. **Expiry list** — `GET /api/inventory/expiry`; expired vs expiring-soon; 30-day window
9. **Recovery entry points** — link from purchase/receiving detail to Munafa case workflow

`frontend/src/api.js` has **no Batch 5 helper functions** — add: `getPurchases`, `getPurchase`, `createManualPurchase`, `editPurchase`, `acceptPurchase`, `createReceiving`, `acceptReceiving`, `getProducts`, `createProduct`, `getMovements`, `getExpiry`, `proposeCommerceAction`.

### 2. Offline Outbox — guard must be lifted (Batch 5 req. 13, 19)

`frontend/src/offline/sync.js` lines 230–231 still throw:
```js
throw new Error('Stock operations are ineligible until a server stock ledger exists.');
```
The ledger now exists. Update to allow `purchase_create`, `purchase_document_upload`, `purchase_receiving_capture`, `inventory_movement` through the outbox. Update `Workspace.jsx` with offline editors for the new operation types.

### 3. Backend Tests — 0% complete (Batch 5 req. 22–23)

Create `backend/tests/test_commerce.py`. Required cases:

| Test case | Key assertion |
|---|---|
| Duplicate invoice (same supplier + reference) | Rejected with `RuleError` |
| Invoice accept | `inventory_events` count unchanged |
| Receiving accept | `inventory_events` delta = undamaged qty only |
| Partial receiving | `delivery_complete=False` ≠ shortage |
| Missing quantity field | Blocked at validation |
| Unit mismatch | Blocked at receiving accept |
| Fractional quantities (2.5 kg) | Accepted; stored as `2.500000` |
| Decimal precision (NUMERIC 20,6) | No rounding artifacts |
| Overdelivery | Recorded; no auto-rejection |
| Stock ledger replay | `SUM(quantity_delta)` = `balance()` |
| Event idempotency | Same `operation_id` → identical receipt, no duplicate event |
| Shortage math | Deterministic paise calculation |
| Manual adjustment requires approve role | Non-approver rejected |
| Conversion precision | Exact 6dp; inexact raises `RuleError` |
| Tenant isolation | Product / purchase / event not visible across stores |
| Proof duplication linked to purchase | Rejected same as case-level |

Also re-run existing 57 supplier workflow tests against PostgreSQL after any schema change — they must continue to pass.

### 4. Documentation

- Write `docs/BATCH-5.md` (this file is the start; finalise after UI and tests)
- Update `docs/HANDOFF.md` to reflect Batch 5 as the current state

---

## Checks at Commit Time

| Check | Result |
|---|---|
| `pytest backend/tests/ -q` | **57 passed, 1 warning** |
| `alembic check` | No new upgrade operations detected |
| `ruff check backend scripts/serve_e2e.py` | **Pass** (1 E401 auto-fixed before commit) |
| `ruff format --check backend scripts/serve_e2e.py` | **Pass** |

> [!NOTE]
> `npm test:offline` and `npm run test:e2e` were not re-run at this commit; the offline guard in `sync.js` has not yet been updated (new operation types are still blocked client-side). Those suites were passing at Batch 4 head and no offline client code changed.

---

## Startup Reminder (unchanged from Batch 4)

```sh
# Check / start PostgreSQL
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /private/tmp/munafa-pg-b23-20261030 status
# Run migration if on a fresh clone
.venv/bin/alembic upgrade head
# Start dev servers
npm run dev
```

Migration head is now `67e38dd313f8`. On any new device, run `alembic upgrade head` before starting the API.
