# Archived owner-supplied extension requirements

Saved for cross-system continuity. This is a requirements document, **not evidence of completion**. The owner subsequently authorised all three batches sequentially in one request, overriding its per-batch pause instructions. Current implementation evidence and discrepancies are in POST-PLAYBOOK-STATUS.md.

title: Paytm Business Partner
subtitle: Post-Playbook Integration & Validation Plan
version: 1.0
date: 30 October 2026

---

# Paytm Business Partner

## Post-Playbook Integration & Validation Plan

**Three focused Codex batches | Kirana-first | Mobile PWA + Android APK | PostgreSQL-only | Existing master playbook assumed complete**

**Purpose:** Extend the completed 10-batch Paytm Business Partner implementation with the remaining real-world integrations, regulated workflows, data-dependent intelligence and merchant validation. This document is an extension to the master playbook, not a replacement for it.

---

# 1. Starting point and scope

## 1.1 Assumed completed foundation

For this extension, assume that all ten batches in **Paytm Business Partner — Master Implementation Playbook** have been implemented and accepted. The product already has:

- The evolved Munafa / Paytm Business Partner application and preserved supplier recovery workflow.
- PostgreSQL as the only server-side application database, with migrations and tests.
- Authentication, merchant/store scoping, permissions and audit controls.
- The mobile-first installable PWA and shared React application packaged for Android through Capacitor.
- IndexedDB-based offline drafts/queue and synchronisation behaviour, with visible pending/conflict states.
- The kirana purchase, physical receiving and inventory foundation.
- The Paytm adapter boundary, demo/live separation and the settlement/daily-brief foundation to the extent supported by available data.
- AI/OCR/voice/help foundations and the P1/P2 modules described in the master playbook, subject to their existing readiness gates.
- Integration, security and release tests from the master playbook.

**Do not rebuild these capabilities.** Begin each batch by inspecting the current branch and verifying the relevant implementation. Extend existing services, models, screens, tests and adapters. If an item is missing or materially incomplete, report the discrepancy and propose the smallest repair before proceeding. Do not silently recreate an existing module.

## 1.2 What this extension addresses

| Batch | Focus                                         | Remaining capabilities                                                                                                                        |
| ----- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | Real commerce and communications integrations | Authorised Paytm production APIs, transaction feeds, settlement webhooks, Soundbox/POS telemetry, WhatsApp Business API and delivery receipts |
| **2** | Regulated and partner workflows               | Lender integrations and authorised application workflows; GST/CA validation and authorised filing integration                                 |
| **3** | Evidence, intelligence and market validation  | Data-ready forecasting, privacy-safe benchmarking, real-world AI evaluation, kirana pilot and repeat-use validation                           |

## 1.3 Global product rules

1. **No fabricated integration.** A mock, fixture, demo adapter, public documentation page or manually uploaded CSV is not a live Paytm/lender/GST/WABA integration.
2. **Verify official documentation at implementation time.** API versions, endpoints, credentials, webhook formats, sandbox access, commercial terms and permissions may change. Use official provider documentation and the actual authorised integration pack supplied by the user/partner. Never infer endpoints or payload fields.
3. **Live access is a prerequisite, not something Codex can invent.** When credentials, partner approval, merchant IDs, sandbox access or legal permissions are missing, implement/test the adapter contract and demo path, record the live path as BLOCKED, and request only the specific missing input. Do not call the batch complete for live integration.
4. **Preserve PostgreSQL-only.** PostgreSQL remains the only server-side application database in development, CI, tests and deployment. Do not introduce SQLite or a SQLite fallback. IndexedDB may remain the browser's offline store.
5. **Keep the same product.** Extend the existing React PWA/Capacitor application and FastAPI backend. Do not create a second app or a collection of disconnected integration dashboards.
6. **Merchant consent and approval remain explicit.** No autonomous payment, refund, customer/supplier message, loan submission, tax filing, purchase order or binding negotiation.
7. **AI never becomes financial/legal truth.** AI can extract, explain, classify, summarise and draft. Deterministic services and authorised partner systems validate facts and execute permitted operations.
8. **Separate demo from live data.** Never merge synthetic/demo and live data into an unlabelled metric, report, export, alert or model-training dataset.
9. **Measure actual merchant outcomes.** Do not treat API calls, records ingested, model responses or screens shipped as product success.
10. **Phone-first remains mandatory.** All new user journeys must work on common Android phone widths, respect touch interactions and expose clear online/offline/pending/sync status. Desktop can remain a useful secondary layout.

---

# 2. How to use this extension

1. Open the repository at its root in Codex.
2. Paste the **Global Extension Instructions** once.
3. Run Batch 1, review the implementation report and test results, then commit it.
4. Run Batch 2 only after its dependencies and permission gates are available. If a real lender/GST partner integration is unavailable, complete only the safe adapter/preparation workflow and report the live connector as blocked.
5. Run Batch 3 after the data and integration events required for evaluation are available. Do not enable forecasts or peer benchmarks merely because a UI can be built.
6. Use a separate Git branch or commit checkpoint for each batch. Never paste all three batches at once.

## Standard completion report required after every batch

Codex must report:

