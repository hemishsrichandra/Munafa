# Merchant UI cleanup

30 October 2026. Owner request: remove build/implementation detail from merchant
screens and keep the existing product calm, clear and easy to use.

## Scope and changes

Frontend-only presentation work; no application database, migration, API contract,
permission, approval, inventory/financial service or provider setting changed.
No new packages, framework, state library or CSS replacement.

- `App.jsx`: removed hackathon badge and AI evaluation/promotional footer; shortened
  home/supplier/report copy, put Home first on desktop, show a useful saved/pending
  status and scroll to the top when navigating. More uses merchant task names.
  Replaced the developer P2 readiness destination with actual store reorder levels.
  Purchase export and Connections have separate focused screens. The old
  `Planning.jsx` module is no longer imported into the merchant app; backend gates
  remain tested and unchanged.
- `BusinessBrief.jsx`: compact heading/freshness, optional yesterday-payment
  disclosure, shorter settlement action with its full reason available on demand.
  Demo/stale labels remain visible. Payment details use readable component names,
  hide internal source IDs and show sample loading only to authorised demo owners.
  Existing demo settlements reload consistently in their isolated demo store.
- `Integrations.jsx`: merchant connection status for Paytm and manual WhatsApp
  handoff; no credentials, API packs, contract checklists, lender/device setup or
  developer BLOCKED codes. No new connection button promises a working live feed.
- `Intelligence.jsx`: product units, actual merchant reorder levels and movement
  links; no model/pilot/cohort flags, event-count diagnostics or fake forecasts.
  Missing history still clearly prevents a forecast; no peer comparison output.
- `Preparation.jsx`: readable bill/tax/date/amount review replaces raw proposal
  JSON. Exact server-side snapshot approval remains required. Period, included
  purchases, recorded tax, attached-bill counts, accountant-review warning, download
  recipient and expiry are shown before confirming. Nothing is submitted externally.
- `Commerce.jsx`, new `MoneyInput.jsx`, `api.js`: bill prices/totals are entered in
  rupees; API/offline payloads continue using integer paise. Decimal-string parsing
  never rounds extra precision or substitutes zero for invalid input. Signed
  rounding is explicit. Invalid/oversized values block form submission; stable
  accessible labels and described validation hints preserve keyboard/assistive use.
  Offline purchase fields use the same money boundary. Internal product IDs are
  retained but not presented as a field merchants must type.
- `Commerce.jsx`: removed raw extraction version/provider/coordinates/confidence
  diagnostics and stock actor/operation IDs. Kept review notes, original documents,
  physical-receiving confirmation and deterministic validation/approval flows.
- `Assistant.jsx`, `InvoiceIntake.jsx`, `LedgerViews.jsx`, `session.jsx`, `pwa.jsx`:
  removed API-key/environment instructions, provider build notes and pilot/pricing
  research. Kept optional AI/manual fallback, real source citations, external
  speech consent, review checks, permission denial and honest connection/install
  limitations. Disabled voice controls do not clutter the default view.
- `offline/Workspace.jsx`: plain-language saved/conflict/retry messages. Actual
  conflict counts remain visible. Developer outbox diagnostics now require both
  a development build and `?debug=1`; production diagnostics remain excluded.
- `styles.css`: small additions to the established design system for connection
  badges, compact brief summaries and invalid fields; existing phone navigation,
  touch targets, reduced-motion and focus styling retained.

Technical details remain in repository documentation and server audit snapshots,
not the default merchant screens. Synthetic labels, stale data, pending sync,
financial uncertainty, review/consent and permission errors are intentionally kept.

## Tests and evidence

- `frontend/tests/money.test.mjs`: existing exact-money checks plus rupee/paise
  round trips, cents, null/invalid/overflow rejection and negative rounding.
