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

### Current checkpoint — 30 October 2026

Batches 6–7 prototype implementation is delivered after the pulled Batch 5 completion. Deterministic fixture-backed payment reconciliation, evidence-linked brief and curated-source help work without cloud keys. Extraction/translation remain optional reviewed proposals; speech is disabled by default pending validation. Empirical provider/merchant/device acceptance and live Paytm integration are external gates, not completed benchmarks. Read HANDOFF.md before the next batch; Batch 8 requires explicit authorisation and truthful prerequisite checks.

### Batch 9 prerequisite status

P2 readiness reporting and safety gates are implemented; actual procurement, financial/lender planning and benchmarking remain blocked. Relevant P1 foundations and quality are unproven, and turning on feature flags cannot change that. Own SKU history links are the safe alternative to unavailable peer comparisons. Batch 8 remains unimplemented; no next implementation should begin without specific authorisation and the prerequisites in BATCH-9.md.

### Batch 10 — demo candidate, not production sign-off

Integration/hardening is verified locally (210 backend / 21 browser / 17 frontend unit tests, synthetic restore rehearsal and debug APK). BATCH-10.md records explicit pass/skipped/unavailable results and remaining acceptance. Follow DEMO.md without deleting real audit history. Next work requires a separately authorised device/provider/deployment/merchant-validation scope; Batch 8/P1 absence and P2 gates are unchanged. Do not treat a successful synthetic demo as Paytm integration, growth evidence or legal/security certification.
