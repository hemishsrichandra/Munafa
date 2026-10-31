"""Real PostgreSQL archive/restore, private-destination contract and retention guards."""

import io
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, update, func
from backend import backup, retention, models as m
from backend.db import engine
from backend.tests.test_workflow import shared


class PrivateStorage:
    """In-memory transport fixture, never a real bucket or encryption claim."""

    def __init__(self, public=False, corrupt=False):
        self.objects = {}
        self.public = public
        self.corrupt = corrupt

    def get_public_access_block(self, **kw):
        return {
            "PublicAccessBlockConfiguration": {
                k: not self.public
                for k in (
                    "BlockPublicAcls",
                    "IgnorePublicAcls",
                    "BlockPublicPolicy",
                    "RestrictPublicBuckets",
                )
            }
        }

    def put_object(self, **kw):
        assert kw["ServerSideEncryption"] == "AES256"
        assert "ACL" not in kw
        body = kw["Body"]
        self.objects[kw["Key"]] = body.read() if hasattr(body, "read") else body
        return {"ServerSideEncryption": "AES256"}

    def get_object(self, **kw):
        return {"Body": io.BytesIO(b"corrupted" if self.corrupt else self.objects[kw["Key"]])}


def destination(schema):
    return backup.Destination(
        "synthetic-private-test-bucket",
        None,
        "ap-south-1",
        "AES256",
        None,
        source_url=os.environ["TEST_DATABASE_URL"],
        schema=schema,
    )


def test_unconfigured_backup_never_connects_or_claims_success(monkeypatch, capsys):
    for key in (
        "BACKUP_DATABASE_URL",
        "BACKUP_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("sys.argv", ["backup", "--check-config"])
    monkeypatch.setattr(backup, "s3_client", lambda *a: pytest.fail("No configured destination"))
    assert backup.main() == 0
    status = json.loads(capsys.readouterr().out)
    assert status["status"] == "NOT_CONFIGURED" and status["backup_created"] is False
    monkeypatch.setattr("sys.argv", ["backup"])
    assert backup.main() == 3
    assert json.loads(capsys.readouterr().out)["backup_created"] is False


def test_real_pg_snapshot_archive_restore_and_encrypted_upload_contract(client, database, tmp_path):
    c = shared(client)
    config = destination(database)
    archive = tmp_path / "synthetic.dump"
    manifest = backup.archive_database(config.source_url, database, archive)
    assert manifest["archive_verified"] is True and not manifest["offhost_verified"]
    assert manifest["table_counts"]["cases"] == 1
    assert manifest["migration_head"] == "a1b2c3d4e5f6"
    assert not manifest["restore_rehearsed"]
    restored = backup.restore_rehearsal(archive, manifest, config.source_url)
    assert restored["restore_rehearsed"] and restored["existing_database_overwritten"] is False
    storage = PrivateStorage()
    uploaded = backup.upload_verified(storage, config, archive, manifest)
    assert uploaded["offhost_verified"] is True
    assert len(storage.objects) == 2
    assert uploaded["archive_sha256"] == backup.sha256(archive)
    with engine().connect() as db:
        assert db.execute(select(m.cases.c.id)).scalar_one() == c["id"]
    with pytest.raises(backup.BackupError):
        backup.restore_rehearsal(
            archive, {**manifest, "archive_sha256": "0" * 64}, config.source_url
        )


def test_private_policy_and_checksum_fail_closed(tmp_path):
    path = tmp_path / "synthetic.dump"
    path.write_bytes(b"SYNTHETIC ARCHIVE TRANSPORT TEST")
    config = backup.Destination("synthetic-bucket", None, "ap-south-1", "AES256", None)
    manifest = {"bytes": path.stat().st_size, "archive_sha256": backup.sha256(path)}
    public = PrivateStorage(public=True)
    with pytest.raises(backup.BackupError):
        backup.upload_verified(public, config, path, manifest)
    assert public.objects == {}
    with pytest.raises(backup.BackupError):
        backup.upload_verified(PrivateStorage(corrupt=True), config, path, manifest)


def test_retention_plan_is_read_only_and_apply_requires_matching_verified_backup(client, database):
    shared(client)
    now = datetime.now(timezone.utc)
    with engine().begin() as db:
        db.execute(update(m.sessions).values(expires_at=now - timedelta(days=31)))
        before = db.execute(select(func.count()).select_from(m.sessions)).scalar_one()
        plan = retention.plan(db, now)
        assert plan["dry_run"] and plan["eligible_security_rows"]["sessions"] == before
        assert plan["business_records_to_delete"] == plan["audit_records_to_delete"] == 0
        assert db.execute(select(func.count()).select_from(m.sessions)).scalar_one() == before
    config = destination(database)
    bad = {
        "created_at": now.isoformat(),
        "source_fingerprint": "wrong",
        "archive_verified": True,
        "offhost_verified": True,
    }
    with pytest.raises(backup.BackupError):
        retention.apply_after_backup(config, bad)
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.sessions)).scalar_one() == before
    # Synthetic-only function-level fixture represents a verified same-source receipt.
    receipt = {
        **bad,
        "source_fingerprint": backup.fingerprint(backup.pg_url(config.source_url), database),
    }
    result = retention.apply_after_backup(config, receipt)
    assert result["dry_run"] is False
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.sessions)).scalar_one() == 0
        assert db.execute(select(func.count()).select_from(m.cases)).scalar_one() == 1
        assert db.execute(select(func.count()).select_from(m.audit_events)).scalar_one() > 0