- `tests/e2e/polish.spec.js`: no build diagnostics in home/More; invalid precision
  rejected; ₹80.05 → 8005 paise, ₹200.12 → 20012 paise, −₹0.01 → −1 paise;
  responsive layouts and no page errors.
- Existing commerce/release tests now type rupees but keep the same integer-paise
  assertions and full purchase/receipt/claim/partial/full recovery behaviour.
- Existing preparation test reviews readable purchases and still verifies the
  downloaded snapshot, source ID, amount, demo mode and unreviewed status.
- P2 browser checks still assert all backend capabilities disabled, no proposal,
  no external action, no verified consent, no financial decision or peer statistics;
  the visible screen now tests reorder levels, insufficient history, own-source
  movement navigation, failed refresh and phone overflow.
- Offline conflict checks retain local count 9, accepted count 11 and server
  version 2 assertions; only the merchant-facing wording changed. No test disabled.
- Source-citation assertions now use human document titles and verify the same
  approved source URL. Locale and demo sign-in tests use the new plain-language copy.

Early runs exposed outdated copy selectors and a changing money-field accessible
name. Those were fixed. Adding the new browser journey also exhausted the existing
shared server's login budget; it now gets its own disposable server/schema group
in `scripts/browser-tests.cjs`. Authentication/rate limits were not weakened.
`scripts/serve_e2e.py` adds only a synthetic isolated polish-test account.

Final results: **246 backend / 23 browser / 18 frontend tests passed**, 0 skipped. The desktop More-entry refinement additionally passed the focused polish journey. Format, Ruff, Node syntax, production build and bounded release audit passed. Physical Android/OS install, live providers and real merchant usability timings remain untested. No claim that fewer words alone improves measured business outcomes.

## Reproduce

```sh
npm run build
npm run test:offline
npm run test:e2e
PG_BIN=/opt/homebrew/opt/postgresql@17/bin RELEASE_EVIDENCE_DIR=artifacts/test-evidence npm test
npm run format:check
.venv/bin/ruff check backend scripts/serve_e2e.py
node --check scripts/browser-tests.cjs
npx cap sync android
```

Use the existing Playwright executable setting on this Mac or install Chromium on
another machine. Run builds before backend collection/server startup. Tests use
disposable PostgreSQL namespaces, never reset merchant data. Android uses the same
React build. See the current handoff for JDK/SDK paths and `assembleDebug lintDebug`.

Rollback is code-only; no data migration is required. Rupee inputs are presentation
boundaries; existing saved drafts and server monetary values remain integer paise.
Historical batch reports describe the older UI; this note records the current
merchant-facing destinations and names.

## Final artefacts and limitations

- Existing licensed JDK/SDK command `assembleDebug lintDebug --no-daemon`: PASS. Signature verification: PASS with existing META-INF coverage warnings. Android lint: 0 errors, 0 fatal, 28 existing warnings. No physical device or emulator test.
- Debug APK `artifacts/munafa-debug.apk`: 4458530 bytes, SHA-256 `a362b4e8c3863a0e9bc84f33c8e086774b00c3d261619d28d7fe9e563cd59dd0`. All 13 public assets match the final frontend build byte-for-byte. No release signing; native sign-in still needs an authorised HTTPS backend.
- `scripts/audit_release.py`: 240 tracked/built files scanned, 0 configured-secret matches, 0 SQLite imports, 65 API operations. This is a bounded audit, not whole-history or penetration-test certification.
- Visually inspected phone/desktop screens. Local ignored screenshots: `artifacts/test-evidence/polished-synthetic-home.png`, `polished-synthetic-more.png`, `polished-home-phone.png`, `polished-more-phone.png`. Browser left on the populated synthetic home; temporary viewport override reset. Existing synthetic database records preserved, no seed/reset/import or external send in this UI task.
- Merchant record truth, provider availability, real OCR/language quality, consent/pilot and production readiness gates remain as recorded in FINAL-CHECKLIST-REVIEW.md. Simplifying the UI does not complete those integrations.
