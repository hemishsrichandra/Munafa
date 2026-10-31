"""Operator-only PostgreSQL backup/restore tooling. Never invoked by a merchant API.

No storage, credentials, paid plan or destructive restore target is provisioned.
Missing configuration is NOT_CONFIGURED, never a successful-backup claim.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


class BackupError(RuntimeError):
    pass


def pg_url(value):
    try:
        url = make_url(value)
    except Exception:
        raise BackupError("A valid PostgreSQL URL is required.") from None
    if url.drivername not in ("postgres", "postgresql", "postgresql+psycopg") or not url.database:
        raise BackupError("A PostgreSQL source/restore URL is required; no fallback exists.")
    if not url.host:
        raise BackupError(
            "Specify an explicit PostgreSQL host for matching snapshot/dump connections."
        )
    url = url.set(drivername="postgresql+psycopg")
    if url.host not in ("127.0.0.1", "localhost", "::1"):
        mode = url.query.get("sslmode", "require")
        if mode not in ("require", "verify-ca", "verify-full"):
            raise BackupError("Remote backup connections require PostgreSQL TLS.")
        url = url.update_query_dict({"sslmode": mode})
    return url


def schema_name(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,62}", value):
        raise BackupError("Invalid backup schema configuration.")
    return value


def fingerprint(url, schema):
    url = pg_url(str(url)) if isinstance(url, str) else url
    # Never persist a password, connection URL or raw host/database identifier.
    return hashlib.sha256(
        json.dumps([url.host, url.port or 5432, url.database, schema]).encode()
    ).hexdigest()


def binary(name):
    path = str(Path(os.environ["PG_BIN"]) / name) if os.getenv("PG_BIN") else shutil.which(name)
    if not path or not Path(path).is_file():
        raise BackupError("Supported PostgreSQL client binaries are required; configure PG_BIN.")
    return path


def pg_environment(url):
    env = dict(os.environ)
    env.update(
        PGHOST=url.host or "127.0.0.1",
        PGPORT=str(url.port or 5432),
        PGUSER=url.username or "",
        PGPASSWORD=url.password or "",
        PGDATABASE=url.database,
        PGCONNECT_TIMEOUT="15",
    )
    for key, target in (("sslmode", "PGSSLMODE"), ("sslrootcert", "PGSSLROOTCERT")):
        if key in url.query:
            env[target] = url.query[key]
    return env


def run(command, **kwargs):
    try:
        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
            **kwargs,
        )
    except (OSError, subprocess.SubprocessError):
        raise BackupError(
            "PostgreSQL tool failed. No verified backup/restore is claimed."
        ) from None


def run_dump(command, env, path, maximum):
    """Monitor the private output file and terminate only this worker's child on limits."""
    process = None
    try:
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=errors)
            start = time.monotonic()
            while process.poll() is None:
                if Path(path).stat().st_size > maximum or time.monotonic() - start > 600:
                    raise BackupError("Backup archive exceeded its size/time budget.")
                time.sleep(0.1)
            if process.returncode != 0:
                raise BackupError("PostgreSQL archive command failed; no backup is verified.")
    except OSError:
        raise BackupError("PostgreSQL archive command could not start.") from None
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_counts(db, schema):
    names = (
        db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname=:schema ORDER BY tablename"),
            {"schema": schema},
        )
        .scalars()
        .all()
    )
    quote = db.dialect.identifier_preparer.quote_identifier
    return {
        name: db.execute(text(f"SELECT count(*) FROM {quote(schema)}.{quote(name)}")).scalar_one()
        for name in names
    }


def table_checksums(db, schema):
    """Canonical UTC row JSON, streamed and SHA-256 hashed without logging raw rows."""
    names = (
        db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname=:schema ORDER BY tablename"),
            {"schema": schema},
        )
        .scalars()
        .all()
    )
    quote = db.dialect.identifier_preparer.quote_identifier
    db.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    result = {}
    for name in names:
        digest = hashlib.sha256()
        rows = db.execute(
            text(
                f"SELECT row_to_json(t)::text FROM {quote(schema)}.{quote(name)} t ORDER BY row_to_json(t)::text"
            ),
            execution_options={"stream_results": True},
        )
        for row in rows:
            digest.update(row[0].encode())
            digest.update(b"\n")
        result[name] = digest.hexdigest()
    return result


