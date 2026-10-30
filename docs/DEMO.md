# Hackathon demo — synthetic kirana rehearsal

Batch 10 · 30 October 2026. This is a **demo candidate**, not a production or live Paytm release. All supplier proof and settlement fixtures in this walkthrough are synthetic. Do not send them to real suppliers or lenders.

## Clean start / repeatable reset without deleting merchant records

Install the locked dependencies and configure a **dedicated PostgreSQL** TEST_DATABASE_URL in private `.env` using README. Apply the normal development migration if using the normal app, or use this disposable rehearsal server:

```sh
npm ci
npm run build
node scripts/python.cjs scripts/serve_e2e.py
```

Open `http://127.0.0.1:8001`. The runner creates a fresh random PostgreSQL `e2e_...` schema and explicitly synthetic accounts, binds loopback only, forces cloud keys off and disables P2/speech previews. Use username **release-owner**, password **isolated-browser-test-password**. These are deliberately public **disposable test credentials**, not production credentials. Do not deploy this runner or use real documents. The active store is assigned by the verified session; there is no interactive store selector.

For another clean take, stop this runner with Ctrl+C, sign out/clear its private browser workspace, and start it again. Only the runner's own generated schema is cleaned; a new run uses a new namespace. Never truncate audit/financial tables, reset public/application schemas, import `.data` files or delete an existing merchant store. After an abrupt process kill, a disposable schema may remain; leave it for reviewed cleanup and start a fresh namespace. Do not guess a schema to drop.

`backend.reset_demo` remains deliberately disabled. `backend.manage seed-demo` only seeds A-104 if its separate demo store is empty; it is not a reset command. Ordinary app data and existing financial history are preserved.

## Four-minute presentation script

| Time      | Merchant task / what to show                                    | Honest narration                                                                                                                                             |
| --------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0:00–0:25 | Sign in, home brief, synthetic store label                      | “This is one verified store. Actions link to recorded evidence. Payments are unavailable until we explicitly load a simulation.”                             |
| 0:25–1:10 | Capture bill photo, manual fallback and review                  | “No AI key is needed. Extraction is a draft; the merchant checks quantities, units and prices against the original.”                                         |
| 1:10–1:50 | Physical receiving and stock timeline                           | “The bill did not add stock. Only accepting the physical receipt added the 2 kg that arrived.”                                                               |
| 1:50–2:50 | ₹40 shortage approval, simulated share, promise, two ₹20 proofs | “A promise is not recovery. Each applied amount needs distinct matching evidence; the remaining balance stays open until verified.”                          |
| 2:50–3:20 | Separate settlement simulation                                  | “Known fee, GST and refund fields explain part of the payout. The ₹8.20 difference needs review; this is not a claim of missing money or a live Paytm feed.” |
| 3:20–4:00 | Saved offline draft → reload → reconnect/sync                   | “Saved on this device is provisional. A timeout is retried with the same operation ID; acceptance or a visible conflict comes from the server.”              |

Do not claim these timings are measured merchant savings. The script duration is presentation pacing only. Automated local timings and their limitations are in BATCH-10.md; real merchant correction-adjusted task-time studies have not run.

## Exact purchase / receiving / recovery take

