# Public authentication and Render handoff

31 October 2026. Scope: merchant signup and isolated public synthetic demo, retaining existing sessions, tenant rules and recovery safeguards. No migration, new dependency, SSO, OTP or email service.

## Entry points

- `POST /api/auth/signup`: username, password, store_name only. Creates a new non-demo merchant/store, owner membership and session atomically. It does not join any existing store or accept tenant/role fields. Usernames are trimmed, lowercased, 3–60 ASCII letters/digits/dot/underscore/hyphen; demo names reserved. Store name 1–120 characters without controls; password 12–200 characters, not all whitespace. Duplicate usernames return 409, including case variants of existing CLI identities. Concurrent registrations serialize with a PostgreSQL advisory lock; exact username uniqueness remains database-enforced. Retry after an uncertain response: sign in with the supplied credentials; do not create another account.
- `POST /api/auth/demo`: empty JSON object. Creates a different synthetic tenant and unpredictable, unavailable password for each visitor. Seeds only the existing A-104 invoice via existing domain rules. Received quantities stay unconfirmed; no stock or recovery is invented. Identity, session and sample seed share one PostgreSQL transaction. Failed seed rolls back everything. No shared demo username/password/code is exposed. Visitors can exercise existing merchant-reviewed workflows inside their own demo store. Only sample information belongs here.
- Existing `login`, `me`, `logout` routes unchanged in contract. Login tries an exact legacy username first, then a trimmed lowercase username. Existing 12-hour server sessions, scrypt hashes, HttpOnly production Secure/SameSite=Strict cookies, CSRF, store-derived tenancy and role checks remain. Logout revokes the current session and clears private browser data through the existing flow.
- Existing `/api/auth/dev-login` remains development/test only. Production still refuses startup with ALLOW_DEV_LOGIN=1. This is distinct from the new public demo.
- `/api/health` advertises `public_signup` and `public_demo`; the frontend shows enabled options only after loading it. A failed options request offers retry. Offline account creation/sign-in/demo are disabled, and existing offline workspace behaviour is preserved. Password confirmation is client-side only; the server independently validates the password.

## Render configuration

No additional secret/API key is required. The two new options default on when unset, so a normal backend + frontend rebuild exposes them.

| Variable               | Value / purpose                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| APP_ENV                | production                                                                                   |
| ALLOW_DEV_LOGIN        | 0                                                                                            |
| DEV_LOGIN_CODE         | unset/empty                                                                                  |
| APP_ORIGINS            | https://munafa-paytm-partner.onrender.com (add any actual custom frontend origin explicitly) |
| ENABLE_PUBLIC_SIGNUP   | 1 (0 disables)                                                                               |
| ENABLE_PUBLIC_DEMO     | 1 (0 disables)                                                                               |
| PUBLIC_DEMO_MAX_STORES | 500 by default; valid 1–10000                                                                |

Keep the existing private PostgreSQL DATABASE_URL and server-side provider keys. No database reset, seed-demo command, create-owner command or migration change is required for this release. Preserve the existing working Render build/start commands; frontend must rebuild with `npm run build` and backend restart to serve it. Same-origin browser deployment normally leaves VITE_API_BASE blank.

Render Settings must point to this repo's `main`, with Auto-Deploy On Commit or After CI Checks Pass. If linked via a public repo URL rather than a connected Git provider, Render requires manual deploy. If automatic deployment does not happen, use Manual Deploy → Deploy latest commit. Do not send a secret deploy hook in chat. Sources: [Render deploys](https://render.com/docs/deploys), [environment settings](https://render.com/docs/configure-environment-variables), checked 31 October 2026.

After deployment, `/api/health` must include public_signup:true and public_demo:true, development_login:false. Accept the PWA update or reload to pick up the new sign-in UI; do not clear local drafts merely to update. Health proves configuration, not successful signup/demo or provider performance.

## Required existing-owner password review

The newer Render commits previously auto-created an `owner` account on an empty database, with an OWNER_PASSWORD override and a fixed fallback in source. This release removes all automatic account provisioning at startup. It does not silently change existing credentials or delete accounts.

If your deployed database already has that account, rotate its password in Render's backend Shell after this deploy:

```sh
python -m backend.manage set-password --username owner
```

