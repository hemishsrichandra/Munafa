# Batch 6 — payments, reconciliation and daily brief

Implemented 30 October 2026, incrementally on GitHub Batch 5 `cba2166`. Migration `ec82825043aa` follows `67e38dd313f8`.

## Delivered

- Immutable PostgreSQL payment/refund/reversal observations, settlement batches and lines; BIGINT paise, TIMESTAMPTZ, store/mode composite ownership, source uniqueness and append-only triggers. Logical event IDs permit multiple partial refunds and duplicate/out-of-order status observations. Conflicting equal-time observations require review.
- Typed internal adapter boundary, fixture-backed isolated DEMO import, disabled LIVE adapter. No unauthenticated ingestion endpoint or guessed signature algorithm.
- Deterministic component net, missing-field handling, timing/cutoff/fee/GST/refund/reversal/adjustment/uncorrelated/stale review candidates. Difference is not a missing-money claim. Payout reference is not verified bank receipt.
- Authenticated `/api/payments?mode=live|demo`, `/api/payments/{id}?mode=...`, administrator `/api/payments/demo`, disabled `/api/payments/live/connect`, `/api/brief`.
- Home brief ranks up to seven actual source-backed settlement exceptions, approved open supplier claims/promises, merchant SKU thresholds and actual lot expiries. No padding, receivables or forecasts. Every action has source IDs, typed route, status, freshness and demo/live marker. Yesterday's activity is explicitly partial recorded observations, not a complete accounting total.
- Phone payment component cards and concrete source navigation. No authenticated response is added to service-worker caching.

## Integration status

| Integration                                  | Status                                                                        |
| -------------------------------------------- | ----------------------------------------------------------------------------- |
| Payment demo                                 | Working, explicitly loaded synthetic fixture in isolated demo store           |
| Reconciliation                               | Working deterministic service over recorded components                        |
| Existing supplier / stock source actions     | Working; source IDs retained                                                  |
| Live Paytm / authentic webhook               | Disabled: authorisation, environment, signature contract and E2E test missing |
| Manual settlement import / bank verification | Not implemented; no unreviewed import path                                    |
| Payment export                               | Not supplied; supplier export remains unchanged                               |

See [PAYTM-INTEGRATION.md](PAYTM-INTEGRATION.md) for official documentation and the external gate checklist.

## Validation and migration

PostgreSQL **17.11**. Full backend suite: **85 passed** (75 existing + 10 Batch 6 cases including parameter cases); existing Starlette test-client warning remains. Includes exact paise validation, multiple refunds, out-of-order events, duplicates/content conflicts, missing/stale/timing fields, tenant/mode isolation, role denial, DB immutability, migration down/up in empty disposable schemas and legacy commerce/recovery tests. Production/PWA build passed. Browser evidence and final complete-suite results are consolidated in HANDOFF.md after Batch 7.

Additive development migration applied after private `artifacts/private/pre-batch6-postgres.dump`; archive contents verified with pg_restore --list, restore not tested. No existing record import/reset/rewrite. `alembic check` reports no drift. On another system provision PostgreSQL privately then `alembic upgrade head`. Never downgrade populated provider tables without backup verification and explicit approval. Existing backup/restore guidance in BATCH-2.md applies.

## Limits / next batch

No live Paytm integration, merchant outcome uplift, bank verification, complete daily coverage, Android device or real provider validation claimed. Source queries are prototype-sized; pagination/query-plan work is needed before large-store deployment. Continue directly to authorised Batch 7; Batch 8 is future context, not implemented.
