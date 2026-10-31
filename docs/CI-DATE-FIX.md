# GitHub CI store-date regression fix

31 October 2026. The supplied GitHub log shows two failures: test_cross_store_every_entity_endpoint_and_same_store_shared_access received a promise-date validation 409 instead of its expected cross-tenant 404; test_complete_shortage_to_resolution_and_export received the same 409 instead of accepting a same-day promise. The server correctly requires a follow-up on/after the authenticated store's business date. The tests used host date.today() or UTC date, which is the preceding calendar day in Asia/Kolkata between 18:30 and 23:59 UTC.

The latest remote had changed one fixture to UTC tomorrow, but the full workflow and new manual-record future-date tests still used host dates. That partial fix is superseded by the explicit store-timezone helper.

## Changes

- backend/tests/clock.py reads the authenticated store timezone and constructs merchant_today using ZoneInfo.
- Existing promise/recovery and cross-store fixtures use that date; existing 200/404 assertions are retained.
- Both existing flows now run immediately before/after Indian midnight (18:29/18:31 UTC) using a test-only domain/fixture clock. Actual server-session expiry keeps its real clock.
- Additional boundary checks assert store-yesterday is rejected with 409, failure leaves case version/status unchanged, and store-today is accepted.
- Manual-record date inputs/future-date assertions also use the store calendar, preventing the same failure from resurfacing in the new module.
- GitHub job explicitly sets TZ=UTC. No production date validation, state rules, permission/tenant guards or runtime code were changed. No test was skipped or weakened.

## Verification

`TZ=UTC .venv/bin/python -m pytest backend/tests -q`: **302 passed**, one existing Starlette/httpx deprecation warning. PostgreSQL only; generated disposable schemas with all migrations through 19b0c9cc7712. This supersedes older 245/268/276/targeted-run results for the current merged code.

Ruff check and format: passed, 62 Python files. Source/bundle audit: 263 files, zero known-private-configuration matches, zero SQLite imports, 80 API operations. These bounded checks are not a security certification. Frontend/offline tests: 19 passed. Complete Chromium browser suite: **29 passed**, including daily records, header, authentication, full supplier recovery and offline flows. Production PWA build and Prettier check passed.

An initial in-progress targeted run encountered a helper variable typo introduced during the repair. It was corrected before the final full run above. No malformed fixture was accommodated by weakening production checks.

Only tests, CI configuration and documentation need publishing. No Render variable change, database reset/import or operator migration is required by this CI fix. The newer manual-record release already carries its own additive migration instructions. GitHub Actions must run again on the pushed revision; local success is not reported as an observed remote CI result.
