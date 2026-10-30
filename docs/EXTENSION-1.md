# Extension 1 — Commerce and communications

Date: 30 October 2026. **Partial implementation; live integration BLOCKED.**
The owner confirmed no provider access, CA reviewer or consented pilot is available.

## Scope and evidence

- `backend/integrations.py`: internal versioned commerce-page, device-observation and message-draft contracts; exact rupee boundary; fail-closed connector; authenticated readiness API.
- `frontend/src/components/Integrations.jsx`, `App.jsx`: More → Connections & readiness, loading/error/offline/refresh states. No credentials or raw provider payload displayed. No API cache added.
- `backend/tests/test_integrations.py`: synthetic internal-contract tests, not official provider contract tests.
- `backend/app.py`: registered authenticated router. Existing payment ingestion/reconciliation remains authoritative; supplier recovery unchanged.
- No migrations, dependencies, provider calls, public webhooks, messages or destructive operations.

## Provider verification

| Capability                      | Actual status           | Missing gate                                                                                                       |
| ------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Paytm transactions/settlements  | BLOCKED — ACCESS        | Authorised merchant/product, enabled APIs, current authentication pack, successful contract test                   |
| Paytm webhook / polling overlap | BLOCKED — SPECIFICATION | Exact authorised event, signature/replay/acknowledgement and pagination contract                                   |
| Soundbox/POS                    | BLOCKED — SPECIFICATION | Device ownership mapping and supported telemetry API; missing data is unavailable, never inferred offline          |
| WABA send/status                | BLOCKED — ACCESS        | WABA/registered number, versioned contract/templates/policy, contact consent/revocation and exact-content approval |
| Existing settlement fixture     | DEMO ONLY               | Existing internal fixture adapter; never live data                                                                 |
| Existing WhatsApp link          | Manual handoff          | No delivery receipt or automatic send                                                                              |

Checked official [Paytm settlement order detail](https://www.paytmpayments.com/docs/api/settlement-order-detail-api/) on 30 October 2026: still production-only, not hosted on staging. The documentation URL differs from the older business.paytm.com page; **no endpoint was copied into a live connector** without the authorised account integration pack. Public docs do not establish entitlement. No API version for this account is verified.

Official [Meta overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview) and [webhook documentation](https://developers.facebook.com/docs/graph-api/webhooks/getting-started) fetch attempts returned HTTP 429. Current API version, signature, retry, pricing and policy claims remain unverified. No wire schema/signature guessed.

## Acceptance checklist

| Plan gate                                        | Result                                                                | Evidence                                                                                                             |
| ------------------------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Authorised live Paytm capability / contract test | BLOCKED                                                               | Owner has no access                                                                                                  |
| Duplicate financial events prevented             | PASS for existing DEMO path; live BLOCKED                             | Existing PostgreSQL payment regression tests; no new ingestion path                                                  |
| Deterministic, evidence-only settlement reasons  | PASS for existing DEMO path                                           | Existing reconciliation tests                                                                                        |
| Supported device health only                     | PASS safety boundary; telemetry BLOCKED                               | Missing/stale/future observations never produce fault alerts; internal fixture tests only                            |
| WABA consent/approval and real receipts          | BLOCKED                                                               | All send/verification execution disabled; draft schema is not a consent registry                                     |
| Live/demo separation                             | PASS for current paths                                                | Explicit modes; existing demo-only importer unchanged                                                                |
| Tenant/secret controls                           | PASS for status API                                                   | Authenticated middleware, no merchant payload/configuration reflected; full release suite rerun after all extensions |
| Munafa regressions                               | Focused payment PASS; full suite pending final extension verification | See consolidated report                                                                                              |

## Commands and limitations

- `.venv/bin/python -m pytest backend/tests/test_integrations.py backend/tests/test_payments.py -q --tb=short`: **24 passed**, 0 skipped, one existing Starlette deprecation warning. Initial sandbox-restricted run: 20 passed/4 setup errors (loopback denied); same tests passed with approved loopback access.
- `.venv/bin/ruff check backend/integrations.py backend/tests/test_integrations.py`: PASS.
- `npm run build`: PASS, 12 public PWA assets.
- No new schema: rollback is code rollback, not a database migration.
- Full phone/PWA/Android regression evidence is recorded in the final extension report after subsequent shared UI additions. No real device, provider failure, signature or delivery test is claimed.

Next: source-linked local preparation, without filing/lender submission. Later connector work requires the exact integration pack and independent consent/review implementation; merely adding a token cannot enable this connector.
