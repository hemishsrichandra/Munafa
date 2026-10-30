# Batch 4 completion report: offline drafts and synchronisation

Date: **30 October 2026**. Implemented incrementally on the existing Batch 2/3 React/Vite and FastAPI/PostgreSQL foundation. No future merchant module, stock ledger, forecast, live analytics or live Paytm integration was added.

## Changes and purpose

- Added `frontend/src/offline/db.js`: versioned IndexedDB stores for verified context, minimal receiving cache, invoice/receiving drafts, attachment blobs, outbox and sync status. Scope checks run inside each transaction. Queue creation and dependencies are atomic; queued requests are frozen.
- Added `sync.js`: persisted six-state lifecycle, multi-tab leases, dependency order, bounded batches, full-response timeout, exponential backoff/jitter, automatic attempt cap and explicit retry/conflict handling.
- Added `provider.jsx` and `Workspace.jsx`: phone-accessible Drafts & sync with local save/preview/notes, manual invoice entry, receiving drafts, file capture, quota errors, last-synced status, local backups, human conflict comparison and non-production count-only diagnostics.
- Updated session/API/PWA/App integration: whitelisted identity-only offline grant, context purge on verified identity/role change, sign-out cleanup/revocation marker, abortable calls, foreground/online resume and server-view refresh after attempted sync. Public service-worker caching remains separate from private data.
- Added `backend/sync.py`: strict allowlist of `invoice_create`, `receiving_save`, `attachment_upload`; reuses server-derived store scope, existing case rules, optimistic versions and PostgreSQL transactional operation receipts. Adds append-only operation audit provenance. No offline approval/recovery/message command exists.
- Updated tests, CI, README, architecture, progress and next-chat handoff. Added [sync protocol](SYNC-PROTOCOL.md) describing actual storage, wire contract, state machine, failure handling and threat model.

## Schema, API and dependencies

Server schema: **unchanged**, Alembic head `37c45f100e71`; `alembic check` reports no drift. Existing PostgreSQL `idempotency_operations` uniqueness/transaction guarantees are reused. No migration, legacy import, reset or real-data deletion occurred.

API: added authenticated `POST /api/sync/operations` with operation UUID matching Idempotency-Key, schema version, entity/version, client time, prerequisites and validated payload. Auth login/me now returns verified `user_id` for namespace construction. No tenant ID is accepted from the client. Repeated accepted requests return the original receipt; changed-body reuse conflicts.

Client schema: IndexedDB version 1, documented in SYNC-PROTOCOL.md. There is no SQLite/local SQL adapter and no new runtime state library. Only new dependency in this batch: **fake-indexeddb**, test-only, locked in package-lock.json. No new environment variable, provider credential or permission is needed.

## Invariants preserved

Manual physical received quantities, matching units, completed-delivery/pricing checks, deterministic integer-paise/Decimal calculations, exact approval snapshots, supplier promise ≠ recovery, proof/reference deduplication, append-only history and optimistic versions remain enforced. Offline receiving is restricted to unapproved cases and cannot replace accepted evidence. An attachment never determines physical quantity. Cached values and pending operations are not presented as accepted stock, recovery, payments or messages.

No inventory draft is eligible until a server stock ledger exists; the reserved polymorphic draft shape is documented and unsupported kinds are rejected. This avoids silently starting a later batch.

## Verification

| Command / check                                                                | Verified result                                                                            |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `npm test`                                                                     | **57 backend tests pass** on PostgreSQL 17.11; original supplier regression suite retained |
| `npm run test:offline`                                                         | **12 IndexedDB/state/transport unit tests pass**                                           |
| `npm run test:e2e`                                                             | **14 Playwright tests pass** using isolated PostgreSQL schemas/stores                      |
| `.venv/bin/alembic check`                                                      | No new upgrade operations detected                                                         |
| `.venv/bin/ruff check backend scripts/serve_e2e.py`                            | Pass                                                                                       |
| `.venv/bin/ruff format --check backend scripts/serve_e2e.py`                   | Pass                                                                                       |
| `npm run format:check`                                                         | Pass                                                                                       |
| `npm run build` / `npm run android:sync`                                       | Pass; same PWA assets packaged into Android                                                |
| `JAVA_HOME=... ANDROID_HOME=... ./gradlew assembleDebug lintDebug --no-daemon` | BUILD SUCCESSFUL; existing 0-error/28-warning Android lint result                          |
| APK signature / source parity                                                  | Signature verifies; every packaged public asset byte-matches current frontend/dist         |

