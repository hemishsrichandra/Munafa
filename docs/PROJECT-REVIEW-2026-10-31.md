# Munafa / Paytm Business Partner — project assessment

31 October 2026. Reviewed current source through header-fix commit **09d013d**, runtime checks, database-backed regressions, browser journeys and prior evidence. This is an engineering/product assessment, not an independent penetration test, legal review or measured merchant-outcome study. The header fix is implemented and pushed; improvements below are proposals, not additional features implemented during this review.

## Verdict and scoring

**7/10 as a focused hackathon prototype. 4/10 for readiness to launch broadly with real merchants.** The purchase → physical receiving → inventory → supplier recovery core is materially stronger than the wider “AI business partner” feature breadth. These are subjective assessments weighted toward actual behaviour and evidence, not a test-derived numeric benchmark or a claim about judge scoring.

| Angle                            | /10 | Assessment                                                                                                                                                                                                                                             |
| -------------------------------- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Core merchant workflows          | 8   | Reviewed purchases, separate partial/final receiving, stock events and evidence-backed recovery work end to end. Legacy and newer purchase entry paths still fragment the experience.                                                                  |
| Financial/domain integrity       | 9   | Exact paise/decimal quantities, approval digests/versions, immutable evidence and append-only events, transaction/idempotency and proof guards have meaningful tests. No external verification that a merchant-entered recovery really reached a bank. |
| UI, accessibility and onboarding | 7   | Coherent visual language, phone navigation, labels, touch controls and responsive checks. Header overlap is fixed. Demo starts with weak next-step guidance; full screen-reader/device/language acceptance is absent.                                  |
| Offline/PWA                      | 8   | Durable scoped IndexedDB drafts/outbox, retries, conflicts, logout cleanup and warm-cache shell launch are tested. Storage eviction still loses unsynced data; cloud services require internet.                                                        |
| AI and language quality          | 5   | Safe extraction proposals and manual fallback; prior documented synthetic translation/STT smoke calls. No representative measured image-OCR accuracy or merchant correction/time/cost benchmark. Help is bounded keyword retrieval.                    |
| Live integrations                | 3   | Live Paytm and partner execution remain disabled. Deterministic reconciliation works on synthetic fixtures. No verified automatic settlement/POS feed or delivered-message channel.                                                                    |
| Identity/security/privacy        | 6   | Signup, isolated demo, hashed passwords, secure sessions, CSRF, tenant/role guards and denial tests. Recovery/identity verification, distributed abuse controls, retention and broader upload/privacy review remain.                                   |
| Testing/maintainability          | 8   | Substantial PostgreSQL and mobile workflow regressions with honest skipped/unmeasured distinctions. Large UI files/CSS cascade and parallel legacy/new paths increase change risk.                                                                     |
| Deployment/operations            | 4   | Render PWA is reachable and latest header CSS verified. Actual backup policy, production restore, monitoring/SLOs, native release and real-device coverage are not established.                                                                        |
| Demonstrated merchant impact     | 4   | A credible operational problem and auditable completion exist. No consented merchant pilot, repeat-use evidence, correction-adjusted time study or independently verified recovery outcomes.                                                           |

A safer disabled integration deserves credit for truthfulness, but cannot be counted as a working integration. Test counts demonstrate regression coverage, not successful adoption, high OCR accuracy, complete security or profitability.

## What genuinely works

- Account creation produces a new private merchant/store owner and logs in. Public demo visitors receive distinct synthetic tenants. Existing administrator provisioning and password rotation CLI remain. No Paytm identity claim.
- Purchase capture supports manual/source intake and merchant review; accepted invoice does not increment stock. Original documents/extraction revisions are preserved. No key is required for manual entry.
- Independent receiving handles explicit quantities/units, partial vs complete deliveries and damaged goods. Fractional quantities use exact decimal validation. Inventory is derived from accepted append-only events, not payment totals or billed quantities.
- Original intake → confirm → approve → share handoff → promise → evidence-backed partial/full recovery survives. Supplier identity/reference/proof duplication, applied-confirmed gate, remaining balance and immutable snapshots remain significant strengths.
- Source-backed brief covers approved claims, stock thresholds, actual expiry records and observed reconciliation exceptions. It does not invent customer dues or SKU sales.
- Labelled fixture settlement reconciliation explains verified components and differences. Fixtures cannot turn into live bank verification.
- Scoped offline drafts, attachment capture, dependency-ordered queue, retries, expected versions and visible conflicts are tested. Logout clears private device data and stops old-context sync; offline logout still needs eventual server revocation.
- Allow-listed read/draft help, strict AI proposal validation, invalid-output budget and manual fallbacks are implemented. Provider configuration is not equivalent to provider accuracy.
- PWA public shell works after connected warm-up; an Android wrapper shares the frontend. Historical debug APK build evidence exists, but that artifact is not proof the newest UI/auth works on an installed phone.

