# Build progress and handoff

Last updated: **29 October 2026**. Offline hackathon: **31 October 2026, Bengaluru**.

## Current state

The initial local prototype is implemented. The React/Vite frontend and FastAPI/SQLite backend run together with `npm run dev`. The API can also serve the compiled frontend with `npm run build` followed by `npm start`.

The folder is initialized as a Git repository on `main`, with `origin` linked to `https://github.com/hemishsrichandra/Munafa.git`. The remote was empty when inspected. The initial prototype is tracked on `main`. Use `git log -1` to identify the current revision and `git status --short --branch` to check local changes and upstream synchronization.

## Completed

- Reviewed all nine source slides and refined the build around shortage-to-resolution.
- Added responsive Overview, Credit cases, Suppliers and Insights views.
- Implemented synthetic, manual, Sarvam text and Sarvam-hosted image intake.
- Added editable invoice fields and merchant receiving/unit/delivery/pricing confirmation.
- Implemented deterministic integer-paise calculations and approval gates.
- Added immutable approved evidence snapshots and invalidation after edits.
- Added downloadable PNG evidence and previewable supplier messages.
- Added Sarvam Hindi/Kannada translation with English comparison.
- Kept WhatsApp sharing manual and required separate merchant sharing confirmation.
- Added supplier promises, follow-up dates, overdue visibility and audit history.
- Added case-owned proof attachments, partial/full credit and refund verification.
- Added unique credit/refund references and proof-content deduplication within transactions.
- Added exact field matching for the supported synthetic credit fixture.
- Added optimistic versions to prevent stale-tab overwrites.
- Added CSV export, synthetic sample files and a reset command preserving merchant cases.
- Added dependency lockfiles, environment template, `.gitignore` and formatters.
- Documented architecture, setup, demonstration, limitations and the remaining roadmap.

## Verification

- **36 backend/domain/API tests pass**, including mocked Sarvam contracts and failures.
- Production frontend compilation passes.
- Python Ruff checks and formatting pass.
- Frontend/Markdown Prettier formatting checks pass.
- Desktop and mobile browser tests exercise the ₹80 workflow, PNG download, promises, closure, persistence, supplier/insight navigation and manual entry.
- Desktop and mobile screenshots were visually inspected during development.
- Browser tests use a separate local database; they do not modify the main workspace data.

A non-failing Starlette test-client deprecation warning is present with the pinned HTTPX dependency. Runtime behavior and tests pass; migrate the test client dependency when the framework transition is evaluated.

## Live integrations and scope limits

**No Sarvam key or credits were provided. Live Sarvam extraction/translation has not been tested.** Endpoint/header/model contracts and error paths are tested with mocks. Add the hackathon account key and validate actual account/model access before claiming a live AI demo or partner credit eligibility.

No live Paytm connection, automatic supplier sending, production authentication or multi-store isolation exists. The prototype is intentionally bound to loopback. Real proof verification is a merchant attestation with identifier/amount rules, not independent document-authenticity validation.

## Next implementation steps

1. Configure Sarvam credentials and run real text/image/translation checks. Log latency, accuracy and credit usage.
2. Evaluate more invoice variations and add regression fixtures for real extraction failures.
3. Record the demo video and update the final presentation with working screenshots. These submission deliverables are not yet produced.
4. Validate recent shortage/credit workflows with 3–5 merchants.
5. Add authentication, store isolation, PostgreSQL, private storage, backups and upload/deployment protections before a real merchant pilot.
6. Expand to fractional quantities, explicit unit conversions, multilingual receiving and evidence-assisted credit matching after validation.

See `ROADMAP.md` for priorities and acceptance criteria, and `DEMO.md` for the rehearsal script. The README contains all start, build, test and reset commands.
