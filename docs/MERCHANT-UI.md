# Merchant UI redesign

Frontend-only changes: four persistent bottom destinations (Today, Deliveries & Stock, Customer Khata, More), with supplier/refund/report routes available in More. Existing sidebar is hidden; existing internal routes remain available. Today adds New Bill, Customer Udhaar and Settle Galla shortcuts. Udhaar opens a blank credit-sale form; Galla opens the existing cash drawer screen. Khata has per-customer credit and collection shortcuts without posting or selecting an allocation automatically.

Bill capture and delivery counts remain separate; the stock screen explains both steps. Missing/usable stock math and all posting rules remain unchanged. Case item arithmetic is expandable. Payment confirmation wording is simpler but checks, proof fields and approvals remain. Reminder preparation uses the existing reviewed WhatsApp/UPI flow and does not auto-send.

Touch controls, 16px inputs, focus outlines, card borders, semantic colours and bilingual destination/action labels are implemented with existing React/CSS. Today's sales use `manual_totals.today.sales_paise`; other balances retain their original coverage. It is explicitly labelled recorded sales, not a claim of complete shop sales.

No backend, data model, provider, integer-money, quantity or offline outbox changes. No new dependencies. Unrelated local files and cookies must not be committed.

Validation: 19 offline/exact-money tests passed; production build passed. New merchant-ui Playwright coverage checks four destinations, shortcuts, Galla, bill dialog, widths 320/390/844/1440 and navigation target heights, with page-error capture. Final result is recorded in the delivery message.

Limitations: this is a tested presentation increment, not a WCAG certification or a completed localisation of every secondary screen. Existing legacy browser specs use old navigation/wording and need migration before claiming a green complete browser suite. Only the new merchant-ui spec was run for this redesign; full backend regression was not repeated because backend files are unchanged. Technical server validation messages and deep administrative screens retain some terminology. No physical phone testing or new Android APK is claimed.