Primary source files: backend/domain.py, actions.py, purchasing.py, inventory.py, store.py, sync.py, auth.py, brief.py, payments.py; frontend/src/offline/, session.jsx, components/Commerce.jsx and CaseActions.jsx. Existing regression tests under backend/tests and tests/e2e exercise these boundaries.

## Concrete gaps and recommended changes

### 1. First-run demo does not demonstrate the product's best workflow — high priority

**Verified in a new disposable PostgreSQL test:** public demo creates one A-104 legacy case in review; `/api/brief` returns no actions; `/api/purchases` is empty. Offering “Use sample invoice” again returns a correct duplicate 409. Home's “You're all caught up” can therefore appear while an existing bill still needs review. The duplicate guard is correct; onboarding is the problem.

Evidence: backend/auth.py public_demo; backend/samples.py demo_seed; backend/brief.py only promotes ready/sent/promised/partial cases; frontend/src/components/BusinessBrief.jsx empty copy; InvoiceIntake.jsx offers the same sample; backend/app.py insert_invoice duplicate check. Temporary reproduction: /private/tmp/test_munafa_demo_review.py, one passed test, scratch schema only.

**Proposal:** a source-linked “Review your sample invoice” / “Continue receiving” next action, a single guided purchase-to-recovery starting point, and opening the existing sample rather than trying to create it again. Keep demo records labelled; do not pre-confirm delivery or manufacture applied recovery. Offer deeper settlement/stock scenarios as explicit synthetic walkthroughs.

**Acceptance:** first-time visitor reaches the seeded bill in one tap, never sees an avoidable duplicate error on the default demo path, and completes a merchant-confirmed receiving/recovery walkthrough. Measure completion and time; do not invent a conversion rate.

### 2. Registration is functional, but account lifecycle is incomplete — before real onboarding

No verified email/phone, self-service password reset, invitation/member management or reviewed in-app privacy/retention flow. Role enforcement exists, but that is not a staff-administration UI. Default-owner auto-creation was removed; an already-provisioned owner still needs owner-executed rotation. This review did not inspect credentials or run that rotation.

A smaller correctness issue was reproduced without touching a database: LoginBody and SignupBody inherit StrictModel's str_strip_whitespace=True, so leading/trailing password whitespace is silently removed. CLI provisioning/password changes hash the exact supplied string. Such CLI-created passwords can therefore behave inconsistently in web sign-in.

**Proposal:** decide invitation-only pilot vs verified self-service signup; implement token-expiring password recovery using an approved channel; preserve exact password bytes independently of normalised usernames; add account/session management. Never weaken session or tenant checks for convenience. Test recovery replay, enumeration-safe responses and whitespace/password round trips.

### 3. Public demo has bounded storage, but not complete abuse/cost/retention operations — before scaling public access

Current demo cap is 500 total public demo stores by default, enforced in PostgreSQL across workers. Sessions expire in 12 hours; records do not auto-expire. Per-IP limits live in process memory. New demo owners can reach the existing provider-backed workflows if configured; no global provider-spend budget is implemented. Anonymous visitors can therefore consume capacity or billable requests within existing limits. Capacity rejection is safe, but not a long-term retention policy.

**Proposal:** monitored public-beta limits, explicit daily provider budgets, distributed/edge rate limiting appropriate to the deployment, and an approved retention/cleanup process. Any cleanup touching immutable evidence needs a reviewed design and backups; do not add blind deletion or disable audit triggers. Define what happens to abandoned drafts and uploaded documents. Audit events/telemetry and browser storage do not constitute device encryption.

