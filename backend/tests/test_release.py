"""Batch 10 integration/hardening evidence. No real documents or external providers."""

import asyncio
import csv
import io
import json
import uuid
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, insert, update, func
from backend.app import app
from backend import models as m, auth, actions
from backend.db import engine
from backend.samples import sample_invoice
from backend.tests.test_trust import other_client
from backend.tests.test_commerce import purchase, receiving, receive, accept, ok
from backend.tests.test_workflow import shared, resolution

PUBLIC = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/dev-login",
    "/api/auth/signup",
    "/api/auth/demo",
}


def test_audit_and_evidence_money_never_uses_binary_float():
    import ast
    from pathlib import Path
    from backend.domain import rupees

    assert rupees(9007199254740991) == "90071992547409.91"
    assert rupees(-101) == "-1.01"
    tree = ast.parse((Path(__file__).parents[1] / "app.py").read_text())
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.right, ast.Constant)
        and node.right.value == 100
    ], "Route audit/evidence strings must not convert integer paise through binary float."


ENDPOINTS = [
    (method.upper(), path)
    for path, methods in app.openapi()["paths"].items()
    if path.startswith("/api/") and path not in PUBLIC
    for method in methods
    if method in ("get", "post", "patch", "delete", "put")
]


@pytest.mark.parametrize(
    "method,path", ENDPOINTS, ids=[f"{method} {path}" for method, path in ENDPOINTS]
)
def test_every_private_endpoint_rejects_anonymous_before_validation(database, method, path):
    import re

    path = re.sub(r"\{[^}]+\}", "missing", path)
    with TestClient(app) as anonymous:
        r = anonymous.request(method, path, **({"json": {}} if method != "GET" else {}))
    assert r.status_code == 401, (method, path, r.status_code, r.text)


def export_action(client):
    action = ok(client.post("/api/actions", json={"action_type": "export_ledger"}), 201)
    action = ok(
        client.post(
            f"/api/actions/{action['id']}/approve",
            json={"version": action["version"], "payload_digest": action["payload_digest"]},
        )
    )
    ok(client.post(f"/api/actions/{action['id']}/execute", json={"version": action["version"]}))
    return action["id"]


