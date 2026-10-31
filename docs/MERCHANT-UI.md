# Merchant UI redesign

## Final tested stop checkpoint

The final complete browser run passed **35/35** journeys with no failures, including the added accessibility scan. **20** offline/exact-money/display tests passed. Automated WCAG A/AA scans found zero violations across the four main destinations and bill dialog after contrast repairs. Missing-item badges require final delivery and exact saved decimal counts; expiry warnings have explicit text and semantic pills. Secondary-screen and phone-saved entry wording was simplified. No backend models, calculations or outbox engine were changed. Production dependency audit reports zero vulnerabilities; 4 moderate development-tool advisories remain. User explicitly requested no further feature implementation; continuation context is in ANTIGRAVITY-UI-CONTEXT.md. Earlier checkpoints below are historical.

## Regression completion

Legacy browser specs have now been migrated to the four-tab navigation and new labels. All **34 distinct browser journeys passed across isolated spec runs**: auth 2, commerce 3, extension 1, header 1, merchant UI 1, offline 6, onboarding 2, partner 3, polish 1, records 3, recovery 1, release 2, workflow 8. Initial failures exposed stale selectors; corrected specs were rerun with their money, stock, source-link, partial/full recovery and account-isolation assertions retained. This is not a claim of one uninterrupted green run. After these checks a small presentation fix restored language-selector labels on all four tabs; the dedicated merchant-UI journey includes switching Hindi/English and is rerun for that fix.

The new customer and purchase paths are now covered beyond empty-state navigation. Source audit: 362 files, zero configured-secret findings and zero SQLite imports. Backend and outbox code remain untouched in this continuation. The 19 storage/money tests passed in the preceding UI increment. No formal accessibility certification or physical-device testing is claimed.

Frontend-only changes: four persistent bottom destinations (Today, Deliveries & Stock, Customer Khata, More), with supplier/refund/report routes available in More. Existing sidebar is hidden; existing internal routes remain available. Today adds New Bill, Customer Udhaar and Settle Galla shortcuts. Udhaar opens a blank credit-sale form; Galla opens the existing cash drawer screen. Khata has per-customer credit and collection shortcuts without posting or selecting an allocation automatically.

Bill capture and delivery counts remain separate; the stock screen explains both steps. Missing/usable stock math and all posting rules remain unchanged. Case item arithmetic is expandable. Payment confirmation wording is simpler but checks, proof fields and approvals remain. Reminder preparation uses the existing reviewed WhatsApp/UPI flow and does not auto-send.

Touch controls, 16px inputs, focus outlines, card borders, semantic colours and bilingual destination/action labels are implemented with existing React/CSS. Today's sales use `manual_totals.today.sales_paise`; other balances retain their original coverage. It is explicitly labelled recorded sales, not a claim of complete shop sales.

No backend, data model, provider, integer-money, quantity or offline outbox changes. No new dependencies. Unrelated local files and cookies must not be committed.

Validation: 19 offline/exact-money tests passed; production build passed. New merchant-ui Playwright coverage checks four destinations, shortcuts, Galla, bill dialog, widths 320/390/844/1440 and navigation target heights, with page-error capture. Final result is recorded in the delivery message.

Final language check: the merchant-UI journey passed again after restoring language selection, including Hindi/English switching. Homepage returned HTTP 200.

Limitations: this is a tested presentation release, not a WCAG certification or a completed localisation of every secondary screen. Browser specs have been migrated and all 34 distinct journeys passed across the runs documented above. Full backend regression was not repeated because backend files are unchanged by this UI work. Technical server validation messages and deep administrative screens retain some terminology. No physical phone testing or new Android APK is claimed.