### 4. AI usefulness has not been established on real invoices — highest priority AI work

The public corpus is 12 synthetic cases; the perfect text baseline is a fixture parser, not image OCR. evaluation/sarvam-unmeasured.json reports provider results as unmeasured. docs/LOCAL-FIX-REPORT.md records real synthetic translation and STT smoke requests, which establish bounded access, not noisy-shop speech or invoice accuracy. Live health currently advertises speech_preview:false; local historical enabled state is not the deployed configuration.

**Proposal:** collect consented/redacted kirana bills and independent field ground truth; freeze provider/model settings; benchmark invoice extraction against manual entry across held-out conditions. Report field exact match, missing critical fields, merchant corrections, corrected completion time, failure rate, P50/P95 and all billed cost per accepted invoice. A proposed initial engineering sample is 30–50 diverse bills, explicitly insufficient to establish broad population performance. Increase evidence before claims.

A concrete parsing gap: backend/pdf_text.py limits total extracted text to 18,000 characters and stops without an explicit truncation flag. A text-heavy PDF can yield a partial extraction while still reporting original page_count. Scanned PDF OCR is not enabled. Add explicit completeness/truncation status and review safeguards rather than silently implying every page was processed. Existing file-signature/active-PDF checks are bounded guards, not full malware scanning/content disarm.

### 5. Grounded help is narrower than a multilingual copilot

backend/help.py matches a small curated corpus using `[a-z]+` tokens and English keywords. Hindi/Kannada-only questions will not match that index without English terms. The sources have fixed review-expiry dates; there is no autonomous approved-source review pipeline. Source citations and abstention are strengths. This is not broad conversational financial reasoning or a live Paytm support agent.

**Proposal:** evaluated multilingual query handling/aliases, task-specific help from existing source records, and a source-review/refresh process. Expand approved material only as needed; avoid arbitrary web retrieval or a framework rewrite. Keep policy, store facts and explanation separate. Validate Hindi/Kannada task copy and voice correction burden with actual speakers before claiming complete language support.

### 6. Live integrations and broad modules remain external or data gates

- Paytm settlement/live payment adapter: disabled; no authorised end-to-end contract test. Synthetic deterministic reconciliation works.
- Soundbox/POS, WhatsApp delivery, lender and GST/IRP execution: unavailable/gated, not operational integrations. A WhatsApp handoff is not a delivery receipt.
- Customer receivables, CRM/marketing, expense bookkeeping and staff task workflows: absent as complete business modules. P1 completeness is not established by readiness screens.
- Demand forecasting and procurement/financial planning/peer benchmarking: readiness/gates, not working engines. Actual SKU sales/coverage and consented cohorts are absent. Keep these suppressed.
- Preparation exports are source-linked purchase packets; missing GSTIN/HSN/place-of-supply/category data and CA review prevent representing them as complete statutory accounts.

**Proposal:** prioritise authorised settlement access only if available. Otherwise show the synthetic reconciliation honestly. After the core pilot, choose one justified next module (e.g. merchant-entered receivables) with provenance/consent, rather than implementing every roadmap tile at once. Do not infer debts or SKU sales from UPI totals.

### 7. Scale and maintainability need measurement before optimisation

Source inspection shows full-list reads and per-record queries: store.all_cases reconstructs case history, brief.build iterates cases/products/lots, inventory.products queries balances per SKU, and legacy duplicate checking iterates loaded cases. These are scale risks, not measured evidence of current slowness. No realistic multi-store load test or slow-query profile was run.

Current large files: frontend/src/components/Commerce.jsx ~1,176 lines, styles.css ~4,614, backend/app.py ~831, purchasing.py ~750. The header issue arose from accumulated fixed/in-flow layout overrides.

**Proposal:** paginated list/detail APIs and aggregate brief queries based on measured query counts; scalable duplicate indexes; benchmark realistic catalogue/event histories. Incrementally extract a few cohesive UI modules and consolidate obsolete CSS rules as touched. Preserve domain contracts and regression tests; no rewrite/state-library migration is justified. Add sanitised correlation/error monitoring; redacted generic 503 responses alone are not operational diagnostics.

