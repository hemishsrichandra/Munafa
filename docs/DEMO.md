# Hackathon demonstration and rehearsal

## Narrative

“Your supplier billed 12 packs. Only 10 arrived. The missing ₹80 is easy to calculate, but the promise to adjust it next time is easy to lose. Munafa keeps the bill, your count and the follow-up together until a credit is actually applied.”

Keep the distinction visible: synthetic examples demonstrate the workflow; live extraction requires your Sarvam credentials and review.

## Before recording

- Follow the README setup; open the UI and API `/docs`.
- Use a synthetic database. Stop the API and run the documented synthetic reset if A-104 already exists.
- Check the full workflow once. Do not reset during a recording or while another teammate is using the database.
- If using Sarvam, set the key in `.env`, restart, then verify both model access and translation with your actual account. Credit availability has not been checked by this build.
- Keep a no-key demonstration ready using the sample invoice and English message.
- Use the image in `samples/invoice-a104.png` for a real AI extraction attempt, or paste only the invoice portion of the text fixture. Do not include the receiving exercise in the pasted invoice.
- Present on a desktop viewport for a clear calculation, then briefly show the mobile layout.

## Suggested 3-minute recording

### 0:00–0:25 — The merchant's problem

Open Overview. Explain that all existing rows are synthetic. Point out the overdue supplier promise. “A promise is visible here, but it has not been counted as recovered money.”

### 0:25–1:15 — Read and confirm

Add A-104. Demonstrate sample intake, or an actual successful Sarvam image/text call if credentials are ready. Never describe fixture loading as a live AI call.

Enter these merchant-confirmed receiving values:

| Item     | Billed | Received | Billed and received unit | Effective price |
| -------- | -----: | -------: | ------------------------ | --------------: |
| Biscuits |     12 |       10 | pack                     |             ₹40 |
| Tea      |      6 |        6 | pack                     |            ₹125 |
| Soap     |     24 |       24 | piece                    |             ₹35 |

The soap unit is intentionally ambiguous. Confirm it on both sides and check the matching-unit box. Confirm complete delivery and effective prices, then save.

Point to the ₹80 calculation and the approval gate. “AI does not know what arrived. The merchant does. Rules calculate the amount only after those inputs are clear.”

### 1:15–1:50 — Prepare evidence

Approve the saved evidence. Download the PNG and preview the deterministic supplier message. If Sarvam is configured, choose Hindi or Kannada, wait for the actual API result, and compare the original. Check identifiers and amounts.

Explain that WhatsApp opens a draft and requires the merchant to attach the card and send. If staying entirely within the synthetic recording, say that the next sharing confirmation simulates the merchant sending it. Do not send a synthetic demand to a real supplier.

### 1:50–2:15 — Record the promise

Confirm the synthetic sharing step. Record “Adjust against next bill” and choose a follow-up date. Emphasize that the claim remains open and the verified amount has not increased.

### 2:15–2:50 — Verify and close

Open Verify credit/refund, load the synthetic next-bill credit and open its proof. Point to supplier, original invoice, reference and ₹80. Confirm application and record.

Show that the balance becomes zero, ₹80 appears once as verified recovery, and the event remains in the paper trail. Reload and open the case from Credit cases to demonstrate persistence.

### 2:50–3:00 — Paytm fit and next step

“Munafa is a focused business partner between supplier payments. The next step is validating this workflow with 3–5 merchants and exploring Paytm distribution with approved access.”

## Additional judge scenarios

- **Ambiguous unit:** leave soap unknown or select carton against piece. Save and show that approval remains blocked.
- **Partial credit:** after a fresh synthetic rehearsal, enter ₹30 in the amount field before loading the synthetic credit, then inspect the generated ₹30 proof and record it. The remaining balance is ₹50. Attach a distinct additional proof/reference for the remainder. A repeated proof or credit reference is blocked.
- **Edited count:** before recording any recovery, edit an approved case to 9 biscuit packs received. Save. Old approval is invalidated, and a fresh ₹120 claim needs reapproval. The old ₹80 approval snapshot remains accessible from the event history.
- **Provider failure:** a missing key leaves AI extraction disabled in the UI; a failed actual call surfaces an error and leaves manual entry available. No fabricated AI result appears.

## Submission checklist

The user requested the initial prototype; a final video and a revised presentation are separate deliverables still to prepare. Before the event submission:

- Record a clean demo video following the above flow.
- Update presentation screenshots to reflect the working prototype.
- Distinguish implemented behavior, mocked/synthetic paths and future integrations.
- Explain Sarvam model roles accurately; the image path is Sarvam-hosted Gemma, the text model is native Sarvam.
- Provide repository setup instructions, prototype access and the test results.
- Add actual merchant validation only after it has been conducted. Do not describe synthetic amounts as pilot outcomes.
