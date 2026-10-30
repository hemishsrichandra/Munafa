# Approved batch boundaries and next work

## Current scope � Batch 5 completed

The owner authorised Batch 5 completion from the attached status report. The purchase register, invoice review, physical receiving, SKU/stock, expiry and offline commerce workflows are now implemented. See [Batch 5](BATCH-5.md) and [handoff](HANDOFF.md). Future batches require a new scope. Earlier authorisation notes below are historical.

## Historical report

Batches 2 and 3 were authorized together, sequentially. They cover PostgreSQL/trust foundations, then the mobile PWA and shared Android shell. Batch 4 was subsequently authorized with a Git push and cross-session handoff. Future batches remain unapproved.

## Batch 4 complete; wait for Batch 5 scope

IndexedDB drafts, scoped receiving cache, attachment capture, durable outbox, bounded dependency-order sync, exact-operation retries and human-reviewed conflicts are implemented. No inventory, forecast or live analytics module was added. See BATCH-4.md and SYNC-PROTOCOL.md.

The owner must supply/approve the next batch before implementation. Preserve pending/server-accepted distinctions, operation IDs and expected versions as future event types become eligible. Do not assume the remaining master-playbook details from this roadmap alone.

## Later merchant features, subject to approval

1. Reviewed purchase/receiving records feeding an append-only stock ledger.
2. Explicit sale, return and adjustment evidence before claiming stock accuracy.
3. Customer-credit ledger before receivable reminders.
4. Authorized payment/refund/settlement records before reconciliation.
5. Source-linked daily actions from accepted records; do not invent operational data.
6. Threshold reordering before forecasting; evaluate forecasts against simple baselines when sufficient real history exists.
7. Sarvam extraction/speech evaluation with account access, provenance, correction-adjusted time and cost measurements.

## Outstanding validation and operations

Actual Android device installation, camera/file/share/download behavior, production signing and deployment, live-provider contracts, merchant discovery and the final submission video/presentation remain separate. A passing headless test does not prove installed-device behavior or merchant impact.

Before any real pilot: review deployment access, DB privileges/backups, retention, file scanning, privacy notices and support procedures. Validate with 3–5 consenting merchants before scaling. Measure verified recovery, correction-adjusted task time, useful completed actions, false alerts and repeat use. The original subscription amount remains a pricing hypothesis.
