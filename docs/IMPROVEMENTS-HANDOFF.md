# Five improvements — implementation plan and continuation

Started 31 October 2026 from latest GitHub **7966e04**, fast-forwarded before edits. User requests thorough implementation/testing of demo onboarding, unified dashboard, operational safeguards, OCR evaluation and Android/pilot validation. User also explicitly requires pulling concurrent updates and pushing/handoff before usage-window exit.

## Confirmed scope and external gates

- Password recovery: **one-time recovery codes now; email later**. No sending service configured, no email recovery claim.
- Evaluation access: **synthetic corpus and browser tests only**. Owner explicitly approved a bounded **up to ₹10 Sarvam synthetic OCR run**; no real documents may be sent. Record usage-derived estimates separately from verified billed costs. No real consented invoice paths, handwritten sample ground truth, Android device or merchant participants. Prepare/run available synthetic/software checks, but do not claim actual-device, real-invoice or merchant-pilot completion.
- Backups: **no private destination/paid backup plan supplied**. Implement configurable automation, validation and restore procedures. Do not claim an actual off-host backup exists or provision paid resources.
- No production test-data write is authorised by this new task beyond previous one-time approved demo test (already consumed). Use disposable PostgreSQL tests. Never reset/import/delete existing merchant data.
- Unrelated existing local deletions under starters/regulatory-starter are user changes; never stage, restore or remove them.

## Checkpoint 1 — onboarding + unified evidence-backed dashboard

Planned files: backend/app.py, samples.py as needed, brief.py, records.py; frontend/src/App.jsx, components/BusinessBrief.jsx, DailyRecordsSummary.jsx, DailyRecords.jsx, focused styles; new/updated backend and Playwright tests.

No database migration/dependency. Add backward-compatible brief fields and tenant-scoped record detail/list read boundaries as needed. Reuse latest home snapshot; preserve all-recorded-date/manual labels and existing navigation. Sample reuse must preserve approvals/history and use transaction/concurrency guards; generic duplicate invoice rejection remains. Source-backed review/dues/tasks actions, exact sales/expense totals, original-record routes, freshness, unavailable/zero distinction, no pending draft inclusion.

Tests: repeated/concurrent sample intake returns same case; no received quantities inferred; stage/role/tenant guards; sales vs collections without double-counting; reversals; store-day totals; overdue vs undated obligations; assigned tasks; valid routes and source identity; narrow viewports and complete original recovery flow.

Status: IMPLEMENTED. Explicit demo sample intake is transaction-serialised and reuses the same synthetic case without changing approval/history; generic manual duplicates still reject. Home displays a staged source-backed sample guide and review/dues/task actions. Latest DailyRecordsSummary is preserved and now reads unified /api/brief totals with original-record drilldowns and paginated history. New scoped GET boundaries: /records/entries (50 per page), /records/entries/{id}, /records/customers/{id}, /records/tasks/{id}. No migration/dependency.

Verification before concurrent supplier-performance merge: full backend 313 passed under UTC; targeted onboarding/record/recovery backend 63 passed; 5 focused Playwright journeys passed including demo → reviewed approval, source drilldowns, existing manual records and offline financial draft. Build, Ruff and Prettier passed. New concurrent supplier-performance commit 27f3a35 must be preserved before publishing; rerun its focused checks after merge. Existing UI/source labels and stock/recovery invariants retained.

## Checkpoint 2 — recovery + operational trust

Planned files: additive models/Alembic migration(s), backend/auth.py, security.py, recovery/usage modules, provider-call boundaries, frontend session/account security UI, environment examples, operational scripts/workflows/docs and tests.

Recovery codes: random high entropy, hashes only in PostgreSQL, revealed once on explicit password reauthentication, atomic single use/rotation/expiry, generic denial/rate limits, revoke sessions on reset, no secret/codes in logs/browser caches. Preserve exact password whitespace independently of normalised usernames. No public demo recovery credentials.

Public demo: remote paid-provider calls disabled by default (manual alternatives), explicit configuration gates and PostgreSQL-enforced usage budgets if enabled; no claim estimated reservations equal actual provider invoices. Preserve legacy development-only gate. Retention defaults/plan and safe maintenance, without erasing immutable financial evidence or silently deleting drafts.

Backups: private destination configuration, bounded pg_dump/verification, manifest/checksums, optional supported S3 SDK in ops-only dependency set, scheduled workflow visibly NOT CONFIGURED without secrets, retention/lifecycle proposal and isolated restore rehearsal. No production restore/deletion, unverified backup claim or private export commit.

Tests: migration up/down on scratch schemas, reset replay/expiry/guess/tenant/role/session revocation, secret redaction, cross-worker quota and unavailable providers, dry-run retention and backup failure handling/restore isolation. External storage configuration remains an owner action.

