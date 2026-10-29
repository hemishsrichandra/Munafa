# Scope refinement and next implementation plan

## Working prototype

The proposal's strongest scope is shortage-to-credit resolution for kirana merchants. This build prioritizes a complete loop over unrelated analytics or a broad chatbot:

- A specific delivery mismatch with merchant-confirmed evidence.
- An exact claim the merchant approves and can share.
- A promise that remains visibly open.
- A documented adjustment/refund that counts once.

The interface adds supplier balances, search, export and evidence snapshots to make this loop demonstrable and useful. Sarvam supplies optional invoice understanding and Indian-language communication.

## Before 31 October 2026

1. **Validate real Sarvam access.** Add the hackathon account key, test the configured model IDs, record latency and credit usage. If image access is unavailable, retain native Sarvam pasted-text extraction and translation. Never silently substitute synthetic output for a live call.
2. **Test five representative synthetic bills.** Include blurred units, discounts, tax-inclusive prices, multiple shortages and unreadable fields. Check that uncertain information requests review. Add new fixtures and regression cases for actual failures.
3. **Rehearse the ₹80 story.** Record a short walkthrough. Prepare a no-key fallback with explicit synthetic labeling.
4. **Produce final submission materials.** Record the demo video and update the presentation with real prototype screenshots, architecture and honest limitations. These artifacts have not been created by the initial prototype task.
5. **Talk to merchants if access allows.** Ask to review a recent short-delivery/credit case. Record actual frequency, pending value, how they track it and follow-up time. Avoid assuming every kirana has this problem.

## First merchant pilot

Target 3–5 consenting stores, one baseline week and four pilot weeks, as proposed in the deck. Before using real records, add the security and data-isolation foundations below.

Measure median preparation minutes against a comparable baseline, documented resolution rate, stores active in both final weeks, and applied credit plus received refund counted once. Keep promise amounts separate from verified recovery. Measure model requests, retries, processing time, hosting and support cost per active store.

Test the ₹199/month subscription hypothesis only after demonstrating recurring net benefit and asking about willingness to pay. Recovery is not guaranteed.

## Implementation priorities after the local build

| Priority | Work                                  | Completion criterion                                                                                                             |
| -------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Authentication and store isolation    | Two stores cannot read or mutate one another's cases, evidence or exports                                                        |
| P0       | PostgreSQL and private object storage | Schema migrations, ownership-scoped queries, tested backups and signed/authorized evidence access                                |
| P0       | Deployment protections                | HTTPS, request/body limits, CSRF/auth controls, rate limits, audit actor identity, upload decoding/scanning and retention policy |
| P0       | Live Sarvam evaluation                | Real account contract tests, timeout/retry policy, per-store budgets and a measured extraction evaluation set                    |
| P1       | Receiving quantities and pricing      | Decimal unit support, explicit conversions, tax/discount review and clear unsupported-case handling                              |
| P1       | Evidence-assisted credit matching     | Extract credit-document fields, surface candidate invoice matches, retain human confirmation and duplicate protections           |
| P1       | Multilingual receiving                | Sarvam speech input, Hindi/Hinglish/Kannada UX, field-by-field confirmation and accessible text fallback                         |
| P1       | Invoice lifecycle                     | Matched/no-claim archive state, draft deletion, safe invoice correction and structured conflict handling                         |
| P1       | Paytm integration discovery           | Confirm partner access, merchant consent and actual API contracts before implementation                                          |
| P2       | Multi-invoice credits and returns     | Explicit allocation ledger, idempotent events, no double recovery across cases                                                   |
| P2       | Messaging integration                 | Approved template/recipient flows, consent and verified delivery callbacks if API access is obtained                             |

## Deliberately outside the first build

Autonomous supplier messaging, credit underwriting, automatic tax/legal judgments, claimed Paytm data access, fully automated refund verification and broad price/scheme dispute detection. Expand scope only after merchant discovery and reliable evidence handling.
