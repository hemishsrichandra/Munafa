"""Declared retention and non-destructive planning; security cleanup follows verified backup.

Never removes business records, audit snapshots, outbox receipts or attachments.
"""

import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete, func, or_, text, create_engine
from . import models as m
from .backup import pg_url, schema_name, fingerprint, BackupError

POLICY = {
    "version": "retention-v1",
    "private_device_cache": "Minimal private cache expires; unsynced drafts are retained until explicit deletion/sign-out or browser eviction. No device encryption claim.",
    "sessions": "Server sessions expire after 12 hours. Optional maintenance removes expired session records only after another 30 days and a verified backup.",
    "recovery_codes": "Hashes only. Codes expire after 365 days; use/reset/rotation revokes them. Optional backed-up maintenance removes expired/used/revoked hashes after 30 days.",
    "business_evidence": "Financial, inventory, recovery and audit evidence is retained; no automatic deletion or destructive purge is enabled. Any lawful deletion/archival request needs reviewed policy, legal retention decisions and an approved backup plan.",
    "public_demos": "Private synthetic stores; sessions expire in 12 hours. Records remain retained and the total-store cap remains enforced. No silent demo reset or financial-history deletion.",
    "attachments": "Private PostgreSQL originals; no automatic attachment deletion. Do not use public demos for real documents.",
    "backups": "Proposed private backup lifecycle is 30 days; no storage/lifecycle policy is active until the owner configures and verifies a destination.",
    "provider_retention_verified": False,
    "cloud_ai": "Only explicitly submitted inputs are sent. Verify Sarvam workspace retention before real documents; local cleanup does not delete provider copies.",
}


def conditions(now):
    cutoff = now - timedelta(days=30)
    return {
        "sessions": (m.sessions, m.sessions.c.expires_at < cutoff),
        "recovery_codes": (
            m.recovery_codes,
            or_(
                m.recovery_codes.c.expires_at < cutoff,
                m.recovery_codes.c.used_at < cutoff,
                m.recovery_codes.c.revoked_at < cutoff,
            ),
        ),
    }


def plan(db, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "policy_version": POLICY["version"],
        "as_of": now.isoformat(),
        "dry_run": True,
        "eligible_security_rows": {
            name: db.execute(select(func.count()).select_from(table).where(where)).scalar_one()
            for name, (table, where) in conditions(now).items()
        },
        "business_records_to_delete": 0,
        "attachments_to_delete": 0,
        "audit_records_to_delete": 0,
    }


def apply_after_backup(config, manifest):
    # Internal worker call only; a user-supplied HTTP/file receipt cannot trigger cleanup.
    now = datetime.now(timezone.utc)
    created = datetime.fromisoformat(manifest.get("created_at", ""))
    url = pg_url(config.source_url)
    if (
        not manifest.get("archive_verified")
        or not manifest.get("offhost_verified")
        or manifest.get("source_fingerprint") != fingerprint(url, config.schema)
        or not timedelta(0) <= now - created <= timedelta(hours=24)
    ):
        raise BackupError("Retention maintenance requires a fresh verified backup of this source.")
    source = create_engine(
        url, connect_args={"options": f"-csearch_path={schema_name(config.schema)}"}
    )
    try:
        with source.begin() as db:
            report = plan(db, now)
            for _, (table, where) in conditions(now).items():
                db.execute(delete(table).where(where))
            return {**report, "dry_run": False, "backed_up_security_maintenance": True}
    finally:
        source.dispose()


def main():
    try:
        import os

        value = os.getenv("RETENTION_DATABASE_URL") or os.getenv("BACKUP_DATABASE_URL")
        if not value:
            print(
                json.dumps(
                    {
                        "status": "NOT_CONFIGURED",
                        "dry_run": True,
                        "missing_variables": ["RETENTION_DATABASE_URL"],
                    }
                )
            )
            return 3
        source = create_engine(
            pg_url(value),
            connect_args={
                "options": f"-csearch_path={schema_name(os.getenv('BACKUP_SCHEMA', 'public'))}"
            },
        )
        try:
            with source.connect() as db:
                db.execute(text("SET TRANSACTION READ ONLY"))
                print(json.dumps(plan(db)))
        finally:
            source.dispose()
        return 0
    except Exception:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "dry_run": True,
                    "detail": "Retention plan could not be verified. No data was removed.",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