- Files created/changed and why.
- Existing feature behaviour preserved.
- Which providers/environments were actually connected: live, sandbox, fixture/demo, manual or blocked.
- Official docs and API versions used, with links and the date checked.
- Migrations/schema changes and rollback steps, if any.
- Commands executed and exact test results.
- Security, privacy, consent and approval checks performed.
- Mobile/PWA/Android and offline behaviour verified.
- Acceptance criteria marked **PASS / FAIL / BLOCKED / NOT APPLICABLE**, with evidence.
- Remaining credentials, partner approvals, legal reviews or merchant access required.
- Known limitations and the smallest next step.

Do not claim success for a live integration based solely on mocked tests or a successful local build.

---

# 3. GLOBAL EXTENSION INSTRUCTIONS — PASTE ONCE INTO CODEX

```text
You are the senior engineer extending an EXISTING, completed Paytm Business Partner / Munafa application. This repository has already completed the ten-batch Master Implementation Playbook. Your task is to implement only the post-playbook work described in the selected batch.

FIRST: inspect the current repository, docs, migrations, tests and integrations relevant to the selected batch. Treat the current code as the source of truth. Do not assume this document's description is perfectly reflected in the branch. Do not rebuild features that already work. If the repository differs, report the difference and propose the smallest safe change.

PROJECT CONSTRAINTS
- Keep the existing React PWA and Capacitor Android application as one shared product.
- Keep FastAPI and the established backend/domain architecture unless a concrete technical reason requires a scoped refactor.
- PostgreSQL is the ONLY server-side application database in development, CI, tests and production. Never introduce SQLite, an embedded server database, or a silent database fallback. Browser IndexedDB is permitted for offline client storage.
- Preserve merchant/store isolation, role permissions, audit events, idempotency, optimistic concurrency, integer-paise money, decimal quantity handling, approval workflows and offline sync semantics already implemented.
- Preserve the Munafa supplier recovery lifecycle and all accepted financial invariants.
- Do not log API keys, access tokens, raw payment credentials, full personal data or sensitive webhook payloads.
- Do not mix demo/synthetic records with live records without explicit source labels and filters.

INTEGRATION RULES
- Use official, current provider documentation and authorised partner-provided integration specifications. Verify the API version, base URL, authentication, scopes, required headers, webhook signature algorithm, idempotency support, rate limits, retry rules and environment limitations before coding.
- Never guess endpoint paths, request/response shapes, signature rules, account identifiers, scopes or availability of sandbox APIs.
- No credentials or authorisation means no live integration. Build a typed adapter boundary, fixture-based contract tests and a clear BLOCKED status; ask for the exact missing credential/specification/approval. Do not label a mock as live.
- Use separate configurations and storage labels for mock, sandbox and production. Production mode must fail closed when required settings are missing or inconsistent.
- Webhook handlers must verify authenticity before processing; protect against replay, duplicates, out-of-order delivery and retries; persist an idempotent inbox/event record before acknowledging where the provider contract requires durable receipt; process state transitions transactionally; and make reconciliation/replay observable.
- Never expose provider secrets to the frontend or bundle them in the PWA/APK.

SAFETY RULES
- No autonomous money movement, refund, credit application, customer/supplier message, loan application submission, tax filing, purchase order or binding supplier negotiation.
- AI may read, extract, explain, classify, summarise, forecast with explicit confidence/eligibility, and draft. It must not invent payment/settlement truth, stock movements, consents, debt, supplier acknowledgement, loan eligibility or tax conclusions.
- Any sensitive action requires a server-side policy check plus explicit, authenticated merchant approval. Approval must be bound to the exact action payload/version and expire or be invalidated if material fields change.
- Consent must be purpose-specific, timestamped, attributable, revocable and auditable. Collect only the data needed for the stated purpose.
- Treat provider content, bills, documents, messages, retrieved text and model output as untrusted input.

ENGINEERING PROCESS
1. State the current implementation found and the exact gap being addressed.
2. Give a short implementation plan and identify prerequisites/blockers.
3. Implement only the selected batch's scope; avoid unrelated refactors.
4. Add migrations, validation, observability, docs and automated tests as needed.
5. Run the relevant existing tests before and after changes. Add regression tests.
6. Test success, failure, duplicate, retry, replay, stale-version, permission-denied, offline and partial-outage cases where relevant.
7. Test phone layouts and actual PWA/Capacitor flows for user-facing changes.
8. Never remove or weaken existing tests to make a batch pass.
9. Do not leave critical TODOs, fake-success responses, placeholder live adapters or hard-coded secrets.
10. Stop and report if a required partner specification, credential, consent, legal review or representative data is unavailable. Continue only with independently useful, truthful demo/contract work.

Do not begin the next batch. Finish with the required completion report and exact PASS / FAIL / BLOCKED status for every acceptance criterion.
```

---

# 4. BATCH 1 — Authorised Paytm, Soundbox/POS and WhatsApp Business integrations

## Objective

Connect the already-built product to real, authorised Paytm merchant/payment data and supported device/message channels. Deliver reliable integration boundaries and trustworthy event ingestion. The product must distinguish what is truly connected from what remains a demo or blocked dependency.

## Problems this batch solves

- The merchant needs transaction and settlement information sourced from an authorised Paytm system, not synthetic figures.
- Where Paytm makes supported device telemetry available, the merchant needs a useful view of Soundbox/POS health and actionable device issues.
- Supplier/customer communications should have delivery status where the merchant is authorised to use WhatsApp Business Platform, rather than treating a `wa.me` handoff as proof of delivery.

