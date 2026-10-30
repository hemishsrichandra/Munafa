# Regulatory Workspace — reusable foundation

A separate, runnable application starter extracted from the owner's Munafa project.
**This is not the regulatory product and not a completed Forge submission.** It has
no hardcoded legal answers, regulatory documents, fake alerts, model calls or sample
business records. The UI explicitly reports that no sources are connected.

Read **MASTER-PROMPT.md** for the complete proposed build, **REUSE-MANIFEST.json** for
provenance, and **VERIFICATION.md** for actual checks. All extraction/glue in this
package is inherited pre-event work. Preserve that disclosure and clarify the event's
boilerplate/reuse interpretation before relying on it for submission eligibility.
Ownership of the source does not change the event's timing rules.

## Contents

| Path                                                  | Status                                                                                                |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `backend/auth.py`, `security.py`, `db.py`, `store.py` | Adapted working identity/session/CSRF/tenant/request-idempotency foundation                           |
| `backend/models.py`, `migrations/`                    | Six identity/session/idempotency tables; fresh migration history; no Munafa commerce schema           |
| `backend/app.py`, `manage.py`                         | New packaging glue, health/login/me/logout and explicit CLI account provisioning                      |
| `frontend/src/`                                       | Neutral React/Vite responsive shell, bounded API client and extracted accessible modal                |
| `frontend/public/sw.js`, manifest and mark            | Adapted static-shell PWA foundation, distinct cache prefix/identity; new neutral SVG mark             |
| `reference/`                                          | Inert text copies of approval/AI/IndexedDB/PWA patterns, **not wired capabilities**                   |
| `backend/tests/`, `scripts/`                          | Isolated PostgreSQL checks and build/run helpers                                                      |
| `MASTER-PROMPT.md`                                    | Complete next-project context, event gates, architecture, phases, evaluation and handoff instructions |

**Not included:** credentials, `.env`, databases, uploads, real merchant data, `.git`,
node_modules, virtualenvs, APK/signing material, invoice/settlement fixtures, Munafa
screens/business domains, regulatory engine, provider keys or deployment accounts.
No source project licence file was present at extraction; this is an owner's private
reuse package, not a new third-party open-source grant. Choose a project licence
explicitly before public distribution and retain dependency licences.

## Start outside Munafa

Copy **this folder's contents** into a new independent project directory. Open that
directory as your editor/coding-agent workspace. Do not initialise a nested Git repo
inside Munafa or point this app at Munafa's database. The parent repo only transports
this package; no new GitHub repository has been created for you.

```sh
# Run from your NEW project root after copying the folder.
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm ci
cp .env.example .env
```

Windows: use `.venv\Scripts\python.exe` and normal Windows copy syntax. `scripts/python.cjs`
selects the platform virtualenv for npm commands. Python 3.13 / Node 20 were used for
local verification; use a supported PostgreSQL release and locked dependencies.

Create **new empty PostgreSQL databases** `regpulse` and `regpulse_test` with your
normal local/admin process. Configure their actual private URLs in this folder's
ignored `.env`; the sample URL is intentionally unusable. No database credentials
or automated database reset are shipped. App/test roles should use least privilege;
test fixtures require permission to create/drop only their generated test schemas.
Never use a production database for tests.

```sh
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.manage create-owner
npm run dev
```

Choose your own username, business name and password (12+ characters). No public demo
login code or auto-seed exists. Open **http://127.0.0.1:5180/**. API: port **8010**.
Munafa remains on 5173/8000. Session/CSRF cookies use `rp_`, not `pbp_`; browser data
and cached shell never intentionally use Munafa's names. No profile/offline private
store is implemented; `reference/` shows patterns to adapt with a new IndexedDB name.

The backend environment loader reads only this starter root's `.env`, not a sibling
or parent `.env`. Already-exported shell variables still take precedence; check
DATABASE_URL/TEST_DATABASE_URL locally before migrating. Never print secrets to chat.
`APP_ENV=production` requires HTTPS (secure cookies); development should stay loopback.
The app checks the Alembic head before startup, never create_all/seeds/migrates itself.

## Verify

```sh
npm run build
npm test
npm run test:e2e
.venv/bin/alembic check
.venv/bin/ruff check backend
```

Build before backend collection/server startup. Tests use a fresh `starter_test_…`
PostgreSQL schema, migrate it, create synthetic **test-only accounts**, then remove
only that generated schema. There are no regulatory mock datasets. No runtime/test
SQLite fallback is allowed. Install Playwright Chromium if needed for `npm run test:e2e`. The browser runner uses its own disposable schema and local port 8011. The tests establish foundation behaviour, not regulatory
correctness, production readiness or external provider access.

For a production-bundle preview, build then use `npm start`; open localhost:8010.
Vite development does not register the service worker. The production shell registers
it; the first cache warm-up needs connectivity. Static shell can launch offline,
but session verification/records need a connection and no cached legal answer exists.
Manifest uses a neutral SVG; add verified project-owned PNG/maskable icons and test
actual OS installation before claiming broad installability. No APK is included.

## Database changes and rollback

`foundation_0001` contains only merchants, stores, users, memberships, sessions and
idempotency_operations. Internal `store_id` means scoped business workspace. Future
regulatory tables require new migrations. No old Munafa migration should be copied.

Downgrading this initial migration drops these tables: **never do so on populated
records without a verified backup, concrete plan and owner approval**. For a scratch
migration test use only its newly generated disposable schema. Production backup:
use matching-version `pg_dump` to a private restricted destination; verify the archive
and restore into a newly created scratch database, compare record counts/constraints,
and rehearse before cutover. No backup/import/reset is performed by this package.

## Reference integration cautions

- Approval reference depends on Munafa domain services and audit models; do not copy
  its action dispatch into a legal engine. New action types need source/profile
  version binding, digest/expiry and reviewed server execution.
- Provider reference is invoice-oriented, account/model access unverified; create
  new regulatory schemas/prompts/adapters during the event and verify official docs.
- Offline references are not enabled. Rename database/cache scopes, define retention,
  clear private data on account switch and test conflicts before integrating.
- Existing middleware has process-local rate limits and a bounded buffered JSON
  response/idempotency path. Do not put large PDFs, streaming jobs or public webhooks
  through it without a deliberate architecture/security review. Source downloads
  need a separate safe bounded path. No whole deployment/security certification.
- No source crawler, SSRF defence, legal PDF parser/OCR, embeddings, scheduler,
  legal-review queue, audit-event table, approval service or AI telemetry is wired.

## New repository and next build

After copying outside Munafa, review the package, choose a product name/licence and
use a new GitHub repository. Preserve REUSE-MANIFEST.json and README attribution;
commit the foundation separately from event-built logic. Do not copy Munafa's `.git`
or misrepresent the inherited commit dates. Copy MASTER-PROMPT.md's START→END block
into the new chat and provide event timing, reuse clarification, selected state,
provider choice and deployment destination. No secrets in the prompt.
