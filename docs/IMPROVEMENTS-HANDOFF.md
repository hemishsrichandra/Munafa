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

Status: PLANNED, gated configuration confirmed.

## Checkpoint 3 — OCR evaluation + device/pilot readiness

Planned files: evaluation corpus/metadata and evaluation scripts/tests; explicit PDF truncation provenance; private correction/evaluation capture tooling; Android/Playwright/device scripts; docs.

Extend labelled synthetic printed/thermal/script/adversarial coverage; distinguish handwriting proxies from actual handwriting. Record field accuracy/abstention, failures, corrections, latency and measured billing only when real evidence exists. Human correction time and accepted-invoice costs remain unmeasured without actual observations. No real PII in public fixtures; no live provider call until bounded authorisation/configuration is established. Real-data ingestion requires consent and checked ground truth.

Available browser checks: camera/file flows, simulated microphone denial, durable reload and interrupted sync, throttled network/CPU where meaningful. Rebuild same Capacitor source if tooling available; inspect ADB device availability but no invented physical coverage. Provide consent/withdrawal/minimised pilot protocol and evidence matrix using existing scripts/analyse_pilot.py. No actual pilot without consenting merchants.

Status: PLANNED; real invoice/device/pilot evidence BLOCKED BY CONFIRMED ACCESS LIMITS.

## Baseline

Current full regression from preceding checkpoint: 302 PostgreSQL backend tests, 29 browser journeys, 19 frontend/offline tests. Latest concurrent home snapshot adds its own tests; rerun relevant/full checks on the final merged code. Migration head 19b0c9cc7712. Production app https://munafa-paytm-partner.onrender.com. Fetch/inspect remote before every commit/push; do not force-push or overwrite concurrent work.