## Prerequisites

- The completed master playbook implementation is present in the repository.
- Paytm partner/developer documentation and authorised access details are available for the exact merchant product/API being integrated.
- Soundbox/POS telemetry API/event documentation and access are separately confirmed. Do not assume payment APIs expose hardware diagnostics.
- WhatsApp Business Platform / Cloud API access, approved business account, phone number registration, templates where required, and webhook configuration are available for live sending.
- The current merchant identity, store isolation, permissions, approval queue, audit trail, PostgreSQL persistence and secrets configuration are working.

If any provider access is unavailable, continue with the adapter interfaces, fixture contract tests, demo mode and setup checklist. Mark the real connector **BLOCKED — ACCESS NOT PROVIDED**. Do not simulate success in production mode.

## Scope A — Paytm transaction and settlement integration

1. Inspect the current Paytm adapter, reconciliation domain model, daily brief and existing source labels. Extend them rather than creating a competing integration path.
2. Read the latest official Paytm documentation supplied/authorised for this integration. Confirm the exact APIs and event products available to this merchant account and environment. The original research notes a settlement-order-detail API with settlement amount, commission, GST and payout/settlement dates, but its staging availability was limited at the time of research; re-check current status rather than assuming it is now available.
3. Create/extend a typed provider adapter with explicit operations for only documented capabilities, such as transaction retrieval, settlement details, supported refunds/disputes and webhook subscription/verification where actually offered.
4. Define normalised internal event contracts while preserving provider event IDs, original status, event time, ingestion time, currency, amount, fees/taxes where supplied, source reference and raw-payload hash. Store only the minimum raw payload required for audit/debugging under retention controls.
5. Convert rupee amounts to integer paise at a validated boundary. Reject malformed, ambiguous or unsupported amounts; never use binary float for money.
6. Implement cursor/time-window sync with overlapping windows and deduplication. Handle missing pages, rate limits, timeouts, expired credentials, provider downtime and delayed events.
7. Implement webhook receipt only according to documented Paytm signature/authentication rules. Verify signatures, timestamp tolerance and event identity before accepting. Persist an idempotent inbox event, return the provider-required acknowledgement, and process asynchronously/transactionally where suitable.
8. Handle duplicate, out-of-order, delayed, reversed, pending and corrected events. Never overwrite a confirmed event silently; append corrections/reversals and preserve source history.
9. Keep deterministic reconciliation responsible for arithmetic and matching. Explain differences using only available facts such as settlement timing, fees, GST, refunds, reversals and payout cutoffs. Never label an unexplained delta as fraud or missing money.
10. Clearly mark last successful sync time, source, coverage window, connection health and stale state. Do not display cached information as real-time.

## Scope B — Soundbox/POS device telemetry

1. Verify whether the authorised Paytm integration provides device inventory, assignment, status, last-seen time, battery/network/health signals, POS state or diagnostic events. Do not infer device health from transaction activity alone.
2. Implement only fields/events documented and authorised. Map each device to a merchant/store only through a trusted provider identity mapping; never rely on user-submitted device IDs as proof of ownership.
3. Provide device status cards and a device-detail timeline that distinguish provider-reported status, last reported time and inferred advisory state.
4. Alert only on explicit supported conditions with sensible deduplication and cooldowns. Missing telemetry means “status unavailable”, not “device offline”.
5. Provide a support/escalation action with captured device reference and observed evidence; do not remotely reconfigure, deactivate or alter a device unless an authorised API and a separate approved workflow explicitly support it.

## Scope C — WhatsApp Business Platform and delivery receipts

1. Preserve the current WhatsApp deep-link path as a manual handoff fallback. Do not mislabel it as an API-sent message.
2. Build a provider adapter for the authorised WhatsApp Business Platform API, based on current official docs. Confirm message types, templates, opt-in requirements, country/recipient rules, rate limits, message windows, pricing and supported statuses.
3. Store purpose-specific contact permission/consent evidence, consent timestamp/source, current opt-in state and withdrawal. Check consent and channel policy at send time, not only when a draft is created.
4. Keep draft creation separate from sending. A merchant must preview the exact recipient, channel, language and rendered message, then explicitly approve sending. Bind approval to the exact content and recipient.
5. Process delivery/read/failure/inbound status webhooks only after authenticating them using the documented verification method. Deduplicate statuses, tolerate out-of-order events and preserve message state history.
6. Show statuses accurately: draft, awaiting approval, queued, accepted by provider, sent, delivered, read (only if provider reports it), failed, or unknown. “Accepted by provider” is not “delivered”.
7. Implement retries only for provider-documented retryable failures, with idempotency and no accidental duplicate messages. Never retry an ambiguous send outcome blindly.
8. Minimise phone number exposure in logs and UI; apply retention and deletion policies.

## Shared UX requirements

- Phone-first integration status and detail screens consistent with the existing design system.
- Clear “Live”, “Sandbox”, “Demo data” or “Not connected” labels.
- Last-sync/last-event time and stale-data state.
- Human-readable failure messages with a safe retry path.
- No provider credentials or raw webhook JSON exposed to a merchant.
- Offline mode can show last-synced cached records and queued drafts, but must not imply a live provider action occurred.