def archive_database(source_url, schema, path):
    """Count and dump from the same exported, read-only MVCC snapshot."""
    url, schema = pg_url(source_url), schema_name(schema)
    dump, restore = binary("pg_dump"), binary("pg_restore")
    version = run([dump, "--version"]).stdout.decode()
    match = re.search(r"(\d+)\.", version)
    if not match:
        raise BackupError("Unable to verify pg_dump version.")
    db_engine = create_engine(url, pool_pre_ping=True)
    try:
        with db_engine.connect().execution_options(isolation_level="REPEATABLE READ") as db:
            with db.begin():
                db.execute(text("SET TRANSACTION READ ONLY"))
                major = int(db.execute(text("SHOW server_version_num")).scalar_one()) // 10000
                if int(match[1]) < major:
                    raise BackupError("pg_dump is older than the PostgreSQL server.")
                snapshot = db.execute(text("SELECT pg_export_snapshot()")).scalar_one()
                counts = table_counts(db, schema)
                hashes = table_checksums(db, schema)
                if "alembic_version" not in counts or "stores" not in counts:
                    raise BackupError("Source is not a migrated Munafa application schema.")
                head = db.execute(
                    text(f'SELECT version_num FROM "{schema}".alembic_version')
                ).scalar_one()
                Path(path).touch(mode=0o600, exist_ok=False)
                maximum = int(os.getenv("BACKUP_MAX_BYTES", str(1024 * 1024 * 1024)))
                if not 1 <= maximum <= 5 * 1024 * 1024 * 1024:
                    raise BackupError(
                        "Configure a backup size budget within the single-object limit."
                    )
                run_dump(
                    [
                        dump,
                        "--format=custom",
                        "--no-owner",
                        "--no-acl",
                        "--schema",
                        schema,
                        "--snapshot",
                        snapshot,
                        "--file",
                        str(path),
                    ],
                    env=pg_environment(url),
                    path=path,
                    maximum=maximum,
                )
        size = Path(path).stat().st_size
        maximum = int(os.getenv("BACKUP_MAX_BYTES", str(1024 * 1024 * 1024)))
        if not 0 < size <= maximum:
            raise BackupError("Backup archive exceeds the configured size limit or is empty.")
        toc = run([restore, "--list", str(path)]).stdout
        if b"TABLE DATA" not in toc or b"alembic_version" not in toc:
            raise BackupError("Backup archive table-of-contents verification failed.")
        return {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_fingerprint": fingerprint(url, schema),
            "schema": schema,
            "migration_head": head,
            "server_major": major,
            "archive_sha256": sha256(path),
            "bytes": size,
            "table_counts": counts,
            "table_checksums": hashes,
            "archive_verified": True,
            "offhost_verified": False,
            "restore_rehearsed": False,
        }
    finally:
        db_engine.dispose()


@dataclass(frozen=True)
class Destination:
    bucket: str
    endpoint: str | None
    region: str
    encryption: str
    kms_key: str | None
    prefix: str = "munafa-backups"
    source_url: str = field(default="", repr=False)
    schema: str = "public"


def configuration():
    required = [
        "BACKUP_DATABASE_URL",
        "BACKUP_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
    ]
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        return None, missing
    endpoint = os.getenv("BACKUP_S3_ENDPOINT_URL") or None
    if endpoint and (urlparse(endpoint).scheme != "https" or not urlparse(endpoint).hostname):
        raise BackupError("Backup destination requires HTTPS.")
    encryption = os.getenv("BACKUP_S3_ENCRYPTION", "AES256")
    kms = os.getenv("BACKUP_S3_KMS_KEY_ID") or None
    if encryption not in ("AES256", "aws:kms") or (encryption == "aws:kms" and not kms):
        raise BackupError("Configure supported server-side encryption for private backups.")
    prefix = os.getenv("BACKUP_S3_PREFIX", "munafa-backups")
    if not re.fullmatch(r"[a-zA-Z0-9/_-]{1,100}", prefix) or ".." in prefix:
        raise BackupError("Invalid backup object prefix.")
    pg_url(os.environ["BACKUP_DATABASE_URL"])
    return Destination(
        os.environ["BACKUP_S3_BUCKET"],
        endpoint,
        os.environ["AWS_DEFAULT_REGION"],
        encryption,
        kms,
        prefix,
        os.environ["BACKUP_DATABASE_URL"],
        schema_name(os.getenv("BACKUP_SCHEMA", "public")),
    ), []


def s3_client(config):
    try:
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region,
            config=Config(connect_timeout=10, read_timeout=60, retries={"max_attempts": 2}),
        )
    except ImportError:
        raise BackupError(
            "Install the optional pinned requirements-ops.txt in the backup worker."
        ) from None