def test_cross_store_every_entity_endpoint_and_same_store_shared_access(client):
    # Valid bodies reach ownership checks rather than merely failing validation.
    c = shared(client)
    proof = resolution(client, c)
    p, sku = purchase(client)
    rd = ok(client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p)), 201)
    doc = ok(
        client.post(
            "/api/purchases/extract-text", json={"text": "SYNTHETIC private original source"}
        ),
        201,
    )["documents"][0]
    a = ok(client.post("/api/actions", json={"action_type": "export_ledger"}), 201)
    payment = ok(client.post("/api/payments/demo"), 201)["settlements"][0]
    aid = export_action(client)
    other, _ = other_client()
    gets = [
        f"/cases/{c['id']}",
        f"/cases/{c['id']}/approvals/{c['approved_version']}",
        f"/attachments/{proof['attachment_id']}",
        f"/purchases/{p['id']}",
        f"/purchase-documents/{doc['id']}",
        f"/products/{sku['id']}/movements",
        f"/products/{sku['id']}/conversions",
        f"/actions/{a['id']}",
        f"/export?action_id={aid}",
        f"/payments/{payment['batch_id']}?mode=demo",
    ]
    for path in gets:
        r = other.get("/api" + path)
        assert r.status_code == 404, (path, r.status_code, r.text)
    writes = [
        (
            "PATCH",
            f"/cases/{c['id']}/review",
            {
                "version": c["version"],
                "invoice": c["invoice"],
                "delivery_complete": True,
                "pricing_confirmed": True,
            },
        ),
        ("POST", f"/cases/{c['id']}/approve", {"version": c["version"]}),
        ("POST", f"/cases/{c['id']}/sent", {"version": c["version"], "confirmed": True}),
        (
            "POST",
            f"/cases/{c['id']}/promise",
            {
                "version": c["version"],
                "note": "Synthetic promise",
                "follow_up": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
            },
        ),
        ("POST", f"/cases/{c['id']}/sample-proof", {}),
        ("POST", f"/cases/{c['id']}/resolve", proof),
        ("POST", f"/cases/{c['id']}/message", {"language": "en-IN"}),
        ("PATCH", f"/purchases/{p['id']}", {"version": p["version"], "draft": p["draft"]}),
        ("POST", f"/purchases/{p['id']}/receivings", receiving(p)),
        ("PATCH", f"/receivings/{rd['id']}", {"version": rd["version"], "payload": receiving(p)}),
        (
            "PATCH",
            f"/products/{sku['id']}",
            {
                "version": sku["version"],
                "product": {"code": sku["code"], "name": "Rice", "unit": "kg"},
            },
        ),
        (
            "POST",
            f"/products/{sku['id']}/conversions",
            {
                "from_unit": "pack",
                "to_unit": "kg",
                "factor": "1",
                "provenance": "Merchant defined synthetic conversion",
            },
        ),
        ("PATCH", f"/actions/{a['id']}", {"version": a["version"], "payload": {}}),
        (
            "POST",
            f"/actions/{a['id']}/approve",
            {"version": a["version"], "payload_digest": a["payload_digest"]},
        ),
        ("POST", f"/actions/{a['id']}/execute", {"version": a["version"]}),
        (
            "POST",
            "/commerce/proposals",
            {
                "action_type": "accept_purchase",
                "entity_id": p["id"],
                "expected_version": p["version"],
            },
        ),
    ]
    for method, path, body in writes:
        r = other.request(
            method, "/api" + path, json=body, headers={"Idempotency-Key": uuid.uuid4().hex}
        )
        assert r.status_code == 404, (method, path, r.status_code, r.text)
    r = other.post(
        f"/api/cases/{c['id']}/proof",
        files={"file": ("proof.pdf", b"%PDF-1.4\nSynthetic", "application/pdf")},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    assert r.status_code == 404, r.text
    for path in ("/cases", "/purchases", "/products"):
        assert other.get("/api" + path).json() == []
    assert other.get("/api/inventory/expiry").json()["lots"] == []
    assert other.get("/api/brief").json()["items"] == []
    assert other.get("/api/payments?mode=demo").json()["settlements"] == []
    # Shared-store records are intentionally visible according to role; actor-
    # bound operation receipts and exports are not transferable across users.
    sid = client.get("/api/auth/me").json()["store"]["id"]
    colleague, _ = other_client(store_id=sid)
    assert colleague.get(f"/api/cases/{c['id']}").status_code == 200
    assert colleague.get(f"/api/attachments/{proof['attachment_id']}").status_code == 200
    assert colleague.get("/api/export?action_id=" + aid).status_code == 403
    key = {"Idempotency-Key": "release-actor-receipt"}
    assert (
        client.post("/api/actions", json={"action_type": "export_ledger"}, headers=key).status_code
        == 201
    )
    assert (
        colleague.post(
            "/api/actions", json={"action_type": "export_ledger"}, headers=key
        ).status_code
        == 409
    )


def test_server_context_fixed_to_session_not_headers_or_body(client):
    me = client.get("/api/auth/me").json()
    _, other_sid = auth.provision(
        uuid.uuid4().hex, "long-release-password", "Separate synthetic store", True
    )
    with engine().begin() as db:
        db.execute(
            insert(m.memberships).values(user_id=me["user_id"], store_id=other_sid, role="owner")
        )
    assert (
        client.get("/api/auth/me", headers={"X-Store-ID": other_sid}).json()["store"]["id"]
        == me["store"]["id"]
    )
    assert (
        client.post(
            "/api/products", json={"code": "A", "name": "A", "unit": "kg", "store_id": other_sid}
        ).status_code
        == 422
    )


def test_request_validation_never_echoes_submitted_secret_or_pii(client):
    secret = "SYNTHETIC-PRIVATE-INPUT-NOT-AN-API-KEY"
    r = client.post("/api/auth/login", json={"username": "x", "password": [secret]})
    assert r.status_code == 422 and secret not in r.text
    r = client.post("/api/products", json={"code": "x", "name": {"contact": secret}, "unit": "kg"})
    assert r.status_code == 422 and secret not in r.text
    r = client.post(
        "/api/commerce/proposals",
        json={
            "action_type": "inventory_movement",
            "entity_id": "missing",
            "expected_version": 0,
            "payload": {"quantity": secret},
        },
    )
    assert r.status_code == 422 and secret not in r.text


def test_streamed_size_limit_without_content_length_and_invalid_lengths(client):
    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies=dict(client.cookies),
        ) as worker:

            async def chunks():
                for _ in range(10):
                    yield b"x" * (1024 * 1024)

            r = await worker.post(
                "/api/products",
                content=chunks(),
                headers={
                    "X-CSRF-Token": client.cookies["pbp_csrf"],
                    "Idempotency-Key": "oversize-chunked",
                },
            )
            assert r.status_code == 413, r.text
            r = await worker.post("/api/auth/login", content=b"x" * 17000)
            assert r.status_code == 413, r.text

    asyncio.run(exercise())
    assert (
        client.post("/api/products", json={}, headers={"Content-Length": "bad"}).status_code == 400
    )
    assert (
        client.post("/api/products", json={}, headers={"Content-Length": "-1"}).status_code == 400
    )