## Out of scope

- Guessing or reverse engineering private Paytm endpoints.
- Treating public docs as proof of access.
- Soundbox/POS remote control or configuration unless separately authorised and explicitly designed.
- Autonomous messaging or automatic customer targeting.
- Any payment/refund initiation unless a separate authorised, approved product flow already exists and is explicitly included by the user.
- Rebuilding the existing reconciliation or daily brief from scratch.

## Required tests

- Provider adapter schema/contract tests from official examples or authorised fixtures.
- Invalid credentials, expired token, permission/scope failure, rate limit, timeout and provider outage.
- Valid/invalid webhook signature; stale timestamp; replay; duplicate event; out-of-order event; unknown event type; malformed payload.
- Same event imported by polling and webhook only once.
- Partial pagination, overlapping sync windows, late event and reversal/correction.
- Settlement values with fees/tax/refunds and deterministic reconciliation outputs.
- Cross-merchant/store access denied for every transaction, settlement and device lookup.
- Soundbox status unavailable vs explicitly offline; stale telemetry; duplicate alerts.
- WhatsApp missing consent, revoked consent, invalid recipient, template rejection, provider acceptance, delivered/read/failure statuses, duplicate/out-of-order status webhook and ambiguous send timeout.
- Approval invalidated if recipient or message text changes after review.
- PWA/Android mobile screens, offline cached state and reconnect behaviour.

## Acceptance gates

- [ ] Each live Paytm capability is backed by official documentation, authorised credentials and a successful real sandbox/production contract test. Otherwise it is explicitly BLOCKED, not marked implemented.
- [ ] No duplicate financial event is created through retries, polling/webhook overlap or replay.
- [ ] Settlement explanations account only for fields and events actually available; unexplained differences remain “needs review”.
- [ ] Device health is sourced from documented telemetry; missing information is never converted into an offline/fault alert.
- [ ] WhatsApp API sends require current consent and explicit approval; statuses reflect provider receipts exactly.
- [ ] Demo, sandbox and live data are visibly separated in the UI, APIs, logs and exports.
- [ ] Cross-tenant tests pass and secrets/PII are not leaked.
- [ ] Existing Munafa workflow and master-playbook regression tests pass.

## Codex execution prompt

```text
Execute BATCH 1 — Authorised Paytm, Soundbox/POS and WhatsApp Business integrations — from the Post-Playbook Implementation Plan.

Start by auditing the existing adapters and completed playbook implementation. Do not rebuild existing modules. Verify current official documentation and the exact provider access/configuration available in this repository. Before implementing any live API, list the exact documented endpoints/events, authentication/scopes, signature rules, environment and missing prerequisites.

Implement only documented and authorised capabilities. If credentials, access or a partner spec are absent, implement the typed adapter contract, fixture-backed tests, demo/live separation and setup checklist, then mark the live connector BLOCKED. Never invent endpoints, payload fields, signatures or successful live events.

Implement transaction/settlement ingestion, webhook durability/idempotency, Soundbox/POS telemetry only where authorised, and WhatsApp Business sending/status receipts with consent and exact-content merchant approval. Preserve all financial invariants, tenant isolation, PostgreSQL-only persistence and offline truthfulness.

Run all relevant regression and new tests. Finish with the standard completion report and a capability-by-capability table: LIVE VERIFIED / SANDBOX VERIFIED / DEMO ONLY / BLOCKED.
```

---

# 5. BATCH 2 — Lending partner workflows and GST/CA-reviewed compliance

## Objective

Add secure, consent-based workflows for authorised lending partners and GST/compliance preparation. The application may help a merchant understand document readiness, prepare information and hand off to a regulated provider or qualified tax professional. It must not become a lender, underwriter or tax authority.

## Prerequisites

- Batch 1's identity, merchant/store mapping, audit and integration-secret patterns are stable.
- Existing PostgreSQL tenancy, roles, explicit approval and consent records work.
- An authorised lending partner's API/onboarding specification and access are available for live integration.
- A qualified CA/tax reviewer is available to validate the GST preparation workflow and sample outputs.
- Current official GSTN/IRP/API documentation, authorised access and required GST practitioner/CA processes are available before any filing integration is attempted.

Without these prerequisites, implement only a safe document-readiness and CA-review workflow with clearly marked demo data. Do not submit a real loan application or tax filing.

## Scope A — Lending readiness and partner integration

1. Define the assistant's role as **document readiness and partner navigation**, not credit approval, loan advice or underwriting.
2. Identify which lending partner and product are authorised for the hackathon/merchant cohort. Read its current official API and consent requirements. Do not scrape or reverse engineer private systems.
3. Build a typed lender adapter for documented functions only, potentially including product/offer display, eligibility pre-check response, document checklist, application handoff/status retrieval and partner callback/webhook. Implement only capabilities actually offered.
4. Display partner identity, regulated role, product terms, fees/rates/tenure where returned by the partner, data shared, consent purpose and link to official disclosures. Do not invent an offer or calculate an approval probability.
5. Allow the merchant to review the exact data/document package and purposes before sharing. Capture explicit, revocable, purpose-specific consent with timestamp, actor, partner, scope and version of disclosure.
6. Minimise data. Share only partner-required fields. Never repurpose transaction, customer, staff, voice or inventory data beyond the stated purpose/consent and applicable partner/legal requirements.
7. Keep lender decisions and eligibility outputs as partner-sourced values with source/time/status. AI may explain plain-language terms but must not change partner terms or declare approval.
8. The final application submission must require an explicit merchant action on a clearly identified partner page/API flow. A draft or eligibility check is not a submitted application.
9. Process partner status callbacks idempotently and show pending, submitted, additional information required, rejected, approved or disbursed only when the partner reports that exact state.
10. Provide consent withdrawal and data deletion/restriction handling as permitted by legal and partner retention obligations; explain when a partner must retain submitted records.

