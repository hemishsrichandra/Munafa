# Batch 7 — bounded AI drafts, language and grounded help

Implemented 30 October 2026, following tested Batch 6 checkpoint `9408088`. PostgreSQL migration `c6ec82a178d3` adds minimal store-scoped provider telemetry; no existing merchant records are rewritten.

## Delivered

- Narrow document, STT, translation and reasoning interfaces in `backend/providers.py`; current Sarvam document adapter invokes a strict billed-field schema with review-only metadata. Dedicated document providers are documented candidates, not guessed integrations. No extra runtime dependency was added.
- Two-invalid-output budget persisted by store/source digest across HTTP failures and app restarts. Missing key, timeout, rate limit, unreadable PDF and invalid schema return manual alternatives; original purchase documents remain preserved. Merchant acceptance still requires exact deterministic totals, units/SKU mapping and effective prices. AI cannot set actual receiving, approve, create inventory events, record payment, promise or resolve recovery.
- Existing legacy invoice adapter retains its contract, clears model receiving data and shares the invalid-output budget. Printed rupee conversion happens with Decimal server-side, not an instruction to the LLM to calculate money. Provider requests are bounded to 20 seconds (5-second connect); no automatic indefinite retries. User retry stops after two invalid structured outputs.
- Authenticated `/api/assistant/capabilities`, `/translate`, `/speech`, `/help`, `/sources/{id}` and `/usage`. Only minimally necessary provider telemetry is stored; billed cost and completed-task cost remain unknown. Read/write/messaging roles are checked server-side.
- Voice-note preview with consent, microphone permission, visible start/stop/cancel, 20-second/2 MB client bound, track release and manual text fallback. Server checks file format/size/consent and preview flag. No native microphone permission or raw-audio persistence. `ENABLE_SPEECH_PREVIEW=0` by default; selected language/device/noise validation remains outstanding. Legacy browser voice no longer populates a physical received quantity automatically.
- Source/translation comparison, numeric mismatch warning, explicit merchant review before translated copy/share, no sending. The previous supplier-message workflow remains available with its original English draft.
- Deterministic extractive help over versioned repository product guidance and one dated official Paytm technical excerpt. Source sections/versions/dates/citations, explicitly selected principal-scoped case/SKU/brief facts, unsupported/stale/contradictory abstention and support routing. Allow-listed typed follow-up draft tool requires an approved case and messaging permission, performs no mutation, and routes back to the original workflow. No arbitrary URL retrieval or uploaded-document RAG.
- Bundled public product help is available with the offline workspace; authenticated AI/API responses remain excluded from shell caching.
- Twelve public synthetic invoice cases, SVG/PNG variants and ground truth with calibration/held-out split; offline evaluation runner and researched provider comparison. See AI-EVALUATION.md for measured baseline, unmeasured provider status and acceptance gates.

## Provider/model decision and measurement

Manual capture + deterministic reasoning/retrieval remain the default. Optional current models: configured `sarvam-105b` for text, `gemma4` for images, `mayura:v1` for translation and opt-in `saaras:v3` speech preview. Names identify adapter settings, not a ranking or live validation claim. Dedicated Document AI, Textract and Azure remain unintegrated evaluation candidates until credentials/contract and representative measured results justify changes.

The text-format parser matched 132 synthetic annotated field slots, with zero merchant acceptances. This is scorer/fixture validation, not OCR accuracy or merchant improvement. Cloud accuracy/latency/cost, human correction rate and correction-adjusted voice/touch time remain **not measured**. Real provider and real device/speaker evaluations cannot be substituted with mocks. No provider winner, live Paytm or voice speed benefit is claimed.

## Tests / checks

The final test counts and commands are in HANDOFF.md. Coverage includes missing key, malformed/authority schema, fractional values, invalid budget and store isolation, provider timeout/429, preserved source, no inventory/finance mutations, consent/MIME/signature gates, translation mismatch, mocked noisy/unclear speech, simulated browser permission denial, cited help, stale/missing/contradictory sources, forbidden tools, cross-tenant reads, approved draft source/role checks, evaluator honesty, legacy workflow and mobile/offline regressions.

Phone checks cover 320/360/390/430px and the existing full PWA/offline suite. Real microphone acquisition, noisy speakers, actual provider contracts and native device tests are not claimed. New source forms use explicit labels, statuses, manual fallbacks and comfortable actions; no framework/state-library/CSS replacement occurred.

## Documentation and data handling

Read AI-EVALUATION.md, AI-DATA-HANDLING.md and PAYTM-INTEGRATION.md. `.env.example` documents optional speech flag/model; `.gitignore` excludes private evaluation artifacts. Public corpus contains synthetic records only. Telemetry currently has no automatic deletion job; actual local and provider retention is documented honestly. Owner must verify provider retention, regional processing and contractual terms before real documents/audio.

Additive migration has been tested through disposable-schema up/down and metadata drift checks. Production/application downgrade, reset and legacy import were not performed. Existing pre-Batch 6 backup remains private; no verified restore is claimed.

## Outstanding acceptance gates / next phase

Authorised live AI corpus runs and billing verification; independently checked real-image ground truth; counterbalanced merchant correction/time studies; real language/device/noise matrix; approved Paytm environment/credentials/signature contract and end-to-end test; Android device acceptance and hosted HTTPS API; production identity, backups/restore, retention/scanning and privacy review. These are recorded limits, not fabricated test results.

Batch 8 specification was supplied as future context. No receivables/CRM/forecast/fraud/GST/staff module was implemented. Obtain explicit Batch 8 approval before starting it.

## Final local APK evidence

Debug APK: `artifacts/munafa-debug.apk` (ignored), **4,456,913 bytes**, SHA-256 `644d49e220f43278b63686706ee050a28d305929a448aa8513a8cf8f8c9ebcf0`. `assembleDebug lintDebug` passed; 0 lint errors and 28 existing warnings. Packaged public assets byte-match the final React build. This is a debug artifact without a configured hosted HTTPS API or device acceptance.
