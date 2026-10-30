# Local repair report — 30 October 2026

## Reported issues and repairs

- Sarvam supplier translation: the local application had no configured API key. Configured the supplied credential in ignored `.env`, restarted the API, and verified live Hindi, Kannada and Telugu translation with synthetic text. Hindi/Kannada supplier-style messages retained numeric/reference tokens. No supplier messages were sent.
- Voice: `ENABLE_SPEECH_PREVIEW` was off. Enabled it locally as the user requested. Live `saaras:v3` returned the exact synthetic spoken sentence through both the adapter and authenticated `/api/assistant/speech` endpoint (HTTP 200). Audio was generated locally for this check; no personal recording was uploaded. Browser microphone permission, provider consent and transcript review remain required. Native Android voice is still disabled by the existing product gate.
- Purchase/stock UI: New purchase did not select the purchases tab when invoked from Stock or Expiry, hiding the editor. It now selects the correct tab and clears the previous source attachment/text. Switching purchase/stock/expiry tabs preserves the current in-memory purchase/receiving editor rather than silently clearing it. This is not a replacement for Save on device before closing/reloading.
- Windows source audit: explicitly reads UTF-8 source files, fixing a Unicode decoding crash.
- Windows browser test isolation: empty environment values could disappear in child processes, allowing dotenv to reload the real local provider key. A preserved whitespace sentinel and trimmed credential checks keep synthetic browser tests offline. An added backend test proves whitespace credentials cannot be sent.
- Windows export browser test: saves the actual download with Playwright saveAs before inspecting contents; remote browser connections do not expose download.path.

## Verification

- Full backend run: 245 passed, 1 skipped, existing Starlette/HTTPX deprecation warning. The skipped PostgreSQL restore rehearsal was subsequently rerun with the local PG_BIN and passed on its own generated database.
- Targeted AI suite plus restore rehearsal: 18 passed, including the added blank-key regression. No schema changes were needed.
- Frontend offline/exact-money suite: 18 passed.
- Production build, Ruff checks, Prettier and release source audit passed. Audit scanned 240 files with zero known-secret matches and zero SQLite imports. This is a source/bundle check, not a full security certification.
- Browser final run: all 24 journeys passed (3 commerce, 3 partner, 2 release, 1 polish, 15 extension/offline/workflow). Includes the added Stock/Expiry navigation regression, invoice/photo review, partial/full recovery, document downloads, offline retries, role/account clearing and responsive layouts.
- Final running application check: website HTTP 200, Sarvam configured true, speech preview true. Migration drift check: no new upgrade operations.

## Access and limits

Application: http://127.0.0.1:8000/. Refresh the app and accept Update when ready after saving any open work. Sarvam keys live only on the backend; the key is excluded from Git and this report. A fresh browser tab was used to verify the corrected purchase navigation.

Live checks establish current key/model access for these sample requests; no account balance or language accuracy benchmark was measured. Real microphone/noisy multilingual speech and physical Android need user/device testing. Paytm remains unconnected. Existing merchant records were preserved. The user subsequently authorised committing and pushing these repairs to origin/main; private configuration and generated files are excluded.