## Scope B — GST preparation, CA validation and authorised filing boundary

1. Separate **bookkeeping preparation**, **GST document checks**, **CA-reviewed output**, and **actual statutory filing** into distinct states.
2. Build a GST-ready record pack from source invoices and accepted transactions already in the product. Preserve original documents and provenance. Every extracted field must point to its source record/document and carry review status.
3. Validate required fields, format consistency, arithmetic consistency and applicable schema rules using current official documentation. Do not let an LLM decide tax applicability, classification, exemptions, HSN treatment, filing eligibility or legal deadlines.
4. Implement an exception list explaining missing/invalid fields and offering a correction workflow. Treat suggested classification/HSN/tax fields as proposals for CA review, never authoritative tax advice.
5. Generate a structured CA export and human-readable review summary with source references, totals, unresolved exceptions and period coverage. Reconcile totals deterministically using accepted source events.
6. Add CA/reviewer role and approval workflow if supported by the existing permissions design. A review approval must bind to a versioned snapshot; later material changes invalidate it.
7. Only implement a direct GSTN/IRP filing connector if the project has the required authorised access, current official API specification, correct taxpayer/authorised-user permissions, tested sandbox and explicit user authorisation. Otherwise provide a CA-reviewed export/handoff and mark direct filing BLOCKED.
8. Before any real submission, render the exact return/filing payload and values for merchant/authorised reviewer approval. The app must not auto-submit based on an AI recommendation.
9. Capture acknowledgement/reference only from the official filing system/provider response. Never show “filed” or “accepted” based on a local button click.
10. Keep versioned source data, reviewer identity, approval timestamp, submission attempt and official acknowledgement/audit history.

## Shared UX requirements

- Separate “Prepare documents”, “Needs CA review”, “Approved for handoff”, “Submitted to partner” and “Officially acknowledged” states.
- Show the lender/CA/provider identity and exactly what data is being shared.
- Provide a plain-language explanation while preserving original official terms and documents.
- Require re-consent if the purpose, recipient or data scope materially changes.
- Work offline for locally saved preparation drafts where safe; online partner checks/submissions must clearly require connectivity.

## Out of scope

- Autonomous underwriting, loan approval, rejection or ranking of merchants for credit.
- Guaranteeing loan eligibility, interest rate or disbursement.
- Invented lender offers, fabricated status updates or fake application IDs.
- Acting as a CA/tax professional or making binding legal/tax determinations.
- Automated GST filing without authorised access, required review and explicit approval.
- Storing additional personal/financial data merely because a partner API accepts it.

## Required tests

- Partner adapter contract and version tests using authorised fixtures.
- Missing consent, expired/revoked consent, changed data purpose, changed recipient and overbroad data-sharing attempts.
- Cross-tenant lending/document access denial.
- Partner errors, timeouts, retries, duplicate callbacks, out-of-order statuses and ambiguous submission outcomes.
- Ensure a draft/eligibility response never becomes a submitted application without explicit merchant approval.
- Verify partner-sourced terms/status are not altered by AI text generation.
- GST source provenance, missing fields, malformed GSTIN/reference, arithmetic mismatch, schema-version mismatch and unsupported tax classification.
- CA review required; edited-after-review snapshot invalidates approval.
- Filing is blocked when credentials/permissions are missing; official acknowledgement required to show submitted/accepted.
- Data export, retention, consent withdrawal and deletion flows, subject to lawful retention constraints.
- Phone/PWA/Android usability, offline draft behaviour and online-only submission states.

## Acceptance gates

- [ ] Lending integration uses an identified, authorised partner and current official contract; unsupported actions are not invented.
- [ ] No model or local rules approve credit, promise an offer or replace partner underwriting.
- [ ] Consent is specific, informed, revocable and recorded before sensitive data sharing.
- [ ] Every shared field can be traced to an approved source and stated purpose.
- [ ] GST preparation preserves source documents and deterministic totals.
- [ ] A qualified CA/reviewer validates the generated output and exception handling before it is presented as ready.
- [ ] No return is labelled filed/accepted without official provider acknowledgement.
- [ ] All real submissions require exact-payload review and explicit authorised approval.
- [ ] Existing product, PostgreSQL, tenancy, audit and offline regression tests pass.

## Codex execution prompt

