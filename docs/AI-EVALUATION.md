# Provider evaluation and routing decision — 30 October 2026

## Decision and evidence

Keep **manual entry as the default**. Retain the current Sarvam adapters as explicitly invoked, unverified cloud options. Prefer deterministic calculations and source retrieval for money, reconciliation and help. Speech is a disabled-by-default experimental note input; no selected language is field validated. No evidence currently justifies declaring Sarvam chat, dedicated Document AI, Textract or Azure the best invoice provider.

| Candidate                            | Implementation / empirical status                                                      | Cost per accepted invoice        |
| ------------------------------------ | -------------------------------------------------------------------------------------- | -------------------------------- |
| Fixture-format text parser           | 12 synthetic text cases; structural baseline only, not OCR                             | Unknown: no merchant acceptances |
| Current Sarvam chat / vision         | Implemented, strict schema and mocked failure/contract tests; zero live benchmark runs | Not measured                     |
| Sarvam dedicated Document AI Extract | Official async specialist candidate researched; not integrated or measured             | Not measured                     |
| Textract AnalyzeExpense              | Official specialist candidate researched; not integrated or measured                   | Not measured                     |
| Azure prebuilt-invoice               | Official specialist candidate researched; not integrated or measured                   | Not measured                     |

This report does **not** present mocked responses or a fixture parser as measured OCR performance. `evaluation/sarvam-unmeasured.json` explicitly has zero measured documents and null precision/recall/latency/cost. Private provider response files can be scored by the same runner after authorised collection. External access and human trials are outstanding acceptance gates.

## Corpus and repeatable scoring

`evaluation/corpus/invoices.json` has 12 public synthetic invoices, six calibration and six held-out cases, with supplier, reference, date, descriptions, quantities, units, printed prices and totals annotated. Matching SVG sources and raster PNGs include clean, low-light, skewed, faded thermal-like, mixed Kannada/Hindi/English, abbreviations, stamp/script-style note, fractional quantity, unreadable field and three injection variants. These are simulated typography/degradations, **not photographs or genuine handwriting**. No real merchant PII, tax ID, address, phone or bank identifier is included. Do not tune prompts on held-out cases.

```sh
.venv/bin/python scripts/build_eval_corpus.py
node scripts/render_eval.cjs
.venv/bin/python scripts/evaluate_ai.py --baseline --provider fixture-text-baseline --output evaluation/text-baseline.json
.venv/bin/python scripts/evaluate_ai.py --provider sarvam-chat-unmeasured --output evaluation/sarvam-unmeasured.json
.venv/bin/python scripts/evaluate_ai.py --predictions evaluation/private/PROVIDER.json --provider PROVIDER --split held_out --output evaluation/private/PROVIDER-report.json
```

Chromium must be installed; `PLAYWRIGHT_EXECUTABLE_PATH` can select an existing executable. Rebuilding fixtures changes only public synthetic artifacts. Private responses/human sheets belong under ignored `evaluation/private/`; never commit merchant documents.

The text-format baseline matched all 132 annotated field slots, including abstention for one unreadable total (131 known values). That demonstrates the scorer/fixture contract, **not general extraction accuracy**. Measured local parser P50/P95 processing times are in `evaluation/text-baseline.json`; these exclude upload/OCR/network and are not provider latency. There are zero merchant-accepted invoices and no human timing/correction trials. Human correction rate, correction-adjusted time and cost per accepted invoice remain null.

The runner computes field exact match, precision/recall over annotated values, field-difference proxy, failure rate and nearest-rank P50/P95 from recorded times. Quantities compare exactly as decimals. Null ground truth tests abstention. Missing provider responses are unmeasured, not successful calls or provider failures. Prediction files use a map from case ID to `draft`, `latency_ms`, `billed_cost_paise`, `merchant_accepted`, `task_time_seconds`, `correction_time_seconds`, `failed`; omitted measurements remain null. Verify billing and acceptance provenance before supplying values. Quality requires human annotation review; this small synthetic sample is not sufficient for merchant outcome claims.

