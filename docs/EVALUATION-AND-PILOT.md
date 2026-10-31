# Evaluation and pilot protocol v1

30 October 2026. **Draft protocol, not approved research or measured outcomes.**
No real merchant pilot, privacy review, fluent-language review, lender/CA review or
representative real-world provider comparison has occurred. The owner confirmed
these prerequisites are unavailable. Synthetic regression tests are not merchant
impact evidence. Keep all real observations under ignored `evaluation/private/`
with restricted access; never commit documents, contacts, consent forms or reports.

## Data readiness and forecasting

`GET /api/intelligence/readiness` reports only the authenticated store's accepted
inventory-event counts, SKU unit, stock version, observed sale dates and merchant
threshold. Distinct observed sale days are **not** complete history. Missing
intervals and stockout periods remain unknown; receiving and purchase quantities
never become inferred sales. Results are capped at 100 SKUs with explicit truncation.
No cross-store query, raw peer record or analytical cohort is exposed.

Before forecasting, a reviewer must approve per-SKU category/unit, observation
calendar and completeness, corrections/reversals/stock counts, stockout censorship,
returns/wastage handling, source confidence, lead time and variability, horizon,
minimum training/test history and loss metric. These are evaluation-plan settings,
not a universal “30 days means ready” rule. No such plan is configured in the app;
all forecasts remain suppressed. Existing merchant reorder thresholds remain rules.

`scripts/evaluate_forecast.py` is a separate offline research tool. It requires
one compatible unit, ordered contiguous daily periods, explicit coverage, a
protocol ID, configured minimum training length and an untouched future holdout.
Unknown gaps are never zero-filled; stockout-censored series are rejected. It
compares a frozen last-observed baseline with the training-period mean using
exact-decimal MAE. Holdout values cannot change predictions. Ties retain the naïve
baseline. A single split does not promote a model, calibrate uncertainty or produce
an order. Repeat rolling-origin splits and reviewer approval are still required.

```sh
.venv/bin/python scripts/evaluate_forecast.py --input evaluation/private/series.json --output evaluation/private/holdout-report.json
```

Use the `Series` Pydantic model as the versioned input schema. Outputs are created
exclusively (no overwrite), chmod 0600, and always `production_enabled: false`.
Structural checks do not prove source quality, legal consent or real data.

## AI protocol and scorecard

Retain the existing 12-case synthetic corpus, calibration/held-out split, generated
image variants, ground truth and adversarial cases in `evaluation/corpus/`.
Do not relabel it real, independently annotated or statistically representative.
The existing `scripts/evaluate_ai.py` scorer remains the shared field-comparison baseline;
see `docs/AI-EVALUATION.md` and `AI-DATA-HANDLING.md`. Provider comparison is blocked
until permissioned data, provider access, handling review and independent reviewers
exist. No new cloud call or price/model quality claim is made by this extension.

| Job                     | Required measurement                                                                                                                                               | Current evidence / launch decision                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Invoice extraction      | Field precision/recall/exact match; critical supplier/ref/date/quantity/unit/money/tax adjudication; confidence calibration; corrections and end-to-end completion | Synthetic schema/fallback/injection regressions only; real score NOT MEASURED; merchant review always mandatory |
| Speech                  | WER/CER by language/accent/noise/device/network; corrections, task completion, abandonment, latency and fallback-to-touch                                          | Permission-denial/browser tests; real language/noise/timing matrix NOT MEASURED; preview remains disabled       |
| Translation             | Fluent double-review of meaning, amounts/names/references/tone, correction burden and source/draft comparison                                                      | Numeric mismatch/manual review tests; real fluency NOT MEASURED; no automatic sharing                           |
| Intent and action draft | Correct allowlisted intent/source IDs, tenant permissions, invalid/malicious requests and unsafe execution attempts                                                | Existing grounded-help/approval tests; representative human-labelled precision NOT MEASURED                     |
| Grounded help           | Supported/unsupported/contradictory questions, citation coverage and correctness, abstention, unsupported assertions and prompt injection                          | Existing deterministic curated-help safety tests; real answer-quality score NOT MEASURED                        |
| Summary                 | Fact-by-fact source agreement, omission, money/source ID preservation, stale/missing-data abstention and correction effort                                         | No evaluated generative summary; deterministic brief remains authoritative                                      |

Before unlocking a job, freeze model/provider/version, prompt/hash, dataset/version,
supported language/layout/device strata, held-out allocation, reviewer identities
and annotation guide. Double-review critical fields; adjudicate disagreements
without tuning on holdout. Define sample sizes and numeric quality thresholds
with the accountable reviewers **before** scoring. Critical financial/consent
violations are stop conditions regardless of average accuracy. Absent approved
thresholds or adequate sample coverage, keep manual/disabled behaviour. Never
substitute confidence returned by a provider for calibrated accuracy.

Report numerator/denominator per stratum; missing runs stay unmeasured, not passing.
Compare cost per _merchant-accepted_ invoice including failed calls/corrections,
P50/P95 latency including network/provider boundaries, and correction-adjusted time.
Do not infer human time, billed cost, acceptance or abandonment from model output.
Retain versioned regression results; a safety failure or increased correction burden
pauses the relevant model/prompt version. No automatic model routing promotion.

## Pilot consent and data minimisation