```text
Execute BATCH 2 — Lending partner workflows and GST/CA-reviewed compliance — from the Post-Playbook Implementation Plan.

First audit the existing identity, permissions, consent, audit and document workflows. Do not rebuild the master-playbook foundation. Identify the authorised lending partner and GST/IRP integration documents actually present. Verify current official specifications and access before implementing a live connector.

Build lending as a consent-based document-readiness and authorised partner workflow only. Partner systems own eligibility, pricing, underwriting and application status. Build GST as source-linked bookkeeping/document preparation with deterministic validation and CA review. Direct submission is allowed only with official authorisation, tested provider contract, exact-payload approval and official acknowledgement.

Where partner access, credentials, CA review or legal authorisation is unavailable, finish the safe preparation/handoff workflow and tests, then mark the live integration BLOCKED. Never fabricate offers, tax conclusions, submission status or acknowledgements.

Preserve PostgreSQL-only persistence, tenant isolation, consent withdrawal, auditability, mobile usability and offline truthfulness. Run all regression and new tests and deliver the standard completion report.
```

---

# 6. BATCH 3 — Data-proven intelligence, AI evaluation and real kirana pilot

## Objective

Prove that the merchant assistant produces measurable value using representative real data and real kirana workflows. Activate forecasting and benchmarking only when their data prerequisites are satisfied. Evaluate AI on realistic, permissioned samples and validate whether merchants return and complete useful actions.

## Prerequisites

- The completed master-playbook data foundation and relevant Batch 1/2 connectors or permitted manual data-ingestion paths are available.
- Source records have reliable store scope, timestamps, units, provenance, sync state and live/demo labels.
- Merchants participating in the pilot have received appropriate notices and provided the required permissions/consents.
- A process exists to collect corrections, task completion times, user feedback, opt-outs and support/escalation events.
- A designated person can review evaluation datasets and pilot results; do not use uncontrolled real customer data as a benchmark corpus.

## Scope A — Forecasting eligibility and measurable reorder assistance

1. Audit SKU-level data availability by merchant/store, SKU, time period and data source. Separate accepted purchases, physical receiving, stock adjustments, sales/depletions, returns, wastage and stock counts. An invoice quantity is not proof of received stock; a payment total is not SKU-level sales.
2. Create a data-readiness report for each merchant/SKU: coverage window, number of observed periods, missing intervals, unit consistency, stockout periods, adjustment frequency and source confidence.
3. Define minimum data-quality and history requirements from an explicit evaluation plan, not an arbitrary hard-coded universal threshold. Expose thresholds/configuration and explain why a forecast is unavailable.
4. Start with transparent baseline rules (reorder point, recent average/median usage, lead-time buffer) where the required data exists. Compare candidate statistical/time-series models against simple naïve baselines using time-based holdout evaluation; prevent future-data leakage.
5. Use fractional quantity and unit conversion rules already supported by the product. Never combine incompatible units or silently infer carton/piece/kg conversion.
6. Show demand forecast, recommended reorder quantity, lead-time assumption, forecast horizon and confidence/uncertainty range. Identify missing/weak data and allow merchant override.
7. Do not issue a confident forecast for new/low-volume SKUs, sparse history, corrupted stock records or long stockout periods. Fall back to a clearly labelled rule-based suggestion or “not enough reliable history”.
8. Keep forecast output advisory. Generate a proposed purchase/reorder draft only; supplier order submission remains a separate merchant-approved workflow.
9. Track forecast error, stockout rate, excess stock, expiry/wastage, accepted/rejected suggestions and override reasons. Evaluate against the current rule-based baseline before promoting a model.

## Scope B — Privacy-safe merchant benchmarking

1. Identify the exact comparison metrics that would help a kirana merchant (for example, stock turnover bands or category-level trends). Do not benchmark sensitive individual transactions, supplier prices or customer behaviour by default.
2. Confirm lawful purpose, merchant participation/consent where needed, contractual restrictions and data-controller responsibilities before any cross-merchant processing.
3. Design an aggregation pipeline that strips direct identifiers and prevents small cohorts from revealing a merchant. Establish a minimum cohort threshold, suppression rules, outlier protection and re-identification risk review. Consider differential privacy where the release risk and implementation capability justify it; do not claim anonymisation merely because names were removed.
4. Keep benchmarking data in a separate, access-controlled analytical path. Do not expose raw cross-merchant records to the LLM or application user.
5. Publish comparisons only when the cohort is sufficiently large, comparable by merchant type/region/size/time window and meets privacy thresholds. Otherwise show “not enough comparable data”.
6. Clearly label peer metrics as aggregated estimates, include the cohort size/band and time period where safe, and explain the comparison method. Do not make claims about an individual competitor or expose merchant-level rankings.
7. Provide opt-out/withdrawal and deletion handling consistent with applicable legal and contractual obligations. Ensure withdrawals stop future aggregation and handle previously generated aggregates according to the approved retention policy.
8. Add a privacy review and re-identification attack tests before enabling the feature for a pilot.

## Scope C — Real-world AI evaluation