1. Under Purchases → stock, create SKU code `DEMO-RICE`, name `Rice`, unit `kg`. An optional reorder threshold of **3 kg** is the demonstrator's explicitly chosen simple rule, not an AI forecast.
2. Purchases → New purchase → choose `evaluation/corpus/images/fractional.png` → Read document. This is a rendered public synthetic bill, not a real camera image. With keys off the original is saved and manual fallback is shown.
3. Review the exact printed source: supplier **Synthetic Wholesale 11**, reference **SYNTH-11**, date **2026-10-29**, description **ಅಕ್ಕಿ / चावल**, billed **2.5 kg**, printed unit price **8000 paise (₹80)**, effective claim unit price **8000 paise**, subtotal/total **20000 paise (₹200)**, tax/discount **0**. Select the reviewed Rice SKU. Enter zero rounding. Confirm effective-price interpretation manually.
4. Save the draft, inspect the original, then confirm the reviewed invoice. Stock is still **0 kg**. No received quantity came from extraction.
5. Record a physical delivery: actual **2 kg**, damaged **0 kg**. Explicitly confirm units, delivery complete and effective prices. Save the receiving draft, review it, then accept it. Stock is **2 kg**, with one accepted receipt event. Do not enter an expiry date unless demonstrating a separately observed synthetic batch.
6. Open the linked supplier case. Deterministic shortage: `(2.5 − 2) kg × ₹80 = ₹40`. Approve the evidence. Show the source link and immutable snapshot.
7. Prepare the English supplier-message draft. Show the WhatsApp **handoff link** without opening/sending it. Explain aloud that sharing is being simulated in this isolated demo, then explicitly confirm the simulated share. No message delivery or supported messaging integration is claimed.
8. Record a supplier promise such as “₹20 on the next bill; balance later,” with a real current follow-up date. Recovered money remains **₹0**.
9. Verify credit/refund: enter **₹20 before loading synthetic proof**. Open/inspect its **SYNTHETIC EVIDENCE** watermark, supplier/reference/amount, then explicitly check application confirmation and record it. Status is partial, recovered ₹20, remaining ₹20.
10. Repeat with the remaining ₹20 and a distinct generated proof/reference. Status becomes resolved; recovered ₹40, remaining ₹0. Stock remains **2 kg**: recovery did not silently change inventory.
11. Reload and reopen the purchase/case. Review receipt timeline, original invoice and approval/audit trail. Use the explicit approved export workflow if showing CSV. Formula-like merchant strings are escaped for spreadsheet consumers.

This exact connected phone journey is exercised in `tests/e2e/release.spec.js`. The legacy A-104 ₹80 supplier flow remains independently tested. Synthetic evidence is not a verified real-world credit or bank receipt.

## Separate Paytm settlement simulation

More → Payments & reconciliation → Load isolated synthetic payment demo. Do not mix it with a live mode display. `backend/fixtures/settlements.json` records:

| Component                 | Synthetic amount |
| ------------------------- | ---------------: |
| Collection / gross        |        ₹1,000.00 |
| Commission                |          −₹10.00 |
| GST on fees               |           −₹1.80 |
| Refund                    |          −₹50.00 |
| Reversal / adjustment     |    ₹0.00 / ₹0.00 |
| Component net             |          ₹938.20 |
| Recorded simulated payout |          ₹930.00 |
| Difference for review     |           −₹8.20 |

The fixture also records cutoff/settlement/payout/observation timestamps. Depending on elapsed time, the source is marked stale. Explain component evidence and timing review candidates, not a guaranteed bank receipt or an invented settlement cause. Live mode remains disabled: no authorised credentials, environment/signature contract or end-to-end Paytm test exists. Reloading the fixture is idempotent and does not rewrite historical observations.

## Offline / conflict take

Warm the production shell online and wait for service-worker readiness; the first install/cache needs connectivity. Open Drafts & sync. Save a manual invoice or receiving draft and a synthetic attachment. Disconnect, reload and inspect the same saved draft. Local state must say Saved on this device/Waiting to sync, never server-accepted stock or recovery. Reconnect, explicitly queue/sync and inspect the result. If a source version changed, show Conflict/Needs attention and review the latest source instead of overwriting it.

Automated tests cover durable invoice/receiving state, attachments, quota failure, expired auth, stale versions, dependency ordering and an intentionally lost server response with exactly one acceptance. They do not establish reliable OS background sync, encrypted device storage, native process-kill recovery or immunity to browser eviction. Do not clear browser storage or sign out until an unsynced draft is intentionally discarded or safely synced; logout clears private local data.

## Optional help / language / gated modules

Ask product help about physical receiving and show the cited version/section; optionally choose your own SKU/case source. An unsupported loan-policy/ETA question must abstain. Translation is a draft requiring source comparison and review. Speech is off by default; automated denial/noisy-transcript tests use mocks, not real language performance. P1 modules from Batch 8 are absent; P2 planning readiness shows explicit disabled/blocked prerequisites. Do not present previews as working forecasts, credit assessments or peer benchmarks.

## Submission / external acceptance still needed

Record the actual presentation/video after rehearsing. A public hosted HTTPS API, authorised Paytm/Sarvam contracts and measured provider evaluation, real messaging channel, real Android device and release signing are not supplied by this demo. Keep production identity, backup/retention/scanning/privacy and qualified legal review on the post-hackathon roadmap. No revenue uplift, fraud prevention, credit eligibility, production readiness or legal compliance is claimed.
