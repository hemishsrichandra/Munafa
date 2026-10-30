# Current demo walkthrough

## Prepare

Use PostgreSQL, migrate with Alembic, and create an owner or explicitly enabled development demo. No Paytm credentials are necessary. No real customer/supplier documents should be used for rehearsal.

`backend.manage seed-demo` creates a separate synthetic store and A-104 only when that store is empty. It never resets existing cases. If A-104 is present, open it under Purchases instead of adding the sample again. For a repeatable clean rehearsal, provision a new isolated demo store/schema rather than deleting old audit history.

## Supplier recovery

1. Sign in. Explain the synthetic-demo label and absence of live Paytm data.
2. Open Purchases. Add the synthetic sample if no A-104 case exists.
3. Confirm 10 biscuit packs, 6 tea packs and 24 soap pieces. The soap billed unit must be clarified to piece; match every received unit explicitly.
4. Confirm complete delivery and effective prices. Save, inspect the ₹80 calculation, then approve.
5. Download evidence or preview the supplier message. WhatsApp sending remains a merchant action. Do not send synthetic claims to real suppliers.
6. Confirm the sharing step only after sending, or explicitly say you are simulating it in this labelled demonstration.
7. Record a promise and follow-up date. Point out that no recovery is counted yet.
8. Verify credit/refund; load the synthetic credit, inspect it and attest application. Record the ₹80 once.
9. Reload the case to show persistence, then inspect recovery and historical approval evidence.
10. To export, use the recovery report and explicitly approve the private-store export dialog.

## PWA and mobile

Use the production build on port 8000. Open once online and wait for service-worker installation. The Install app control gives browser-specific guidance. Disconnect and reload: the shell should start while explaining that authentication, records and AI need connectivity. There is no offline draft/sync feature in this batch.

Show phone bottom navigation, card lists and receiving controls. Hindi/Kannada shell labels are previews; full workflow localization is not approved or complete. Browser voice remains optional with a touch alternative. No native microphone permission is requested.

## Honesty during evaluation

Live Sarvam use requires actual credentials and quality testing. Fixture loading is not AI extraction. Synthetic recovery is not measured impact. No stock, customer dues, forecast or payment-settlement dataset is connected. The Android wrapper shares the UI but native installation/permissions need separate device testing. Final video and presentation remain submission work.