For a real comparison collect consented/redacted representative images with independently checked ground truth and explicit train/held-out splits. Include poor lighting, blur/skew, thermal fading, scripts, product abbreviations, stamps, actual handwriting only if supported, and adversarial text/image/metadata. Freeze provider/model/settings. Capture failures, retries and total billed page/token usage, including rejected documents. Measure corrected task completion from upload/entry start to reviewed acceptance, using the same merchants/tasks with counterbalanced order. Divide **all billed costs** by verified accepted invoices, not successful API calls. Report confidence intervals and sample size; compare against manual entry, not only another model.

## Official sources and dated pricing review

Provider comparison metadata and gates: `evaluation/provider-candidates.json`. Current official sources checked on **30 October 2026**:

- [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing): chat uses token billing, speech uses duration billing, translation uses character billing, document products list page billing. Published rates are plan dependent and exclude GST; there is no hard-coded invoice price in the app. Confirm actual billed usage, retries and page rounding in the account before a cost claim.
- [Sarvam limits](https://docs.sarvam.ai/api/getting-started/ratelimits): limits vary by API and account plan. HTTP 429/credit errors fall back to manual entry; the app does not retry indefinitely.
- [Document AI overview](https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/overview): dedicated parse/extract jobs are alternatives to chat prompting. Job setup, polling, field geometry, page/size limits and billing need authorised contract tests before implementation. The current bounded PDF helper reads a text layer; it does not perform scanned-PDF OCR.
- [Textract invoice/receipt contract](https://docs.aws.amazon.com/textract/latest/dg/invoices-receipts.html), [pricing](https://aws.amazon.com/textract/pricing/): specialist candidate; verify region, quotas and mixed-script fit.
- [Azure invoice model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/invoice?view=doc-intel-4.0.0), [pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/): specialist candidate; validate supported languages and regional terms.

A dated published pay-as-you-go snapshot (₹, excluding GST; **not application constants or a quote**): Sarvam-105B input/output ₹15/₹60 per million tokens; Gemma4 ₹35/₹90 per million tokens; STT ₹0.49/minute; translation ₹2/1,000 characters; document extraction ₹1/page. Recheck current plan/account billing and job-contract applicability before estimating or comparing cost. No accepted-document cost can be calculated from these list rates alone.

Public documentation confirms a candidate contract exists, not this team's account access or accuracy. No provider was silently contacted during this benchmark. Commercial terms, processing regions, subprocessors, training use and deletion assurances must be checked in the team's actual contracts before real documents are sent.

## Speech/touch and translation acceptance matrix

Use `en-IN`, `hi-IN`, `kn-IN` as **preview choices**, not validated language support claims. Test each on Android Chrome/PWA and the packaged Android WebView (native microphone intentionally unsupported), plus supported desktop/iOS browsers; quiet shop vs fan/traffic/customer noise; regional accents/code-mix; good, slow, offline and interrupted network; permission granted, denied and revoked; recording start/stop/cancel, route change and background interruption; invoice notes, quantities and supplier-message drafts.

For each task record correct completion, human corrections, correction-adjusted task time, abandonment and touch baseline. No raw audio retained by default. Use consented test recordings only in private evaluation storage when explicitly approved. Current evidence: mocked STT valid/unclear/missing-key paths, MIME/signature/consent/permission gates and simulated browser permission denial. No real speaker/device/noise benchmark has run; no claim voice is faster or accurate is made. Translation preserves a visible source, flags numeric mismatches, requires review before copy/share and never sends automatically.

## 31 October validation extension

See [five-improvement validation](FIVE-IMPROVEMENTS-VALIDATION.md) for the five owned image fixtures, bounded Sarvam-only runner and null-metric availability report. The key is Render-only; the owner chose no live benchmark. Zero provider calls were made. Thermal/handwriting images are typography proxies, not real invoices. Human corrections, timing, accepted-invoice cost and device/pilot outcomes remain unmeasured.