The browser timeout test lets the server commit, deliberately delays its reply past the actual **12-second client timeout**, reloads/retries the frozen operation and verifies one case/capture event plus the original idempotent receipt. Other tests cover attachment response loss and exact retry bytes, offline draft reload, quota failure preserving old/new input, expired auth/same-account resume, account switch, stale receiving conflict and unchanged server counts. Existing 360/390/430/narrow/rotation and invoice-to-recovery tests pass.

Unit checks cover transaction abort, reopen durability, claim exclusion, frozen payloads, retry cap, scope/role changes, future-schema refusal, pending-data retention and attachment dependency/cleanup. PostgreSQL tests cover duplicate IDs/changed bodies, tenant spoofing, role denial, invalid quantities, checksum/partial-file rejection, prerequisite guards, financial-state denial and one accepted operation audit.

Evidence: ignored `test-results/offline-draft-phone.png` was visually inspected at 390px. Existing phone/workflow/offline-shell screenshots are also regenerated by tests. No private merchant documents were used.

## APK and explicit limits

Updated local debug artifact: `artifacts/munafa-debug.apk`, **4,333,280 bytes**. SHA-256:

```text
f385c75e9a39f1b2b0dcfe4c737cd29e009b4a8de724c43bce7f950409a829a5
```

Built with Java 21.0.13+9, Gradle 8.11.1 and SDK 35; temporary tool locations and exact commands remain in HANDOFF.md. The generated instrumented test’s package assertion now matches the actual app identifier; it has not run on a device.

No hosted HTTPS backend is configured in this APK. First connected sign-in needs an owner-provided endpoint and deliberate native-origin CORS configuration; without it, only the public shell is available. Real Android process-kill, WebView persistence/quota, camera/file/share, native Back, installation/update and encrypted-device behavior are untested. No release signing or production readiness is claimed. Browser tests do not establish those native properties.

One non-failing Starlette HTTPX test-client deprecation warning and existing Gradle/template/plugin warnings remain. No test/lint suppression was added. CI was updated but its remote result is not claimed before GitHub runs it.

## Retention and operational risks

Cached unapproved receiving sources expire after 24 hours. Synced draft copies expire after seven days. Unsynced/failed/conflicted data is retained until explicit discard/sign-out, with >30-day proposals paused for review. Raw attachments are capped at 4 MB each/40 MB per context. A transaction failure never silently deletes a saved draft. JSON backup includes fields, not attachment bytes.

This app does **not** provide device-level encryption at rest, forensic secure deletion, guaranteed browser persistence, automatic cloud backup of unsynced drafts, background delivery or cross-device recovery. Same-origin scripts/unlocked-device users may access IndexedDB. Browser eviction can erase pending work. The UI and protocol state these limits; original documents should be retained separately.

## Handoff and next phase

The owner requested a Git push before exit. The commit includes the previously uncommitted Batch 2/3 foundations plus Batch 4 source, tests and documentation; private env/data/build artifacts are excluded. Consult HANDOFF.md and Git history for the exact pushed revision.

Batch 4 is complete within the verified scope above. **Wait for the owner’s Batch 5 prompt.** No remaining master-playbook requirements should be inferred or implemented automatically. Before a connected/device demo: configure HTTPS, test a physical Android device and evaluate storage pressure/app update behavior. Before a merchant pilot: deployment authentication operations, least-privilege DB access, backups/restores, file scanning/retention and live provider evaluation still need infrastructure and validation.