1. Create a documented evaluation protocol for each AI job: invoice OCR/extraction, translation, speech-to-text, intent recognition, assistant answer grounding, action drafting and summarisation.
2. Build a permissioned, representative evaluation set from realistic kirana invoices and interaction samples. Include multiple bill layouts, faded/blurred images, skew, low light, thermal print, handwriting only if in scope, mixed scripts/languages, abbreviations, quantities, GST fields and noisy speech. Do not upload sensitive merchant/customer data to providers without documented permission and data-processing review.
3. Separate training/tuning examples (if any) from a held-out test set. Version the dataset, annotation guidance, model/provider version, prompt version, language, device/capture conditions and evaluation date.
4. Have human reviewers label field-level ground truth and disagreements. Use double-review/adjudication for high-impact fields such as supplier, invoice reference, amount, item, quantity, unit, tax fields and received quantities.
5. Measure OCR field precision/recall or exact match as appropriate, confidence calibration, correction rate, percentage accepted without correction, time-to-correct, end-to-end task completion and failure/abandonment rate. Do not report only document-level “success”.
6. For voice, evaluate transcription accuracy by language/accent/noise/device, correction time, task completion, latency and fallback-to-touch rate. Compare voice-assisted and touch-first completion; do not assume voice is faster.
7. For RAG/assistant answers, measure source-grounded answer correctness, citation/source coverage, abstention when information is missing, unsupported claims, unsafe tool-call attempts and action-draft accuracy. Use adversarial prompt-injection cases embedded in bills/messages/retrieved content.
8. Evaluate translation with fluent human reviewers for meaning preservation, amounts/names/references and tone; generated text remains a draft requiring merchant preview.
9. Define launch thresholds before evaluating the holdout set. If a model fails a critical field/region, restrict supported templates/languages or fall back to manual review. Never hide low accuracy by averaging across easier cases.
10. Maintain a regression suite and monitor production correction signals with consent and minimised data. Roll back provider/model/prompt versions when quality regresses.

## Scope D — Kirana pilot, outcomes and repeat adoption

1. Design a small, consented pilot with actual kirana merchants representing the intended operating conditions. Record merchant type, store size band, device/network conditions and supported languages without collecting unnecessary identity details.
2. Establish baseline workflow measures before claiming improvements: manual invoice-entry time, receiving/reconciliation time, current stockout/expiry tracking practice, supplier-credit follow-up, and merchant-reported pain points.
3. Define product hypotheses and primary metrics before the pilot. Recommended core metrics:
   - Correction-adjusted time per completed invoice/purchase task.
   - Percentage of invoice fields accepted without correction and the time spent correcting fields.
   - Physical stock-record accuracy from sampled stock counts.
   - Documented supplier credit/refund recovered, not verbal promises or unverified claims.
   - Settlement discrepancy resolution time and false-positive rate, where live settlement data is authorised.
   - Forecast error and stockout/excess-stock change versus a baseline, only for eligible SKUs.
   - Useful actions completed per active merchant, with a measure of recommendation precision/false alerts.
   - Weekly/period repeat use, task completion, opt-out, abandonment and support burden.
4. Distinguish observed product metrics from merchant-reported estimates. Do not attribute sales or recovery changes to the app without a comparison design and enough data.
5. Use a control/comparison or phased rollout where feasible. Document confounders and limitations; do not claim causal lift from testimonials alone.
6. Capture structured feedback at task completion and short periodic interviews. Ask what was wrong, what required correction, what was ignored and whether the tool saved time after corrections.
7. Track negative outcomes too: wrong recommendations, duplicate messages, missed alerts, sync conflicts, data loss, incorrect extraction, increased workload and alert fatigue.
8. Create a prioritised iteration backlog based on observed merchant friction, not the number of AI features requested.
9. Define a go/no-go review. Pause a feature that causes financial errors, material privacy/consent failures, repeated false alerts, or greater correction burden than the manual workflow.
10. Produce a pilot results report with cohort description, method, sample/coverage limitations, metrics, confidence intervals where appropriate, qualitative findings, failures, changes made and recommendation to expand/iterate/stop.

## Shared UX requirements

- Forecast and benchmark cards must display data coverage, freshness and eligibility; show a reason when a result is unavailable.
- AI features must expose correction/edit paths and a clear manual fallback.
- Pilot feedback should be lightweight and usable on a phone, not a long survey interrupting core work.
- Provide a visible way to report an incorrect recommendation or data issue.
- Do not show a benchmark or AI confidence badge unless it is computed and calibrated from an evaluated method.

## Out of scope

- Forecasting from payment totals alone or invoice-billed quantity without physical receiving/sales/depletion data.
- Treating a forecast as a purchase order or automatically ordering stock.
- Cross-merchant raw data sharing or displaying individual competitor information.
- Training on merchant/customer documents without a valid documented purpose and permission.
- Claiming AI accuracy, time savings, recovery uplift, stockout reduction or retention without measured evidence.
- Expanding the pilot to every merchant vertical before the kirana workflow is validated.

## Required tests and evaluation artefacts

- Data-readiness checks for missing SKU sales/depletion, inconsistent units, unconfirmed receiving, stock adjustments, returns and stockout periods.
- Time-split forecast evaluation, baseline comparison, leakage tests, uncertainty and cold-start/low-data fallback.
- Benchmark cohort threshold, suppression, outlier and re-identification tests; access-control tests for analytical data.
- Versioned AI evaluation dataset, annotation guide, held-out test, field-level scorecards and reviewer adjudication.
- OCR tests across image quality and bill-layout strata; verify received quantities are never hallucinated as confirmed.
- Speech tests stratified by language/accent/noise/device with touch fallback.
- RAG citation correctness, abstention, prompt injection and unauthorised tool-call tests.
- Consent withdrawal and retention tests for pilot/evaluation data.
- Playwright mobile tests for forecast explainability, unavailable states, feedback and offline behaviour.
- Reproducible pilot analysis script/report and an auditable metric definition sheet.

## Acceptance gates