def test_source_schema_and_destination_validation(monkeypatch):
    for value in ("sqlite:///no.db", "mysql://user@host/db", ""):
        with pytest.raises(Exception):
            backup.pg_url(value)
    with pytest.raises(backup.BackupError):
        backup.schema_name("public;DROP DATABASE example")
    for key, value in {
        "BACKUP_DATABASE_URL": "postgresql://synthetic:private-test-password@localhost/example",
        "BACKUP_S3_BUCKET": "synthetic",
        "AWS_ACCESS_KEY_ID": "synthetic",
        "AWS_SECRET_ACCESS_KEY": "synthetic",
        "AWS_DEFAULT_REGION": "ap-south-1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("BACKUP_S3_ENDPOINT_URL", "http://insecure.example")
    with pytest.raises(backup.BackupError):
        backup.configuration()
    monkeypatch.setenv("BACKUP_S3_ENDPOINT_URL", "https://storage.example")
    config, missing = backup.configuration()
    assert not missing and config.encryption == "AES256"
    assert "private-test-password" not in repr(config)
    assert replace(config, schema="public").schema == "public"


def test_s3_sdk_contract_uses_private_checks_and_explicit_encryption(tmp_path):
    import boto3
    from botocore.stub import Stubber, ANY
    from botocore.response import StreamingBody

    payload = b"SYNTHETIC SDK ARCHIVE CONTRACT"
    archive = tmp_path / "synthetic.dump"
    archive.write_bytes(payload)
    config = backup.Destination("synthetic-private-bucket", None, "ap-south-1", "AES256", None)
    manifest = {"bytes": len(payload), "archive_sha256": backup.sha256(archive)}
    client = boto3.client(
        "s3",
        region_name="ap-south-1",
        aws_access_key_id="synthetic",
        aws_secret_access_key="synthetic",
    )
    with Stubber(client) as stub:
        stub.add_response(
            "get_public_access_block",
            {
                "PublicAccessBlockConfiguration": {
                    k: True
                    for k in (
                        "BlockPublicAcls",
                        "IgnorePublicAcls",
                        "BlockPublicPolicy",
                        "RestrictPublicBuckets",
                    )
                }
            },
            {"Bucket": config.bucket},
        )
        stub.add_response(
            "put_object",
            {"ServerSideEncryption": "AES256"},
            {
                "Bucket": config.bucket,
                "Key": ANY,
                "Body": ANY,
                "ContentLength": len(payload),
                "ContentType": "application/octet-stream",
                "Metadata": {"sha256": manifest["archive_sha256"]},
                "ServerSideEncryption": "AES256",
            },
        )
        stub.add_response(
            "get_object",
            {"Body": StreamingBody(io.BytesIO(payload), len(payload))},
            {"Bucket": config.bucket, "Key": ANY},
        )
        stub.add_response(
            "put_object",
            {"ServerSideEncryption": "AES256"},
            {
                "Bucket": config.bucket,
                "Key": ANY,
                "Body": ANY,
                "ContentType": "application/json",
                "ServerSideEncryption": "AES256",
            },
        )
        assert backup.upload_verified(client, config, archive, manifest)["offhost_verified"]
        stub.assert_no_pending_responses()


def test_backup_failure_redacts_details_and_cannot_trigger_retention(monkeypatch, capsys):
    config = backup.Destination("synthetic", None, "ap-south-1", "AES256", None)
    monkeypatch.setattr(backup, "configuration", lambda: (config, []))
    monkeypatch.setenv("SECURITY_RETENTION_APPLY", "1")
    monkeypatch.setattr("sys.argv", ["backup"])

    def failed(*args):
        raise RuntimeError("DO-NOT-LOG-PRIVATE-CONNECTION-DETAIL")

    monkeypatch.setattr(backup, "backup", failed)
    monkeypatch.setattr(
        retention,
        "apply_after_backup",
        lambda *a: pytest.fail("Cleanup must never follow failed backup"),
    )
    assert backup.main() == 1
    output = capsys.readouterr().out
    assert "DO-NOT-LOG" not in output and json.loads(output)["status"] == "FAILED"


def test_archive_monitor_kills_own_child_on_size_limit(monkeypatch, tmp_path):
    archive = tmp_path / "too-large.dump"
    archive.write_bytes(b"12345")

    class Process:
        killed = False
        returncode = None

        def poll(self):
            return 1 if self.killed else None

        def kill(self):
            self.killed = True

        def wait(self):
            self.returncode = 1

    process = Process()
    monkeypatch.setattr(backup.subprocess, "Popen", lambda *a, **k: process)
    with pytest.raises(backup.BackupError):
        backup.run_dump(["synthetic-no-command"], {}, archive, maximum=4)
    assert process.killed
