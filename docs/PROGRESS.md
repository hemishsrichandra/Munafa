# Build progress and handoff

## Current status � Batch 5

Batch 5 purchase, physical receiving, inventory and offline commerce work is implemented locally. See [Batch 5](BATCH-5.md) for delivered scope and [handoff](HANDOFF.md) for current verification. The Batch 2�4 report below is historical; its instruction to wait for Batch 5 is superseded by the current user request.

## Historical report

Updated **30 October 2026**. Batches **2, 3 and 4** implemented in the existing Munafa repository. No Batch 5 feature was started. The owner authorized committing and pushing the completed work before handoff.

## Completed product and foundations

- PostgreSQL-only SQLAlchemy/Psycopg persistence and Alembic; normalized tenant/store membership and supplier workflow records. No SQLite application/test fallback or startup DDL.
- Exact fractional quantities and BIGINT paise, immutable approval snapshots, append-only audit/financial/resolution events and rebuildable recovery projection.
- Session authentication, CSRF, role/store checks, bounded concurrency, operation receipts and exact version/digest-bound approvals.
- Original invoice → physical receiving → approval → manual sharing confirmation → supplier promise → proof-backed recovery remains working.
- Mobile Home/Purchases/More, actual-record brief, PWA public-shell install/update/offline launch and same-source Capacitor Android wrapper.
- IndexedDB private receiving cache, manual invoice/receiving drafts and attachment capture; durable frozen outbox with dependency order, leases, bounded retries and explicit conflicts.
- Offline draft reload and same-account reauthentication preserve saved work. Sign-out/account/role change clears private context. No offline approval, financial recovery, messaging or stock mutation is eligible.

## Verified results

- **57 backend tests**, PostgreSQL **17.11**, isolated disposable schemas/stores.
- **12 IndexedDB/state-machine tests**, including transaction quota abort, leases, immutable payload, context purge, schema refusal and attachment cleanup.
- **14 Playwright tests**, including actual client timeout after acceptance with duplicate-proof replay, offline reload, attachment retry, auth expiry, quota and stale receiving.
- Ruff, Prettier, production PWA build and Alembic metadata check pass.
- Capacitor sync and Java 21/SDK 35 `assembleDebug lintDebug` pass. Android lint: 0 errors, 28 existing warnings. APK signature and packaged frontend byte parity verified.
- APK `artifacts/munafa-debug.apk` and screenshots `test-results/` are ignored local artifacts. See BATCH-4.md for checksum, commands and limitations.

## Current environment

Ignored private `.env` configures a fresh local PostgreSQL cluster on **127.0.0.1:55432**, database `munafa_b23`. Tests use generated schemas, not public application tables. An explicitly labelled synthetic A-104 demo store was seeded without reset. Legacy `.data/*.db` files remain untouched.

The development UI/API can be started with `npm run dev`. Port 5173 is Vite; the built PWA is served at port 8000. Detailed restart commands, tool locations and sign-in instructions are in HANDOFF.md. Never print or commit the private development access code.

## Remaining work and decisions

1. Owner review and **explicit Batch 5 prompt** before more implementation. Do not infer future scope from the roadmap.
2. Hosted HTTPS API and real Android device validation: login, offline restart, process kill, storage pressure, file/camera/share, native Back and install/update. No release signing/device-level encryption is implemented or claimed.
3. Production authentication operations, least-privilege PostgreSQL role, verified backups/restores, deployment protections and data retention/scanning require infrastructure and operational review.
4. Authorised Sarvam account/model checks, correction-adjusted accuracy/time, latency/cost evaluation remain unverified. No live Paytm connection exists.
5. Merchant research/evaluation, final presentation, submission video and production rollout remain outstanding. No business outcome improvements are claimed without measurement.

For the next chat read **[HANDOFF.md](HANDOFF.md)** first, then [Batch 4](BATCH-4.md), [sync protocol](SYNC-PROTOCOL.md) and the actual source/tests. Earlier [Batch 2](BATCH-2.md) and [Batch 3](BATCH-3.md) reports preserve their historical validation context; current behavior is documented above.

## 30 October 2026 — Batches 6 and 7

Pulled Batch 5 completion `cba2166`. Batch 6 checkpoint `9408088` adds deterministic component reconciliation, isolated synthetic payment observations and source-linked daily brief. Batch 7 adds strict bounded extraction, persistent invalid-output budget, reviewed language/voice drafts, scoped cited help, synthetic corpus/evaluator and data-handling notes. Full verification: 101 backend + 18 browser + 14 IndexedDB tests; production/PWA and Android debug build/lint pass. Live Paytm, measured provider comparisons and real language/device/merchant studies remain explicit gates. See HANDOFF.md for cross-system setup, preserved invariants and remaining work. Batch 8 was not implemented.