Enter and confirm a unique private password at the hidden prompts. Do not use a command-line password argument or paste the password in chat. This changes only that identity's password and revokes all its server sessions in the same transaction; store records remain intact. If the account does not exist, the command stops without changes. A new merchant can instead use Create account. OWNER_PASSWORD is no longer read; remove that unused variable if configured. No remote account password was inspected or changed during this release.

## Abuse controls and retention limits

- Public creation shares a 3 attempts/minute/IP/process budget; login and creation together retain the 10 attempts/minute/IP/process budget. Origin allowlist and 16 KiB authentication body limits also apply. Invalid attempts count. No client-supplied forwarding header is manually trusted by this code; proxy/IP behaviour depends on the deployed ASGI configuration.
- A PostgreSQL advisory lock and query enforce the **total** public-demo identity/store cap across workers/restarts. Default 500 is a capacity cap, not a sliding time window. At capacity, the UI displays a 429 explanation and account creation remains available. No operation deletes merchant data automatically.
- Demo sessions expire after 12 hours. Demo records are **not automatically deleted** on session expiry/logout and cannot be recovered by signing in with a shared demo credential. A new demo starts a new store. Retention/deletion automation is not implemented. Before public expansion, owner must decide retention, approve a backed-up cleanup process and evaluate storage/provider budget. Do not reset the database to make demo capacity available.
- Public signup has no email/phone verification, CAPTCHA or password recovery. The UI explicitly warns that recovery is unavailable. No verified business identity is claimed. Production-scale rollout needs a recovery/verification decision, reviewed consent/privacy/retention information, distributed/edge abuse controls and provider budget limits. Existing provider calls remain subject to existing permissions/rate limits; this release does not add a global AI-spend quota. Disable public demo/signup if the public beta cannot be monitored.
- Existing demo safeguards keep fixtures out of live merchant stores, but a demo visitor could type private data: labels are not encryption or consent. Do not enter real documents into the demo. No device-level encryption claim is made.

## Verification / continuation

Backend tests use generated disposable PostgreSQL schemas only. Phone browser tests cover signup/password mismatch/logout/relogin, four narrow widths, no-code demo and distinct visitor store isolation. Existing development-code workflow test now explicitly chooses Development demo access, preserving its original complete recovery journey.

Exact final commands/results and pushed revision are recorded in the implementation handoff below before release. No Android rebuild or real-device test is implied by a web-auth release. Unrelated locally deleted regulatory starter files are excluded from this commit.

## Final local verification

Final merged base: a00979f (all six newer GitHub/Render commits incorporated before release).

| Command                                                                                              | Result                                                                                                                                              |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.venv/bin/python -m pytest backend/tests -q`                                                        | 268 passed, including 21 public-auth cases; one existing Starlette/httpx deprecation warning                                                        |
| `npm run test:e2e` with PLAYWRIGHT_EXECUTABLE_PATH pointing to the installed Chromium headless shell | 26 passed across six isolated server groups; includes production build, signup/demo, 320/360/390/430 layouts, logout/offline sync and full recovery |
| `npm run test:offline`                                                                               | 18 passed                                                                                                                                           |
| `npm run format:check`                                                                               | Passed                                                                                                                                              |
| `.venv/bin/ruff check backend scripts`                                                               | Passed                                                                                                                                              |
| `.venv/bin/ruff format --check backend scripts`                                                      | 56 files passed                                                                                                                                     |
| `.venv/bin/python scripts/audit_release.py`                                                          | 247 files scanned, no private configuration matches, no SQLite imports, 67 API operations                                                           |
| `git diff --check` excluding unrelated starter deletions                                             | Passed                                                                                                                                              |
| `.venv/bin/python -m backend.manage --help`                                                          | Includes create-owner, set-password and seed-demo                                                                                                   |

An initial new signup browser test exposed helper text being included in the Username accessible name. The helper now uses aria-describedby outside the label; the test passed without weakening its exact-label assertion. Earlier runs on the pre-Render-merge base are superseded by the results above.

Local evidence: ignored `artifacts/test-evidence/signup-phone.png` and `public-demo-phone.png`. No actual Android device, new APK or local Docker-image build was run for this web-auth change. No live provider calls were needed. Remote deployment must be verified by its public health flags after the push; no existing remote merchant account/password was accessed during local testing.