def upload_verified(client, config, archive, manifest):
    """Require public-access blocking, explicit SSE and a streamed read-back checksum."""
    try:
        block = client.get_public_access_block(Bucket=config.bucket)[
            "PublicAccessBlockConfiguration"
        ]
        if not all(
            block.get(key) is True
            for key in (
                "BlockPublicAcls",
                "IgnorePublicAcls",
                "BlockPublicPolicy",
                "RestrictPublicBuckets",
            )
        ):
            raise BackupError("Backup bucket public access is not fully blocked.")
        key = f"{config.prefix}/{datetime.now(timezone.utc):%Y-%m-%d}/{uuid.uuid4().hex}.dump"
        extra = {"ServerSideEncryption": config.encryption}
        if config.kms_key:
            extra["SSEKMSKeyId"] = config.kms_key
        with Path(archive).open("rb") as handle:
            response = client.put_object(
                Bucket=config.bucket,
                Key=key,
                Body=handle,
                ContentLength=manifest["bytes"],
                ContentType="application/octet-stream",
                Metadata={"sha256": manifest["archive_sha256"]},
                **extra,
            )
        if response.get("ServerSideEncryption") != config.encryption:
            raise BackupError("Storage encryption could not be verified.")
        body = client.get_object(Bucket=config.bucket, Key=key)["Body"]
        digest = hashlib.sha256()
        size = 0
        try:
            for chunk in iter(lambda: body.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
        finally:
            body.close()
        if digest.hexdigest() != manifest["archive_sha256"] or size != manifest["bytes"]:
            raise BackupError("Off-host backup checksum/size verification failed.")
        result = {**manifest, "object_key": key, "offhost_verified": True}
        receipt = client.put_object(
            Bucket=config.bucket,
            Key=key + ".manifest.json",
            Body=json.dumps(result, sort_keys=True).encode(),
            ContentType="application/json",
            **extra,
        )
        if receipt.get("ServerSideEncryption") != config.encryption:
            raise BackupError("Backup manifest encryption could not be verified.")
        return result
    except BackupError:
        raise
    except Exception:
        raise BackupError(
            "Private backup upload or verification failed; no success is claimed."
        ) from None


def backup(config, client=None):
    # Temporary plaintext archive is private to the worker and removed even on failure.
    with tempfile.TemporaryDirectory(prefix="munafa-backup-") as folder:
        os.chmod(folder, 0o700)
        archive = Path(folder) / "application.dump"
        manifest = archive_database(config.source_url, config.schema, archive)
        return upload_verified(client or s3_client(config), config, archive, manifest)


def restore_rehearsal(archive, manifest, admin_url):
    """Restore only into a generated scratch DB. Never accepts an existing target name."""
    archive, url = Path(archive), pg_url(admin_url)
    schema = schema_name(manifest["schema"])
    if not manifest.get("archive_verified") or sha256(archive) != manifest["archive_sha256"]:
        raise BackupError("Only a verified matching archive may be rehearsed.")
    name = "munafa_restore_" + uuid.uuid4().hex
    assert name != url.database and re.fullmatch(r"munafa_restore_[0-9a-f]{32}", name)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    created = False
    restored = None
    try:
        with admin.connect() as db:
            db.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        target = url.set(database=name)
        run(
            [
                binary("pg_restore"),
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname",
                name,
                str(archive),
            ],
            env=pg_environment(target),
        )
        restored = create_engine(target)
        with restored.connect() as db:
            if table_counts(db, schema) != manifest["table_counts"]:
                raise BackupError("Restored record counts do not match the exported snapshot.")
            head = db.execute(
                text(f'SELECT version_num FROM "{schema}".alembic_version')
            ).scalar_one()
            if head != manifest["migration_head"]:
                raise BackupError("Restored migration head differs from the source.")
            if (
                not manifest.get("table_checksums")
                or table_checksums(db, schema) != manifest["table_checksums"]
            ):
                raise BackupError("Restored row checksums differ from the source snapshot.")
        return {
            "restore_rehearsed": True,
            "table_counts_match": True,
            "row_checksums_match": True,
            "migration_head_matches": True,
            "existing_database_overwritten": False,
        }
    finally:
        if restored is not None:
            restored.dispose()
        if created:
            assert re.fullmatch(r"munafa_restore_[0-9a-f]{32}", name) and name != url.database
            with admin.connect() as db:
                db.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--restore-archive")
    parser.add_argument("--manifest")
    parser.add_argument("--confirm-isolated-restore", action="store_true")
    args = parser.parse_args()
    try:
        if args.restore_archive:
            if (
                not args.confirm_isolated_restore
                or not args.manifest
                or not os.getenv("RESTORE_TEST_ADMIN_URL")
            ):
                parser.error(
                    "Restore requires a manifest, separate RESTORE_TEST_ADMIN_URL and explicit --confirm-isolated-restore."
                )
            result = restore_rehearsal(
                args.restore_archive,
                json.loads(Path(args.manifest).read_text()),
                os.environ["RESTORE_TEST_ADMIN_URL"],
            )
            print(json.dumps(result))
            return 0
        config, missing = configuration()
        if args.check_config:
            print(
                json.dumps(
                    {
                        "status": "CONFIGURED" if config else "NOT_CONFIGURED",
                        "missing_variables": missing,
                        "backup_created": False,
                    }
                )
            )
            return 0
        if config is None:
            print(
                json.dumps(
                    {
                        "status": "NOT_CONFIGURED",
                        "missing_variables": missing,
                        "backup_created": False,
                    }
                )
            )
            return 3
        result = backup(config)
        if os.getenv("SECURITY_RETENTION_APPLY", "0") == "1":
            from .retention import apply_after_backup

            apply_after_backup(config, result)
        # Do not log source identifiers, credentials, PII, archive contents or table counts.
        print(
            json.dumps(
                {
                    "status": "VERIFIED_OFFHOST",
                    "archive_sha256": result["archive_sha256"],
                    "created_at": result["created_at"],
                    "restore_rehearsed": False,
                }
            )
        )
        return 0
    except Exception:
        # Operational boundary: SQL/SDK exceptions may contain private connection details.
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "backup_created": False,
                    "detail": "Backup/restore did not verify. Check private worker configuration and permissions; no successful backup is claimed.",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
