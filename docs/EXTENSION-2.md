# Extension 2 — Local preparation and regulated boundaries

30 October 2026. **Safe preparation implemented; regulated integrations BLOCKED.**

## Changes and preserved behaviour

`backend/preparation.py` creates a bounded, source-linked preparation pack from immutable accepted purchase snapshots. Periods are explicit (up to 367 days, maximum 100 records; larger results fail rather than truncate). Exact integer-paise totals are purchase amounts, not unpaid debt, tax liability, sales or complete cashflow. The pack includes document IDs/hashes, original record routes, merchant-review status and unresolved exceptions; original bytes stay in existing scoped storage.

`backend/actions.py` and `app.py` add only `export_preparation` to the existing approval service. Proposals bind the exact payload, selected source IDs, digest and 15-minute expiry; execute/download recheck scope, creator/approver, permissions, expiry and current source versions/document hashes. Revision invalidates approval. Downloads use a repeatable-read PostgreSQL snapshot and leave an audit event. Export is JSON, with no spreadsheet formula interpretation. Raw customer contacts, document bytes and credentials are excluded.

`frontend/src/components/Preparation.jsx` is available under More → Connections & readiness. The merchant sees period, source records, totals, exceptions, purpose and local recipient before explicitly approving a download. Errors and server-denied permissions remain visible. No unreviewed document is called CA-ready, submitted, accepted or filed. Online preparation is required; the existing offline purchase draft path remains available and excluded until server acceptance.

`backend/tests/test_preparation.py` covers source linkage/exact totals, empty periods, tenant isolation, spoofed context, invalid periods, role denial, mandatory approval, stale sources, edited payloads and idempotent execution. Existing trust tests remain unchanged.

No new schema/dependencies, migrations, partner calls, consents, filings or loan applications. No external recipient can be configured. A local export approval is **not** permission for a lender or tax authority to receive data. Consent withdrawal/provider callbacks cannot be claimed tested because those workflows are not implemented or enabled.

## Documentation checked

Official [IRIS IRP sandbox access](https://einvoice6.gst.gov.in/content/kb/manage-sandbox-access/) checked 30 October 2026. Endpoint access requires registered sandbox settings; public documentation is not access. Filing/API schema version remains unverified for this project. No statutory GST validation, GST applicability or HSN determination is implemented. The current purchase model lacks GSTIN, HSN, place of supply and structured tax components; the pack explicitly records that exception.

No authorised lender, product, disclosures, terms or checklist was supplied. No lender API version is asserted. A qualified CA has **not** reviewed this output. No new reviewer role was added without a verified reviewer process. The owner explicitly confirmed these prerequisites are unavailable.

## Acceptance checklist

| Plan gate                                              | Status and evidence                                                                   |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Named authorised lender/current contract               | BLOCKED — ACCESS                                                                      |
| No local underwriting/offer promises                   | PASS safety boundary; no eligibility/terms/status generator exists                    |
| Consent before sensitive external sharing              | BLOCKED workflow; external sharing unavailable, local approval is not partner consent |
| Every shared field traceable/purpose-bound             | PASS for local pack only; source IDs, hashes, exact approval; partner sharing BLOCKED |
| Source documents/deterministic preparation totals      | PASS; immutable accepted snapshots, originals retained                                |
| Qualified CA validates outputs/exceptions              | BLOCKED — LEGAL/CONSENT                                                               |
| Official acknowledgement before filed/accepted         | PASS safety boundary; no filing/submission status can be created                      |
| Exact-payload review and explicit approval             | PASS local export; partner submissions BLOCKED                                        |
| Existing PostgreSQL/tenancy/offline product regression | Focused PASS; consolidated final verification follows Extension 3                     |

## Validation and rollback

`.venv/bin/python -m pytest backend/tests/test_preparation.py backend/tests/test_trust.py -q --tb=short`: **19 passed**, 0 skipped, existing Starlette warning. Ruff check/format: PASS. Final phone/PWA/Android build evidence is consolidated after all shared UI changes.

No migration: rollback code to the Extension 1 checkpoint if needed. Already-created preparation action/audit snapshots should be retained, not deleted. An older backend cannot execute this new action type safely; expire outstanding proposals or keep the new handler while rolling back UI.

Smallest next step: CA review and a scoped source-field/schema proposal, then an identified lender/IRP integration pack, legal/data-sharing/retention review, purpose-specific consent and real contract tests. Do not enable submission merely because an export exists.