### 8. Deploy and device evidence is incomplete

render.yaml selects free web/PostgreSQL plans; actual subscribed dashboard plans were not inspected. Render documents cold-start/free-service limits, no free web Shell, and 30-day expiry/no managed backups for Free Postgres: https://render.com/docs/free and https://render.com/docs/ssh, checked 31 October 2026. If the deployed database uses that plan, it is inappropriate as the only store for real merchant records. No production backup restore was performed; scratch-schema/database restore tests do not prove it.

**Proposal:** confirm actual plan/lifecycle, enable appropriate backups and rehearse restore with approved data controls, monitor errors and availability, and confirm secrets/provider retention. Keep migration/rollback operations explicit; never downgrade populated finance tables casually.

Native wrapper configuration exists, but the current review did not rebuild an APK or test an Android device. Rebuild the same frontend against the deployed HTTPS API, verify the configured native origin/CORS/auth rather than guessing, and test install, camera/file permissions, pause/resume, offline reload and reconnect. Debug signing is not a release-signing plan. Browser success does not prove native lifecycle behaviour. Test browser screen-reader semantics and real phone ergonomics beyond automated label/overflow checks.

## Recommended sequence

1. **Before presenting:** header release (done), guided existing-sample action, coherent purchase/receiving/recovery narrative, honest live/demo labels. These are the highest return usability changes.
2. **Before accepting real pilot data:** account/credential review, recovery policy, actual hosting/backup plan, privacy/provider sharing/retention decisions, public abuse/spend limits and device acceptance.
3. **Next bounded evaluation phase:** representative OCR/manual baseline; approved translation/speech tasks; instrument completion/correction without unnecessary PII. Test on a real Android phone and actual shop-like network conditions.
4. **Merchant pilot:** proposed 3–5 consented kiranas for a short supervised trial. Measure correction-adjusted capture/receiving time, verified applied recovery, ledger-vs-physical stock accuracy, useful completed actions, false alerts and repeat use. No outcome lift should be claimed beforehand.
5. **Then expand:** one data-justified module at a time. Authorised Paytm feed, merchant-created receivables or sales/POS coverage may unlock value; forecasts and autonomous procurement should remain gated until their evidence exists.

## Evidence and exact limits

- Complete browser run after header change: `PLAYWRIGHT_EXECUTABLE_PATH=/Users/hemish/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell npm run test:e2e` — **27 passed**, including build, header geometry/guidance/offline, signup/demo, recovery, narrow/rotated layouts, offline response loss, conflict and account switch.
- `npm run test:offline` — **18 passed** after header change.
- Latest full backend run in the preceding auth release: `.venv/bin/python -m pytest backend/tests -q` — **268 passed**, one known Starlette/httpx deprecation warning. Header release changed no backend code; this review did not rerun that entire unchanged suite. One additional temporary PostgreSQL test reproduced demo next-step/duplicate behaviour and passed; it is diagnostic evidence, not an extra committed passing test.
- `npm run format:check`, Ruff check and production build passed. Latest release audit: **251 files**, zero known-private-configuration matches, zero SQLite imports, **67 API operations**. This bounded scan is not a full secret-history scan or security certification.
- Header fix is live: anonymous GETs returned site/CSS 200 and the new min-width:761px sticky-sidebar rule in `/assets/index-MHelXG7e.css`. Earlier explicitly approved live demo sign-in/logout passed; no additional production tenants or business events were created for this review.
- Not performed: live merchant signup, new real provider OCR benchmark, real merchant pilot, load/penetration/accessibility certification, new APK build, physical device tests or production backup/restore. Feature counts in older documents are historical taxonomy, not proof every supplied batch was completed.

## Owner inputs that would unlock progress

No new secret is needed for the header or current signup/demo. Sarvam is already configured according to live health; never paste that key in chat. Useful next inputs are: confirmation of the owner-password rotation, actual Render database plan/backup ownership, a test Android device, consented redacted invoices and intended language/device targets, an approved small provider evaluation budget, and a decision on supervised pilot versus public signup. Paytm/WABA/POS/lender/GST packs remain external gates; earlier confirmed absence should be respected until the owner says access exists.