An accountable pilot lead and data reviewer must approve the protocol, participant
notice, retention/deletion process, support channel and go/no-go criteria before
recruitment. Document any real provider processing separately; this protocol does
not authorise sharing with AI providers, lenders, Meta or tax authorities.

Collect only random `pilot_` + 12-hex participant IDs; keep identity mapping and
signed permission evidence separately with restricted access. No names, phones,
document contents, customer/staff identities or raw transcripts in observations.
The private consent record has purpose `pilot-v1`, attributable human evidence,
timestamp, expiry within 30 days and withdrawal. The analysis schema is not a
consent-verification service. A lead must verify actual permission evidence.

Local observation files are not device-encrypted by this tool. Use OS encryption,
restricted access and approved backups; do not claim anonymous/encrypted storage.
Stop collection on withdrawal; exclude all withdrawn/expired participants from
subsequent reports. Delete their observation and identity-mapping files through
the approved process, including retained copies/backups as permitted; keep only
the legally required minimal consent/deletion evidence. The tool does not pretend
to delete partner-held data. No server-side pilot registry/retention job exists.

## Pilot design and metrics

Recruit consented kirana stores across relevant size bands, languages, devices and
network conditions only after review. Capture baseline workflows before enabling
assistance; use paired tasks or a phased comparison where practical. Predeclare
comparison groups and account for learning, seasonality, invoice complexity and
missing observations. No causal claim from an uncontrolled before/after demo.

`scripts/analyse_pilot.py` validates private versioned observations, exact operation
IDs and permission windows, rejects conflicting replays, ignores exact duplicates
and excludes expired/revoked participants. It emits no participant-level report,
provider call, database mutation or inferred money recovery. Do not publish its
small-cohort descriptive output as anonymised peer benchmarking.

```sh
.venv/bin/python scripts/analyse_pilot.py --input evaluation/private/pilot.json --output evaluation/private/pilot-report.json
```

The `Dataset` model is the input contract. Empty participants/observations produce
`NOT YET AVAILABLE`, empty metrics and null repeat-use rate. Inputs need schema
version 1, mode `demo` or `pilot`, protocol `pilot-v1` and explicit `observed_until`.
No defaults create fictitious observations. Output creation refuses overwrite and
sets mode 0600. Validation failures print no private input values.

| Metric                                  | Definition / evidence requirement                                                                                                                                                                    |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Correction-adjusted task time           | Completed task active milliseconds **excluding** corrections + separately observed correction milliseconds; grouped by task and method; compare manual baseline rather than assuming voice is faster |
| Field correction rate                   | Corrected reviewed fields / reviewed fields; unknown denominator remains null                                                                                                                        |
| Completion/abandonment                  | Observed complete and abandoned counts over task starts, mutually exclusive; never count app opens as completed work                                                                                 |
| Negative outcomes                       | False alerts, sync conflict, data loss, wrong extraction, support-needed counts, plus incident review; no causal accuracy claim from these labels                                                    |
| Repeat use                              | Among participants with 14 elapsed days and a completed task in consent-relative days 0–6, fraction completing a task in days 7–13; incomplete follow-up is excluded, not counted as churn           |
| Verified supplier recovery              | Existing confirmed proof-backed financial events, separately reviewed against baseline/period; task timing file cannot establish money recovered; promise/draft never counts                         |
| Physical stock accuracy                 | Independently sampled physical counts versus accepted stock ledger at the same time/unit; not measured by number of receipts                                                                         |
| Settlement resolution / false alerts    | Authorised source-linked exceptions, resolution evidence/timestamps and human labels; DEMO fixtures excluded                                                                                         |
| Forecast stockout/excess/expiry effects | Eligible, evaluated SKU histories, known coverage and comparator; currently unavailable                                                                                                              |
| Useful recommendations                  | Source-linked completed action and explicit merchant correctness judgement; no ratio inferred from page views                                                                                        |

No pilot has run. All real outcome rates, confidence intervals, savings, provider
costs and adoption estimates remain unavailable. Interview/feedback collection is
manual, optional and minimised; no intrusive survey, covert analytics or raw free
text logging was added. The lead records what required correction, ignored alerts,
increased workload and support needs. Prioritise the backlog from this evidence.

Pause on any financial truth error, material privacy/consent breach, repeated false
alerts, data loss or correction burden worse than manual. An accountable review
must recommend expand/iterate/stop with cohort size, coverage, comparison method,
uncertainty, confounders, negative outcomes and unresolved issues. No automated
go-live decision or fabricated result is produced.

## Benchmark boundary

Peer comparison remains suppressed. No pipeline reads across merchant stores.
Before a separate analytical path is built, approve lawful purpose/participation,
data-controller responsibilities, metric comparability, minimum cohort size,
outlier/small-cell suppression, repeated-query/differencing controls and attack
tests, retention and withdrawal. Removing names alone is not anonymisation.
There is no configured safe cohort threshold or privacy review, so every cohort
is suppressed regardless of a client-supplied size. No raw peer data reaches an LLM.

31 October supplement: [five-improvement validation](FIVE-IMPROVEMENTS-VALIDATION.md) records the bounded synthetic image runner and available browser/APK evidence. It does not establish a real-invoice or merchant pilot result. No pilot participant was recruited.
