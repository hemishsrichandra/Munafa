# Merchant frontend connections — 31 October 2026

Scope: wire the supplied frontend gap analysis into the existing merchant app, preserving its four destinations and supplier recovery state machine. No schema, framework, application dependency or paid integration added. Existing uncommitted overdue/expiry/supplier-message backend work was inspected and preserved; it must ship with the consuming frontend, not independently afterward.

## Delivered connections

| Entry point                 | Source / action                             | Merchant-visible behaviour                                                                                                                |
| --------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Customer Khata              | GET /api/records/summary                    | Overdue amount and maximum days late alongside pending balance; no inference from payments                                                |
| View account history        | GET /api/records/customers/{id}             | Original obligation links, recorded due dates and individual days late                                                                    |
| Received Payment            | Existing reviewed entry and allocation flow | ₹100/₹200/₹500 and exact full-balance chips; amounts above the balance disabled; selecting does not confirm or save                       |
| Deliveries & Stock → expiry | GET /api/inventory/expiry                   | Batch cards, urgency text/colour, expired handling, recorded quantity/unit, known-cost estimate and missing-cost distinction              |
| Today → Open expiry radar   | Same expiry endpoint, /stock/expiry route   | Only actual critical/expired batches create attention; direct route lands on expiry rather than attempting a product lookup               |
| Today → Review reminder     | POST /api/records/customers/{id}/reminder   | Permission-aware busy/error state and reviewed draft; no automatic window opening or send/payment claim                                   |
| Supplier claim → message    | POST /api/cases/{id}/message                | English/Hindi/Kannada buttons, approved amount, original translation comparison, fresh proposal version and backend-supplied WhatsApp URL |
| Add/review bill             | Existing purchase draft APIs                | Clear bill-first/delivery-second explanation; total visible; subtotal/tax/discount/rounding disclosed on demand without discarding values |

Supplier handoffs require review after each language change; numeric mismatches, stale case versions or invalid URLs block the link. Only HTTPS wa.me destinations without embedded credentials are allowed. Missing/failed drafts show retry; language loading clears the previous draft to prevent sharing the wrong one. No cloud call was made for validation; provider paths are mocked or use deterministic existing templates in the isolated demo.

Expiry discounts are existing **heuristic proposals based on the latest accepted purchase cost**, not measured optimal prices, retail-price discounts or proven losses. UI states this explicitly. Arithmetic now uses Decimal and explicit HALF_UP to integer paise, and the draft preserves paise instead of truncating to whole rupees. No model performs financial calculations. No freshness claim is invented for an expiring batch. Expired goods have no promotional handoff. A clearance draft requires review of the physical batch, price, content and permission to receive offers; WhatsApp remains a merchant-selected handoff, never an automatic broadcast or delivery receipt.

Today overdue text now preserves cents. Existing whole-rupee wording remains compatible. No received quantity, stock event, credit application or financial approval is inferred by these UI changes.

## Verification

- `npm run build`: passed; React/Vite production build and versioned PWA shell.
- `TZ=UTC .venv/bin/python -m pytest backend/tests -q`: 357 passed on the integrated existing backend contracts. Two additional tests then covered fractional expiry-price rounding and overdue cents; final affected suite `backend/tests/test_unified_brief.py backend/tests/test_merchant_connections.py -q`: 10 passed.
- `npm run test:offline`: 20 passed.
- Ruff check/format and Prettier: passed before final documentation update; rerun final formatting check before publishing.
- `npm run test:e2e`: **36 passed** in the final full per-spec runner. Includes accessibility, four destinations, new real API-backed phone journey, purchase/receiving/recovery, offline reconnect/idempotency and account workflows.

The new phone test creates synthetic records in a disposable PostgreSQL schema and follows Today → reminder review → expiry detail → clearance review → Khata history → payment chips, verifying paise and review reset. It does not open WhatsApp or send a message. Existing recovery tests now explicitly acknowledge message review; accounting tests expand the new details section before entering tax/rounding. Assertions were not weakened.

Failures encountered and fixed: a disabled anchor needed an explicit link role for its accessible disabled state; the initial new test used a Khata sub-tab label instead of the main-navigation label; the new backend assertion initially assumed a list where movements returns an events object; the restored accessibility runner found low contrast in existing bill-dialog sample text, now repaired. Whole-rupee compatibility remains covered while new tests preserve cents.

The repository's locked accessibility package was missing locally; `npm ci --ignore-scripts` restored the existing lock without changing manifests. npm reports an existing Node engine warning (axe package requests Node >=22.12; local Node20.20.2) and four moderate dependency advisories. No automatic/major dependency upgrades or audit suppression were performed. Browser checks run on Chromium; physical Android, release signing, real speakers/merchants and production provider quality are not implied by this web release. Off-host backups and live Paytm authorisation remain externally gated as previously documented.

Unrelated local deletions under starters/regulatory-starter are excluded. No production database migration/reset, production synthetic record creation, provider spend or secret changes were performed.

Final checkpoint: 357 full backend tests passed; final affected brief/expiry suite 10 passed (including two new regressions), all 36 browser journeys passed, and 20 offline unit tests passed. Production build, accessibility scan, Ruff and Prettier passed. Earlier failed attempts were corrected and rerun; no skipped check is counted as passing. No physical-device or production rollout verification is claimed.