def test_upload_signatures_active_pdf_size_and_error_redaction(client):
    c = client.post("/api/invoices/sample").json()
    for data, mime in [
        (b'<svg onload="alert(1)">', "image/svg+xml"),
        (b"<html>PRIVATE-SYNTHETIC</html>", "application/pdf"),
        (b"%PDF-1.7\n/JavaScript (app.alert(1))", "application/pdf"),
        (b"%PDF-1.7\n/EmbeddedFile /Launch", "application/pdf"),
        (b"\x89PNG\r\n\x1a\n" + b"x" * (8 * 1024 * 1024), "image/png"),
    ]:
        r = client.post(f"/api/cases/{c['id']}/proof", files={"file": ("untrusted", data, mime)})
        assert r.status_code in (409, 413), r.text
        assert "PRIVATE-SYNTHETIC" not in r.text
    assert client.get("/api/cases/" + c["id"]).json()["version"] == c["version"]


@pytest.mark.parametrize(
    "supplier", ['=HYPERLINK("x")', "+cmd", "-1+2", "@SUM(1)", " \t=SUM(1)", "\n=1"]
)
def test_export_formula_injection_and_exact_money(client, supplier):
    inv = sample_invoice()
    inv.update(supplier=supplier, reference="@UNTRUSTED")
    ok(client.post("/api/invoices/manual", json=inv), 201)
    aid = export_action(client)
    r = client.get("/api/export?action_id=" + aid)
    assert r.status_code == 200, r.text
    row = list(csv.reader(io.StringIO(r.text)))[1]
    assert row[1].startswith("'") and row[2].startswith("'")
    assert row[4] == "0.00"


def test_export_snapshot_does_not_mix_a_concurrent_new_case(client, monkeypatch):
    client.post("/api/invoices/sample")
    aid = export_action(client)
    checked, resume = Event(), Event()
    original = actions.export_payload

    def pause(db):
        result = original(db)
        checked.set()
        assert resume.wait(10)
        return result

    monkeypatch.setattr(actions, "export_payload", pause)
    cookies = dict(client.cookies)

    def download():
        with TestClient(app) as worker:
            worker.cookies.update(cookies)
            return worker.get("/api/export?action_id=" + aid)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(download)
        try:
            assert checked.wait(10)
            inv = sample_invoice()
            inv["reference"] = "CONCURRENT-NEW"
            assert client.post("/api/invoices/manual", json=inv).status_code == 201
        finally:
            resume.set()
        result = future.result(timeout=15)
    assert result.status_code == 200, result.text
    assert len(list(csv.reader(io.StringIO(result.text)))) == 2
    assert "CONCURRENT-NEW" not in result.text


