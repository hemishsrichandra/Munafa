# Extension 3 — Evidence and validation

30 October 2026. **Readiness and offline measurement tooling implemented; real-world evaluation/pilot BLOCKED.**

## Changes

- `backend/intelligence.py`, `backend/app.py`: authenticated store-scoped readiness API. Accepted event kinds remain distinct; sale-day observations are not coverage. Reports per-SKU units, event counts, source versions, known sale-date bounds, unknown missing/stockout intervals and merchant threshold. All forecasts disabled; peer statistics suppressed without any cross-store data query. Empty and explicitly truncated catalogue states are reported.
- `frontend/src/components/Intelligence.jsx`, `Integrations.jsx`: phone-friendly readiness, empty/loading/error/snapshot states under the existing More entry. No invented confidence, benchmark or pilot result.
- `scripts/evaluate_forecast.py`: private offline frozen-origin time-holdout baseline comparison with exact-decimal MAE. Explicit per-protocol training-history setting, no unknown-gap filling, rejects unconfirmed/stockout-censored history. Never enables the app or generates an order.
- `scripts/analyse_pilot.py`: strict private observation/permission schemas, deduplication/conflicting replay rejection, permission-window validation, withdrawal/expiry exclusion, correction-adjusted completed-task time, correction rates, negative outcomes and follow-up-qualified repeat use. No contacts/free text/provider calls. No data yields null/unavailable metrics, not manufactured zero outcomes. Exclusive private report output; safe validation errors.
- `docs/EVALUATION-AND-PILOT.md`: data/AI annotation and holdout protocol, metric sheet, pilot design, consent/retention and go/no-go gates. Existing invoice scorer/corpus retained; real scorecard remains unmeasured.
- `backend/tests/test_intelligence.py`, `tests/e2e/extension.spec.js`, `scripts/serve_e2e.py`: synthetic readiness/analysis and connected phone export/offline failure tests, isolated test account. CI lints new analysis tools.
- Shared UI correction: correct private download URL, retry after accepted export, breadcrumb label. Original browser assertions retained.

No new dependencies, migrations, models, background jobs, telemetry collection,
real provider access, forecasting activation, cross-merchant aggregation or pilot
recruitment. Existing PostgreSQL/offline/recovery behaviour remains intact.

## Acceptance checklist

| Plan gate                                                    | Status / evidence                                                                                |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Enable forecasts only for ready SKUs                         | PASS safety boundary; all disabled. Actual eligible forecasting DATA NOT READY                   |
| Beat/justify explicit time-held-out baseline                 | PASS offline comparison algorithm/regressions; real model evidence DATA NOT READY                |
| No result from incompatible/insufficient data                | PASS; gap, stockout, coverage, cold-start tests; UI suppresses all forecasts                     |
| Privacy-reviewed benchmark releases                          | BLOCKED — LEGAL/CONSENT; no releases/analytical pipeline; all cohorts suppressed                 |
| Representative real/human-reviewed held-out AI set           | BLOCKED — LEGAL/CONSENT and ACCESS; existing 12 synthetic cases are not representative real data |
| OCR/voice correction time, failure/abandonment               | Tool/protocol implemented; actual OCR/voice merchant measurements NOT MEASURED                   |
| Grounded-answer/citation/abstention/unsafe-action evaluation | Existing synthetic safety tests PASS; representative human quality score NOT MEASURED            |
| Pilot baseline/comparison and evidence-matched claims        | PILOT NOT RUN; protocol/tool exists, no impact claim emitted                                     |
| Repeat use/support/alert burden with positive metrics        | PASS analysis formulas/tests; real results PILOT NOT RUN                                         |
| Failed gates disabled/restricted                             | PASS; no forecast/peer release/provider submission enabled                                       |

## Validation

Focused intelligence tests: **13 passed**, 0 skipped. Full PostgreSQL suite:
**245 passed**, 0 skipped, PostgreSQL **17.11 Homebrew**. Node offline/money tests:
**17 passed**, 0 skipped. Complete browser results, APK and command matrix are
recorded in `docs/POST-PLAYBOOK-STATUS.md` after final verification.

No official provider API version changed; no external provider contract was
verified. No schema change: Alembic head remains `c6ec82a178d3`; `alembic check`
reports no new operations. Rollback code without deleting existing preparation
actions/audit snapshots. Keep the new action handler or expire proposals if older
code is deployed. No data import/reset/migration was performed.

Smallest next step: accountable data/pilot lead, real consent and privacy handling,
permissioned representative corpus and independent reviewers, then declared
coverage/baseline and held-out measurements. Do not recruit, upload merchant
documents, collect analytics or turn on predictions solely because tooling exists.