- [ ] Forecasting is enabled only for merchants/SKUs meeting documented data-readiness requirements.
- [ ] Forecasts beat or justify their use against an explicit simple baseline on a time-based holdout; otherwise the UI uses the baseline or suppresses the forecast.
- [ ] No forecast or peer benchmark is generated from insufficient/incompatible data.
- [ ] Benchmark releases pass cohort-size, suppression and privacy/re-identification review.
- [ ] AI evaluation includes representative real-world samples, human-reviewed ground truth and held-out results by meaningful strata.
- [ ] OCR and voice performance includes correction-adjusted time and failure/abandonment, not only raw model accuracy.
- [ ] RAG and assistant evaluations measure unsupported answers, citation coverage, abstention and unsafe tool calls.
- [ ] Pilot outcomes are measured against a documented baseline/comparison; claims match the evidence and limitations.
- [ ] Repeat usage and support/alert burden are reported alongside positive metrics.
- [ ] Any feature that fails safety, privacy or quality gates is disabled, restricted or rolled back rather than cosmetically marked complete.

## Codex execution prompt

```text
Execute BATCH 3 — Data-proven intelligence, AI evaluation and real kirana pilot — from the Post-Playbook Implementation Plan.

Start by auditing the real data available in PostgreSQL and the existing source/provenance/consent models. Do not assume transaction feeds equal product sales, invoice quantities equal received stock, or all SKUs have enough history. Build data readiness checks before activating forecasting or benchmarking.

For forecasting, establish a transparent baseline and time-based holdout evaluation. Suppress forecasts for insufficient/incompatible data. For benchmarking, implement a separate permissioned aggregate path with minimum cohort thresholds, suppression and re-identification review. Never expose raw merchant data across stores.

Build a versioned, permissioned AI evaluation protocol and representative kirana evaluation set. Measure field-level quality, correction-adjusted time, speech quality by language/accent/noise, RAG grounding/abstention, unsafe actions and translation review. Do not train on or send real merchant documents to an external provider without documented permission and data-processing approval.

Design and instrument a real kirana pilot with predeclared baselines, primary metrics, negative-outcome monitoring, repeat-use tracking and an honest results report. Do not invent pilot data or claim impact before it is measured. If real merchants or sufficient data are not yet available, implement the measurement infrastructure and pilot protocol, clearly marking measured outcomes as NOT YET AVAILABLE.

Preserve PostgreSQL-only persistence, mobile-first PWA/Android, merchant consent, audit trail, approval controls and existing product behaviour. Run all tests and deliver the standard completion report plus a data-readiness report, AI evaluation scorecard and pilot measurement plan/results (whichever are genuinely available).
```

---

# 7. Final post-playbook acceptance checklist

## Integrations

- [ ] Paytm production data access has been authorised and verified per capability.
- [ ] Transaction and settlement data ingestion is idempotent, traceable and freshness-labelled.
- [ ] Webhook authenticity, replay protection and event ordering are tested.
- [ ] Soundbox/POS health is based only on supported telemetry.
- [ ] WhatsApp Business API sends and delivery receipts are real and consent/approval protected.
- [ ] Demo/sandbox/live environments are never conflated.

## Regulated workflows

- [ ] Lending partner identity, terms, data scope and consent are explicit.
- [ ] Lender-owned eligibility/underwriting/status is not rewritten by AI.
- [ ] GST preparation is source-linked and CA-reviewed.
- [ ] Actual filing requires authorisation, exact payload review and official acknowledgement.

## Data and validation

- [ ] Forecasting has valid SKU-level sales/depletion and stock data and beats/justifies a baseline.
- [ ] Benchmarking uses sufficiently large comparable cohorts with privacy review.
- [ ] AI evaluation is representative, permissioned, versioned and human-reviewed.
- [ ] Real kirana pilot has documented baseline, outcome metrics and negative-outcome monitoring.
- [ ] Repeat usage and merchant correction effort are measured.

## Product integrity

- [ ] PostgreSQL is the only server-side application database.
- [ ] Existing PWA/Android and offline behaviour remains intact.
- [ ] Merchant approval remains mandatory for sensitive actions.
- [ ] No feature shows invented or stale data as live truth.
- [ ] All existing master-playbook regression tests still pass.

---

# 8. Completion status convention

Use these labels in documentation, UI/admin integration status and batch reports:

- **LIVE VERIFIED** — authorised production credentials and real production contract/event verified.
- **SANDBOX VERIFIED** — official sandbox/test environment and contract verified; not production-connected.
- **DEMO ONLY** — fixture/mock/manual simulation. Useful for demo, not a real integration.
- **BLOCKED — ACCESS** — needs credentials, partner enablement, approved account or API access.
- **BLOCKED — SPECIFICATION** — current official API/event contract or product support is not documented/available.
- **BLOCKED — LEGAL/CONSENT** — required agreement, permission, reviewer or consent basis is missing.
- **DATA NOT READY** — data volume, quality, coverage or provenance is insufficient for the feature.
- **PILOT NOT RUN** — measurement instrumentation exists, but no real merchant pilot has been completed.
- **MEASURED** — result has a documented method, dataset/cohort, date and limitations.

Never substitute “implemented” for “verified”, “connected”, “measured” or “adopted”.

---

**End of post-playbook implementation plan.**
