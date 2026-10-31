# One-time account recovery and public-demo AI controls

31 October 2026. The owner chose **recovery codes now; email later**. No email/SMS/OTP service or new paid API was added. Migration **f237b2e9c014** adds hashed recovery credentials, an explicit users.provider_access approval flag, and public-demo service usage counters/events; it is additive from 19b0c9cc7712. Docker's existing Alembic startup applies forward migrations. Do not downgrade populated schemas/reset/import records to roll back application code.

## Merchant workflow

More → Account recovery: re-enter the current password and create eight high-entropy recovery codes. Replacing a set requires explicit UI confirmation, reauthentication and CSRF. The codes are shown once; download a private browser copy or select/save them separately from the device. “I saved these codes” removes them from view. The app never saves codes in IndexedDB, service-worker/API caches, audit metadata or operation receipts. Native file export of recovery secrets is deliberately not enabled; there is no reviewed device secure-export claim.

Sign-in → Recover account: username + one unused saved code + new password/confirmation. Codes expire after one year. Reset consumes the code atomically, revokes the entire remaining set and all server sessions, and returns to sign-in; it does not automatically log the user in. Sign in with the new password and enrol fresh codes. If no code was saved, use the trusted administrator CLI process; there is no public email recovery or identity bypass.

Only SHA-256 hashes of random 128-bit codes are stored. Passwords remain scrypt-hashed and now preserve exact leading/trailing spaces at HTTP input, matching CLI provisioning. Usernames alone are normalised. Own-account code setup is available to viewer/staff/owner roles without granting ledger-write permission. Logout also works for viewers. Public demo accounts cannot enrol/recover. No tenant/user ID is accepted in issuance bodies; own identity comes from the verified session. Reset failures are generic for wrong, unknown, used, revoked and expired credentials. Sensitive public endpoints retain origin/body/IP rate limits. Recovery is a credential, not proof of business identity.

CLI password rotation also revokes codes and sessions. Account/user locks serialise login/reset/rotation. Store audit records include actor/action identifiers but no password/code/raw request. Codes are never sent by email/message. Review [OWASP recovery guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html); the offline-code method remains only as secure as the private copies the merchant retains. No MFA, verified email or security certification is claimed.

## Explicit shared-provider approval

Public signup does not prove the account is trusted to spend the application's Sarvam credits. New public-signup accounts and existing accounts migrated without provenance default to provider_access=false. Manual workflows/recovery remain available. Trusted CLI provisioning sets approval; a database operator can enable or revoke an exact account with:

```sh
python -m backend.manage allow-ai --username YOUR_EXACT_USERNAME
python -m backend.manage deny-ai --username YOUR_EXACT_USERNAME
```

The CLI requires ALLOW/DENY confirmation. This is not a public HTTP operation or a privilege a merchant owner can grant themselves. On free Render, run the command from a trusted local checkout with the privately configured external PostgreSQL URL, as with password rotation. Do not paste that URL in chat/history. After migration, an existing real account needs explicit approval before cloud extraction/translation/speech; do not automatically approve all existing users. Signed-in capability responses/UI reflect the gate. Public demo identities remain controlled by their separate global quota configuration and cannot be granted this bypass.

## Public demo provider usage / cost

**PUBLIC_DEMO_AI_ENABLED=0 by default**, including the Render blueprint. Server-side provider boundaries enforce this even when SARVAM_API_KEY is configured: vision/text extraction, translation and speech cannot contact paid providers for public-demo identities. Manual intake, deterministic help and all reviewed synthetic workflows remain. Trusted merchant/development fixture accounts are distinct from public demo identities; do not expose administrator provisioning as a public bypass.

If an operator intentionally enables paid public-demo AI, all four settings must be positive and bounded:

- PUBLIC_DEMO_AI_REQUEST_RESERVE_PAISE: conservative configured reservation per provider request.
- PUBLIC_DEMO_AI_DAILY_RESERVE_LIMIT_PAISE: global and per-store UTC-day reservation ceiling.
- PUBLIC_DEMO_AI_GLOBAL_DAILY_CALLS and PUBLIC_DEMO_AI_STORE_DAILY_CALLS: call ceilings.

An independent PostgreSQL transaction locks global then store counters and appends an immutable reservation event before any network call. Failed downstream requests do not erase reservations; crossing either cap rejects before a provider call. Multiple workers share the same limit; changing process memory/restarting does not reset it. Translation chunks count as individual requests. Missing/invalid configuration denies use. Actual provider charges are not known from a reservation: **these are operator budget controls, not reconciled billing or a guaranteed monetary cap when a reservation underestimates vendor charges**. Keep paid public-demo AI off until account-level provider budgets/prices/max request sizes are reviewed. Default off is the hard zero-paid-call protection.

Rebuildable counter basis is service_usage_events grouped by UTC window globally and by store (sum reserved_paise/count). Do not reset counters to bypass a budget or delete immutable events. Backend-only counters have no merchant-facing cross-store API. Existing per-IP/in-process sensitive-endpoint limits remain; these are not a distributed WAF.

## Verification / rollout

PostgreSQL tests cover hash-only storage, rotation, expiry, generic rejection, wrong user, replay, concurrent reset, old-session denial, exact password spaces, CLI invalidation, viewer own-account/logout, tenant spoof rejection, paid-call denial, concurrent quota reservation and event immutability. Browser tests cover private code display/clear, no IndexedDB leakage, reset/sign-in and old-session rejection. Initial direct multi-file tests hit the intended sensitive-IP budget; the normal per-spec isolated-server runner passed without weakening production limits.

No new Render secret is required for code recovery or default-off public AI. Apply forward migration/start backend normally. Set up codes while the password is known. Backups/storage and real-provider billing controls remain separate operational gates; see ../ops/BACKUP-RECOVERY.md and IMPROVEMENTS-HANDOFF.md for current results/remaining work.
