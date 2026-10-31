# Private backups, restore and retention operations

31 October 2026. **NOT CONFIGURED: the owner has no backup destination or paid Render backup plan. No real off-host backup has been created.** Software tests use synthetic disposable PostgreSQL databases and storage fixtures. No storage account, paid resource, email service or other paid API is provisioned by this release. Sarvam is the only authorised paid AI provider.

## What is implemented

`python -m backend.backup` uses a read-only exported PostgreSQL snapshot shared by row counts, canonical UTC row SHA-256 checksums and `pg_dump --snapshot --format=custom`. It checks compatible client/server major versions, size/time limits and archive contents. The archive has a private temporary directory and is removed on success/failure. The temporary plaintext archive is **not encrypted on the worker disk**; protect the worker/host. Production remote database connections require TLS; credentials are passed to child tools in environment variables, never command arguments or logs.

The optional pinned boto3 SDK lives in `backend/requirements-ops.txt` and dev requirements, not the application runtime requirements. Install it in the backup worker. The worker uses an existing owner-configured S3-compatible HTTPS destination, requires all four bucket PublicAccessBlock settings, requests SSE AES256 by default and verifies the storage response. It streams the uploaded archive back to verify exact byte size and SHA-256, then stores an encrypted private manifest. A backend-compatible provider must support these APIs; unsupported contracts fail closed. No claim is made that every free S3-compatible tier implements them. Check actual private-access/encryption controls, quotas and storage/egress costs before enabling. No destination has been tested live.

The manifest contains source fingerprint (not URL/credentials), schema/migration head, table counts and hashes, archive size/hash and verification flags. It is private backup metadata, not a public report. Database dumps include documents, PII and password/recovery hashes; never place them in Git, a public bucket, CI artifact upload or shared chat. Normal application artifacts are ignored; keep operator files in private ignored artifacts or approved private storage.

## Configure existing private storage

Do not paste credentials into chat or `.env.example`. Supply secret values to an isolated worker or GitHub repository secrets:

| Worker environment       | GitHub secret/variable                                                     |
| ------------------------ | -------------------------------------------------------------------------- |
| BACKUP_DATABASE_URL      | Secret BACKUP_DATABASE_URL (this app's external PostgreSQL URL)            |
| BACKUP_S3_BUCKET         | Secret BACKUP_S3_BUCKET                                                    |
| AWS_ACCESS_KEY_ID        | Secret BACKUP_AWS_ACCESS_KEY_ID                                            |
| AWS_SECRET_ACCESS_KEY    | Secret BACKUP_AWS_SECRET_ACCESS_KEY                                        |
| AWS_DEFAULT_REGION       | Variable BACKUP_AWS_REGION                                                 |
| BACKUP_S3_ENDPOINT_URL   | Optional variable BACKUP_S3_ENDPOINT_URL, HTTPS only                       |
| BACKUP_SCHEMA            | public for the current Render deployment                                   |
| PG_BIN                   | Supported client directory; CI worker uses /usr/lib/postgresql/17/bin      |
| BACKUP_S3_PREFIX         | munafa-backups by default                                                  |
| BACKUP_MAX_BYTES         | 1 GiB default; single-object worker rejects configured budgets above 5 GiB |
| SECURITY_RETENTION_APPLY | 0 by default; do not enable without reviewing the policy below             |

Use a least-privilege credential scoped to the backup prefix: public-access-block inspection, put/get objects and required encryption permissions. The worker needs no bucket creation, public ACL, lifecycle mutation or object-deletion permission. Default AES256 avoids adding a separate KMS service. Optional existing KMS configuration requires its own reviewed permissions/cost decision; none is enabled here. Do not assume a free tier remains free beyond quotas.

```sh
python -m pip install -r backend/requirements.lock.txt -r backend/requirements-ops.txt
python -m backend.backup --check-config
```

CONFIGURED means required environment fields validate, not that the database/bucket/network has been verified. Missing secrets report NOT_CONFIGURED and no backup. An actual backup run returns success only after archive/readback verification. Failed upload may leave an unverified private object; there is no automatic destructive deletion. Failure messages redact driver/SDK details.

`.github/workflows/backups.yml` schedules the job daily at 20:25 UTC (01:55 IST next day) and supports manual dispatch. When secrets are absent, the configuration job warns and the backup job is skipped. A green **configuration check is not a green backup**. The workflow never uploads database files to GitHub artifacts. GitHub account/action quotas still apply. No paid infrastructure purchase is authorised or necessary to commit the configuration template.

After configuring, operator acceptance is: inspect Actions log for VERIFIED_OFFHOST, inspect the private manifest, download/rehearse a trusted archive and establish monitoring for missing/failed nightly backups. Agree an RPO/RTO based on measured rehearsal results; none is claimed yet. A daily logical backup is not continuous recovery/PITR.

## Restore rehearsal and actual incident procedure

Only restore trusted archives; pg_restore executes SQL from the archive. Download the matching archive and manifest from the private destination using authorised storage tooling/console. Do not put a connection URL on the command line. Privately configure RESTORE_TEST_ADMIN_URL for a scratch-capable PostgreSQL service; the role must create/drop a **new generated database**. Never point application traffic at it automatically.

```sh
python -m backend.backup --restore-archive artifacts/private/application.dump \
  --manifest artifacts/private/application.dump.manifest.json --confirm-isolated-restore
```

The command cannot take an existing target database name. It generates `munafa_restore_<uuid>`, verifies archive hash, restores with no original ownership/ACL, compares migration head, every table count and every canonical row hash, and drops only its own generated database afterward. Existing source/application databases are never overwritten. Role grants/global PostgreSQL configuration and external object/provider systems are not restored by pg_dump.

**Actual recovery:** preserve the original database and incident evidence, verify the latest private backup/time, restore into a separate retained recovery instance under an explicitly reviewed plan, validate counts/hashes/ledger replay/attachments/tenant checks and account controls, and only then approve application cutover. Changing live DATABASE_URL, importing real data, dropping/resetting an existing database or downgrading populated financial schemas requires verified backup and explicit owner approval. This rehearsal command deliberately does not perform live cutover.

Render's [backup documentation](https://render.com/docs/postgresql-backups) says managed recovery is provided for paid PostgreSQL plans and unavailable on Free. The deployed plan has not been inspected. Upgrading/provisioning a paid plan is an owner decision, not performed here.

## Retention policy and safe maintenance

`GET /api/auth/privacy` exposes the versioned plain-language policy to signed-in users. Account → How your data is kept displays the relevant portions. This documents behaviour; it is not legal certification or a reviewed statutory retention schedule.

- Sessions expire in 12 hours; expired session rows become eligible for maintenance after another 30 days.
- Recovery-code hashes expire in 365 days, and reset/rotation revokes codes. Used/revoked/expired hashes become eligible after 30 days. Raw codes are never stored in PostgreSQL or browser offline storage.
- Financial/inventory/recovery history, audit events, operation receipts and original attachments are **not automatically deleted**. Audit/immutability triggers stay enabled. Agree legal retention, deletion-request handling and archival with qualified reviewers before adding deletion mechanisms.
- Public demo sessions expire but their synthetic records are retained. The total demo-store cap remains to bound growth. No unapproved financial purge or silent reset is introduced.
- Unsynced device drafts remain until explicit delete/sign-out or browser eviction. Logout warns before clearing private data. No device-encryption claim.
- Provider retention is separate: confirm actual Sarvam workspace/product settings before real invoices/audio; local cleanup cannot establish provider deletion.
- `ops/s3-backup-lifecycle.example.json` is a **30-day proposal only**. Applying it deletes old versions/objects and needs an owner-reviewed backup/retention decision. No lifecycle API is called by this app/worker.

For a read-only security-retention plan, privately set RETENTION_DATABASE_URL (or BACKUP_DATABASE_URL) and BACKUP_SCHEMA, then:

```sh
python -m backend.retention
```

No apply flag is exposed on that planning command. Optional expired-security maintenance is invoked only by the backup worker when SECURITY_RETENTION_APPLY=1 **after the same run has verified a fresh off-host backup** of the same source/schema. It removes only eligible session/recovery-hash rows in one transaction; financial/audit/attachment records remain. This switch is disabled in the supplied workflow. Review the dry-run, approve the policy and actual destination, and enable deliberately; it has not been executed on production.

## Validation evidence and limitations

Real pg_dump/pg_restore checks run only against generated synthetic schemas/scratch databases; row counts and content hashes match. SDK Stubber/in-memory fixtures test private-policy checks, SSE parameters, readback tampering, failure redaction and that failed backup cannot trigger cleanup. These are not live-bucket tests. Current configuration commands return NOT_CONFIGURED. No successful production backup, recovery point, restore time, deployment retention execution or legal review is claimed.

Official references checked 31 October 2026: [PostgreSQL pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html), [S3 security controls](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html), [boto3 PublicAccessBlock](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_public_access_block.html). Actual storage contracts/regions/pricing must be verified for the chosen existing destination before activation.
