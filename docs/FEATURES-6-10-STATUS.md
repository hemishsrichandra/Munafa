# Features 6–10: implementation checkpoint

User requested checking and implementing five features, retaining the earlier hackathon preference for short, complete increments and clean pushed code. Inspection found none of the five complete. This increment implements feature 10 only; features 6–9 remain unimplemented, not partially enabled. Do not report the whole request complete.

## Delivered: 10. Supplier performance summaries

Suppliers now includes an expandable documented-outcomes report. Each supplier shows unresolved approved claim count and amount; each case shows approved missing/unusable product quantities, linked accepted-receipt damage in original units, recovered/pending money, and hours from case creation to first/full documented recovery. The original invoice/evidence opens through the existing case view.

Read-only endpoint: `/api/supplier-performance`, using existing authentication, read permission and explicit tenant filters on every joined table. No migrations, dependencies or financial writes. Draft shortages are excluded. Promises are not recoveries. Missing damage data is labelled unknown coverage. Missing/unusable quantities can already include damage, so the UI explicitly warns not to add the two. Quantities in different units are never summed. Recovery times do not measure delivery punctuality or infer a supplier rating.

Files: `backend/supplier_performance.py`, router inclusion in `backend/app.py`, `frontend/src/components/SupplierPerformance.jsx`, integration in `LedgerViews.jsx`, backend regression tests and expanded supplier browser journey.

## Remaining work / Antigravity continuation

Read `docs/ANTIGRAVITY-HANDOFF.md` for environment, standing safeguards and prior increment. Then implement these as separate reviewed increments:

6. CSV imports: bounded UTF-8 file parsing, preview with field mapping, strict integer-paise conversion, dates/categories/existing customer references, within-file and existing-store duplicate checks. Preview must perform no writes. Confirmed atomic submission must revalidate all rows and use current `records.Entry`/`record_entry` guards and request idempotency. Opening customer balance imports must be explicit obligations, not balance overwrites. Do not import a payment as a sale.
7. Stock exceptions: persistent store-scoped/versioned settings for exact per-unit absolute correction thresholds and repeat counts/time windows. Evaluate actual accepted correction events, not purchase receipts; retain actor/time/reason and before/after quantities. Never add different units or silently mutate stock when acknowledging flags.
8. Reminder management: stable source/occurrence identity, append-only acknowledgement/snooze history, tenant/user visibility rules, UTC deadlines with store display timezone, duplicate suppression, source revalidation and clear UI for resurfacing. In-memory dismissal or a local-only checkbox is insufficient.
9. Sales observation calendar: persisted merchant-confirmed dates, explicit zero versus observed-positive versus no-information states, source/coverage notes, revision/correction history and future-date guards. Financial ledger entries alone do not prove complete daily SKU sales. Do not enable forecasting/dead-stock conclusions until SKU/day/stockout coverage and evaluation exist.

No external partner access is available. Do not expose `.env` secrets or reset merchant data. Exact paise, fractional quantities, store isolation, permissions, immutable audit and offline conflicts must remain intact. Exclude unrelated local research/output/tmp files from commits. Fetch before pushing because Hemish may push concurrently; never force-push.

Verification: all 3 supplier backend tests passed (cross-store isolation, unapproved exclusion, full recovery timing and accepted fractional damage linkage); all 8 workflow browser journeys passed, including supplier summary expansion and opening the original invoice/evidence, phone navigation and existing full recovery. Build, Ruff, Prettier and diff checks passed. Source audit: 322 files, zero configured-secret findings, zero SQLite imports. No full backend-suite run is claimed for this increment.