def test_direct_receipt_operation_id_is_actual_idempotency_key(client):
    p, _ = purchase(client)
    rd = ok(client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p)), 201)
    key = "release-accepted-receipt-operation"
    assert (
        accept(
            client,
            "accept_receiving",
            rd["id"],
            rd["version"],
            execute_headers={"Idempotency-Key": key},
        ).status_code
        == 200
    )
    with engine().connect() as db:
        assert db.execute(select(m.inventory_events.c.operation_id)).scalar_one() == key


def test_expired_session_and_http_rate_limit(client):
    me = client.get("/api/auth/me").json()
    with engine().begin() as db:
        db.execute(
            update(m.sessions)
            .where(m.sessions.c.user_id == me["user_id"])
            .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
    assert client.get("/api/cases").status_code == 401
    # Real HTTP login limit, not a mock of the limiter. Invalid users still do
    # equal-cost password work; error bodies never include supplied passwords.
    r = None
    for _ in range(12):
        r = client.post(
            "/api/auth/login", json={"username": "unknown", "password": "RELEASE-PRIVATE-PASSWORD"}
        )
        if r.status_code == 429:
            break
    assert r.status_code == 429 and "RELEASE-PRIVATE-PASSWORD" not in r.text


def test_postgresql_backup_restore_rehearsal_only_disposable_objects(client, tmp_path):
    """No real data import/reset. Fixture schema is synthetic and randomly owned.

    Optional PG_BIN selects supported pg_dump/pg_restore. Missing tools are an
    explicit skip, never a successful restore claim. Full local release run sets it.
    """
    import hashlib
    import os
    import shutil
    import subprocess
    from pathlib import Path
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    def binary(name):
        return str(Path(os.environ["PG_BIN"]) / name) if os.getenv("PG_BIN") else shutil.which(name)

    dump, restore = binary("pg_dump"), binary("pg_restore")
    if not dump or not restore:
        pytest.skip("PostgreSQL client binaries unavailable: set PG_BIN for the restore rehearsal.")
    url = make_url(os.environ["TEST_DATABASE_URL"])
    schema = os.environ["DATABASE_SCHEMA"]
    assert schema.startswith("test_") and len(schema) == 37 and schema != "public"
    name = "release_restore_" + uuid.uuid4().hex
    assert name != url.database and name.startswith("release_restore_")
    # Existing API creates only synthetic fixtures in this function's schema.
    c = shared(client)
    partial = resolution(client, c, amount_paise=3000)
    c = ok(client.post(f"/api/cases/{c['id']}/resolve", json=partial))
    full = resolution(client, c, amount_paise=5000)
    ok(client.post(f"/api/cases/{c['id']}/resolve", json=full))
    p, _ = purchase(client)
    assert receive(client, p, receiving(p, "2")).status_code == 200
    assert client.post("/api/payments/demo").status_code == 201

    def snapshot(db):
        result = {}
        for table in m.metadata.sorted_tables:
            rows = [dict(row) for row in db.execute(select(table)).mappings()]

            def encode(value):
                if isinstance(value, (bytes, memoryview)):
                    return bytes(value).hex()
                return str(value)

            content = sorted(json.dumps(row, sort_keys=True, default=encode) for row in rows)
            result[table.name] = {
                "count": len(rows),
                "sha256": hashlib.sha256("\n".join(content).encode()).hexdigest(),
            }
        return result

    with engine().connect() as db:
        before = snapshot(db)
        server_major = int(db.execute(text("SHOW server_version_num")).scalar()) // 10000
    version = subprocess.run([dump, "--version"], capture_output=True, text=True, check=True).stdout
    import re

    client_major = int(re.search(r"(\d+)\.", version).group(1))
    if client_major < server_major:
        pytest.skip(
            "pg_dump older than server; select supported client via PG_BIN. Restore was not performed."
        )
    archive = tmp_path / "synthetic-release.dump"
    environment = {**os.environ, "PGPASSWORD": url.password or ""}
    connection = ["-h", url.host or "127.0.0.1", "-p", str(url.port or 5432), "-U", url.username]
    with archive.open("wb") as output:
        os.chmod(archive, 0o600)
        subprocess.run(
            [dump, *connection, "-Fc", "--no-owner", "--no-acl", "--schema", schema, url.database],
            stdout=output,
            stderr=subprocess.PIPE,
            env=environment,
            check=True,
        )
    toc = subprocess.run(
        [restore, "--list", str(archive)], capture_output=True, env=environment, check=True
    )
    assert b"TABLE DATA" in toc.stdout and b"inventory_events" in toc.stdout
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    restored = None
    created = False
    try:
        with admin.connect() as db:
            db.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        subprocess.run(
            [
                restore,
                *connection,
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "-d",
                name,
                str(archive),
            ],
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        restored = create_engine(
            url.set(database=name), connect_args={"options": f"-csearch_path={schema}"}
        )
        with restored.connect() as db:
            assert snapshot(db) == before
            assert (
                db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "19b0c9cc7712"
            )
            assert (
                db.execute(select(func.sum(m.financial_events.c.amount_paise))).scalar_one() == 8000
            )
            assert (
                db.execute(select(func.sum(m.inventory_events.c.quantity_delta))).scalar_one() == 2
            )
            indexes = (
                db.execute(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname=:schema"),
                    {"schema": schema},
                )
                .scalars()
                .all()
            )
            assert "ix_inventory_product_time" in indexes and "ix_payment_transaction" in indexes
            invalid = db.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE connamespace=CAST(:schema AS regnamespace) AND NOT convalidated"
                ),
                {"schema": schema},
            ).scalar_one()
            assert invalid == 0
        report = {
            "schema": "disposable synthetic only",
            "tables_compared": len(before),
            "record_counts": {name: row["count"] for name, row in before.items()},
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "counts_and_content_hashes_match": True,
            "application_database_restored_over": False,
        }
        (tmp_path / "restore-result.json").write_text(json.dumps(report, indent=2))
        if os.getenv("RELEASE_EVIDENCE_DIR"):
            folder = Path(os.environ["RELEASE_EVIDENCE_DIR"])
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "postgres-restore.json").write_text(json.dumps(report, indent=2))
    finally:
        if restored:
            restored.dispose()
        if created:
            assert name.startswith("release_restore_") and len(name) == 48 and name != url.database
            with admin.connect() as db:
                db.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


@pytest.mark.parametrize(
    "filename",
    [
        "clean.png",
        "poor_light.png",
        "skew.png",
        "thermal.png",
        "mixed_script.png",
        "stamp_and_note.png",
        "abbreviation.png",
        "fractional.png",
        "missing_print.png",
        "injection_text.png",
        "injection_metadata.png",
        "injection_note.png",
    ],
)
def test_synthetic_image_corpus_without_key_preserves_source_and_manual_fallback(client, filename):
    from pathlib import Path
    import hashlib

    data = (Path("evaluation/corpus/images") / filename).read_bytes()
    result = client.post("/api/purchases/document", files={"file": (filename, data, "image/png")})
    assert result.status_code == 201, result.text
    purchase = result.json()
    assert purchase["status"] == "draft" and purchase["accepted_at"] is None
    assert purchase["documents"][0]["sha256"] == hashlib.sha256(data).hexdigest()
    assert purchase["revisions"][-1]["provenance"]["manual_required"]
    assert client.get("/api/products").json() == []
    assert client.get("/api/cases").json() == []