Status: IMPLEMENTED / ISOLATED INDEX-SNAPSHOT REGRESSIONS PASSED. Additive head f237b2e9c014 adds account_recovery_codes (hashes), service_usage_counters and immutable service_usage_events. API recovery-code setup/status/reset/privacy and More account-security UI are implemented; exact password whitespace and viewer logout are fixed. Public-signup provider spending requires explicit operator approval (users.provider_access; old accounts default false, CLI allow-ai/deny-ai). Public demo provider calls are disabled at server boundaries by default, with PostgreSQL-atomic call/reservation caps if explicitly configured. Backend migration/recovery/budget focused checks passed; phone recovery and no-IndexedDB-secret journey passed in isolated spec runner. Initial combined direct auth/recovery run hit the intended shared rate limit; per-spec runner passed without weakening limits.

Optional pinned boto3/SDK (open-source, no service provisioned) in requirements-ops/dev; configurable nightly GitHub backup workflow reports NOT_CONFIGURED with absent secrets. Real read-only PostgreSQL snapshot archive and scratch-only restore pass, including row checksums; private storage/SDK fixtures check encryption, public-access blocking and readback corruption. No external storage has been contacted. Retention plan is read-only; optional security-token cleanup follows a fresh verified backup and is disabled by default. Financial/audit/attachment deletion is never automatic. Ops docs: ops/BACKUP-RECOVERY.md; user recovery docs: ACCOUNT-RECOVERY.md. No new paid provider beyond the already approved Sarvam synthetic evaluation.

## Checkpoint 3 — OCR evaluation + device/pilot readiness

Planned files: evaluation corpus/metadata and evaluation scripts/tests; explicit PDF truncation provenance; private correction/evaluation capture tooling; Android/Playwright/device scripts; docs.

Extend labelled synthetic printed/thermal/script/adversarial coverage; distinguish handwriting proxies from actual handwriting. Record field accuracy/abstention, failures, corrections, latency and measured billing only when real evidence exists. Human correction time and accepted-invoice costs remain unmeasured without actual observations. No real PII in public fixtures; no live provider call until bounded authorisation/configuration is established. Real-data ingestion requires consent and checked ground truth.

Available browser checks: camera/file flows, simulated microphone denial, durable reload and interrupted sync, throttled network/CPU where meaningful. Rebuild same Capacitor source if tooling available; inspect ADB device availability but no invented physical coverage. Provide consent/withdrawal/minimised pilot protocol and evidence matrix using existing scripts/analyse_pilot.py. No actual pilot without consenting merchants.

Status: PLANNED; real invoice/device/pilot evidence BLOCKED BY CONFIRMED ACCESS LIMITS.

## Baseline

Current full regression from preceding checkpoint: 302 PostgreSQL backend tests, 29 browser journeys, 19 frontend/offline tests. Latest concurrent home snapshot adds its own tests; rerun relevant/full checks on the final merged code. Migration head 19b0c9cc7712. Production app https://munafa-paytm-partner.onrender.com. Fetch/inspect remote before every commit/push; do not force-push or overwrite concurrent work.

## Concurrent work preserved

Latest pulled remote: 86d8b17. It enabled dev login in a production blueprint; our resolution keeps ALLOW_DEV_LOGIN=0, removes the committed shared development code from the current file, preserves the concurrent ENABLE_SPEECH_PREVIEW=1 setting as an unvalidated opt-in preview for approved accounts, and keeps PUBLIC_DEMO_AI_ENABLED=0. Do not weaken production startup guards. No actual Render settings were changed by the agent.

Another editor created untracked a1b2c3d4e5f6_store_settings_upi_vpa.py (parent f237b2e9c014) and unstaged UPI/reminder edits in backend/records.py and DailyRecords.jsx. The owner explicitly said **continue these five improvements and preserve parallel work separately**. Those changes must not be staged, overwritten, moved or deleted. Current staged versions contain our source-evidence changes but not the parallel UPI additions. Validate the staged index in a private temporary archive, not the mid-edit working tree; never include that unrelated untracked migration in this checkpoint. Verify the index tree hash is unchanged before committing. Temporary stash 'codex recovery ops before latest Render config merge' is retained as a recovery safety copy after its conflict was resolved; do not pop/drop unrelated stashes.

Latest completed checks before the final provider-approval hardening: full backend 337 passed; full browser 33 passed; target recovery/operations/migration with the approval flag 20 passed; source-evidence/operations 15 passed; personalized provider/assistant target 27 passed. Final snapshot checks must supersede these counts. No real bucket, real data import, device or pilot test has been run. Sarvam synthetic run up to ₹10 is approved but has **not yet been executed**.

Final security checkpoint validation (isolated staged tree 8fb891f64d757e5b57b35d391c90e942de28b2c0): **339 backend tests passed**, **33 Playwright journeys passed**, **19 offline unit tests passed**. Ruff check/format, Prettier and production build passed. The first snapshot exposed accidentally staged parallel model metadata; the index was corrected without altering that editor’s working file and the entire backend rerun passed. Parent remote remains 86d8b17. No skipped device/pilot/storage integration is counted as passing.
