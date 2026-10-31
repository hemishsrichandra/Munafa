import copy
import uuid
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select, func
from backend import models as m
from backend.db import engine
from backend.domain import RuleError
from backend.inventory import exact
from backend.purchasing import checks
from backend.tests.test_trust import other_client


def ok(r, status=200):
    assert r.status_code == status, r.text
    return r.json()


def product(c):
    return ok(
        c.post(
            "/api/products",
            json={"code": uuid.uuid4().hex, "name": "Rice", "unit": "kg", "reorder_threshold": "1"},
        ),
        201,
    )


def draft(p, qty="2.5"):
    return {
        "supplier": "Wholesale",
        "reference": uuid.uuid4().hex,
        "date": date.today().isoformat(),
        "lines": [
            {
                "description": "Rice",
                "product_id": p["id"],
                "billed_quantity": qty,
                "unit": "kg",
                "unit_price_paise": 8000,
                "effective_price_paise": 8000,
            }
        ],
        "tax_paise": 0,
        "discount_paise": 0,
        "total_paise": int(Decimal(qty) * 8000),
    }


def accept(c, kind, entity, version, payload=None, execute_headers=None):
    a = ok(
        c.post(
            "/api/commerce/proposals",
            json={
                "action_type": kind,
                "entity_id": entity,
                "expected_version": version,
                "payload": payload or {},
            },
        ),
        201,
    )
    a = ok(
        c.post(
            f"/api/actions/{a['id']}/approve",
            json={"version": a["version"], "payload_digest": a["payload_digest"]},
        )
    )
    return c.post(
        f"/api/actions/{a['id']}/execute",
        json={"version": a["version"]},
        headers=execute_headers or {},
    )


def purchase(c, p=None):
    p = p or product(c)
    d = draft(p)
    row = ok(c.post("/api/purchases/manual", json=d), 201)
    ok(accept(c, "accept_purchase", row["id"], row["version"]))
    return ok(c.get(f"/api/purchases/{row['id']}")), p


def receiving(p, qty="2.5", damaged="0", complete=True, **kw):
    result = {
        "purchase_version": p["version"],
        "received_on": date.today().isoformat(),
        "delivery_complete": complete,
        "pricing_confirmed": True,
        "lines": [
            {
                "purchase_line_id": p["lines"][0]["id"],
                "quantity": qty,
                "damaged_quantity": damaged,
                "unit": "kg",
                "unit_confirmed": True,
            }
        ],
    }
    result["lines"][0].update(kw)
    return result


def receive(c, p, body):
    r = ok(c.post(f"/api/purchases/{p['id']}/receivings", json=body), 201)
    return accept(c, "accept_receiving", r["id"], r["version"])


def stock(c):
    return Decimal(ok(c.get("/api/products"))[0]["stock_quantity"])


def test_acceptance_no_stock_and_duplicate(client):
    p = product(client)
    d = draft(p)
    row = ok(client.post("/api/purchases/manual", json=d), 201)
    assert client.post("/api/purchases/manual", json=d).status_code == 409
    ok(accept(client, "accept_purchase", row["id"], row["version"]))
    assert stock(client) == 0
    assert (
        client.patch(f"/api/purchases/{row['id']}", json={"version": 1, "draft": d}).status_code
        == 409
    )


@pytest.mark.parametrize(
    "qty,damaged,expected",
    [("2.5", "0", "2.5"), ("2.5", "0.5", "2"), ("3", "0", "3"), ("0.000001", "0", "0.000001")],
)
def test_actual_undamaged_fractional_and_overdelivery(client, qty, damaged, expected):
    p, _ = purchase(client)
    ok(receive(client, p, receiving(p, qty, damaged)))
    assert stock(client) == Decimal(expected)
    with engine().connect() as db:
        assert db.execute(
            select(func.sum(m.inventory_events.c.quantity_delta))
        ).scalar_one() == Decimal(expected)
    c = ok(client.get(f"/api/cases/{p['case_id']}"))
    assert c["calculation"]["amount_paise"] >= 0


def test_partial_then_final(client):
    p, _ = purchase(client)
    ok(receive(client, p, receiving(p, "1", complete=False)))
    c = ok(client.get(f"/api/cases/{p['case_id']}"))
    assert not c["calculation"]["eligible"]
    p = ok(client.get(f"/api/purchases/{p['id']}"))
    ok(receive(client, p, receiving(p, "1.5")))
    assert stock(client) == Decimal("2.5")


@pytest.mark.parametrize(
    "changes",
    [{"quantity": None}, {"unit": "pack"}, {"unit_confirmed": False}, {"damaged_quantity": "3"}],
)
def test_invalid_receiving_cannot_accept(client, changes):
    p, _ = purchase(client)
    r = ok(client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p, **changes)), 201)
    response = client.post(
        "/api/commerce/proposals",
        json={"action_type": "accept_receiving", "entity_id": r["id"], "expected_version": 1},
    )
    assert response.status_code == 409, response.text
    assert stock(client) == 0


def test_event_replay_and_shortage_math(client):
    p, _ = purchase(client)
    r = ok(client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p, "2")), 201)
    a = ok(
        client.post(
            "/api/commerce/proposals",
            json={"action_type": "accept_receiving", "entity_id": r["id"], "expected_version": 1},
        ),
        201,
    )
    a = ok(
        client.post(
            f"/api/actions/{a['id']}/approve",
            json={"version": 1, "payload_digest": a["payload_digest"]},
        )
    )
    key = {"Idempotency-Key": uuid.uuid4().hex}
    first = client.post(
        f"/api/actions/{a['id']}/execute", json={"version": a["version"]}, headers=key
    )
    second = client.post(
        f"/api/actions/{a['id']}/execute", json={"version": a["version"]}, headers=key
    )
    assert ok(first) == ok(second)
    assert stock(client) == 2
    c = ok(client.get(f"/api/cases/{p['case_id']}"))
    assert c["calculation"]["amount_paise"] == 4000


def test_commerce_tenant_isolation(client):
    p, sku = purchase(client)
    other, _ = other_client()
    assert ok(other.get("/api/purchases")) == []
    assert ok(other.get("/api/products")) == []
    assert other.get(f"/api/purchases/{p['id']}").status_code == 404
    assert other.get(f"/api/products/{sku['id']}/movements").status_code == 404


def test_adjustment_approval_role(client):
    p, sku = purchase(client)
    viewer, _ = other_client("viewer", client.get("/api/auth/me").json()["store"]["id"])
    body = {
        "action_type": "inventory_movement",
        "entity_id": sku["id"],
        "expected_version": 0,
        "payload": {
            "product_id": sku["id"],
            "expected_stock_version": 0,
            "kind": "count",
            "quantity": "5",
            "unit": "kg",
            "reference": "COUNT-1",
            "occurred_on": date.today().isoformat(),
            "reason": "Physical stock count",
        },
    }
    assert viewer.post("/api/commerce/proposals", json=body).status_code == 403
    a = ok(client.post("/api/commerce/proposals", json=body), 201)
    assert (
        viewer.post(
            f"/api/actions/{a['id']}/approve",
            json={"version": 1, "payload_digest": a["payload_digest"]},
        ).status_code
        == 403
    )


def test_exact_precision_and_input_checks():
    assert exact("2.500000") == Decimal("2.5")
    with pytest.raises(RuleError):
        exact("0.0000001")
    d = draft({"id": "sku"})
    assert checks(d)["eligible"]
    bad = copy.deepcopy(d)
    bad["total_paise"] += 1
    assert not checks(bad)["eligible"]


def test_conversion_exactness_and_no_inferred_units(client):
    sku = product(client)
    ok(
        client.post(
            f"/api/products/{sku['id']}/conversions",
            json={
                "from_unit": "pack",
                "to_unit": "kg",
                "factor": "0.333333",
                "provenance": "Merchant checked package weight",
            },
        ),
        201,
    )
    d = draft(sku)
    d["lines"][0].update(unit="pack", billed_quantity="1")
    d["total_paise"] = 8000
    p = ok(client.post("/api/purchases/manual", json=d), 201)
    ok(accept(client, "accept_purchase", p["id"], p["version"]))
    p = ok(client.get(f"/api/purchases/{p['id']}"))
    body = receiving(p, "1", unit="pack")
    ok(receive(client, p, body))
    assert stock(client) == Decimal("0.333333")


def test_receiving_stale_purchase_rejected(client):
    p, _ = purchase(client)
    first = ok(
        client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p, "1", complete=False)),
        201,
    )
    second = ok(
        client.post(f"/api/purchases/{p['id']}/receivings", json=receiving(p, "1", complete=False)),
        201,
    )
    ok(accept(client, "accept_receiving", first["id"], 1))
    response = client.post(
        "/api/commerce/proposals",
        json={"action_type": "accept_receiving", "entity_id": second["id"], "expected_version": 1},
    )
    assert response.status_code == 409
    assert stock(client) == 1


def test_purchase_linked_proof_cannot_be_counted_twice(client):
    from backend.tests.test_workflow import approve

    p, _ = purchase(client)
    ok(receive(client, p, receiving(p, "2")))
    c = ok(client.get(f"/api/cases/{p['case_id']}"))
    c = approve(client, c)
    c = ok(
        client.post(f"/api/cases/{c['id']}/sent", json={"version": c["version"], "confirmed": True})
    )
    proof = ok(
        client.post(
            f"/api/cases/{c['id']}/proof",
            files={"file": ("receipt.pdf", b"%PDF-1.4\nSynthetic refund proof", "application/pdf")},
        ),
        201,
    )
    body = {
        "version": c["version"],
        "kind": "refund",
        "supplier": c["invoice"]["supplier"],
        "invoice_reference": c["invoice"]["reference"],
        "evidence_reference": "REF-1",
        "amount_paise": 2000,
        "attachment_id": proof["attachment_id"],
        "applied_confirmed": True,
    }
    c = ok(client.post(f"/api/cases/{c['id']}/resolve", json=body))
    body.update(version=c["version"], evidence_reference="REF-2")
    assert client.post(f"/api/cases/{c['id']}/resolve", json=body).status_code == 409
    assert stock(client) == 2


def test_offline_commerce_operations_replay_without_duplicate_stock(client):
    import base64
    import hashlib
    from datetime import datetime, timezone

    def operation(kind, payload, entity=None, version=None, dependencies=None):
        return {
            "operation_id": str(uuid.uuid4()),
            "operation_type": kind,
            "payload_schema_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "entity_id": entity,
            "expected_version": version,
            "dependency_ids": dependencies or [],
            "payload": payload,
        }

    def submit(body):
        return client.post(
            "/api/sync/operations", json=body, headers={"Idempotency-Key": body["operation_id"]}
        )

    sku = product(client)
    data = b"%PDF-1.4\nSynthetic offline purchase"
    metadata = {
        "name": "bill.pdf",
        "mime": "application/pdf",
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    create = operation("purchase_create", {"draft": draft(sku), "document": metadata})
    created = ok(submit(create), 201)
    assert ok(submit(create), 201) == created
    pid = created["entity_id"]
    assert (
        client.post(
            "/api/commerce/proposals",
            json={"action_type": "accept_purchase", "entity_id": pid, "expected_version": 1},
        ).status_code
        == 409
    )
    upload = operation(
        "purchase_document_upload",
        {**metadata, "content_base64": base64.b64encode(data).decode()},
        pid,
        1,
        [create["operation_id"]],
    )
    uploaded = ok(submit(upload), 201)
    assert ok(submit(upload), 201) == uploaded
    p = ok(client.get(f"/api/purchases/{pid}"))
    assert len(p["documents"]) == 1
    ok(accept(client, "accept_purchase", pid, p["version"]))
    assert stock(client) == 0
    p = ok(client.get(f"/api/purchases/{pid}"))
    capture = operation("purchase_receiving_capture", receiving(p), pid, p["version"])
    captured = ok(submit(capture), 201)
    assert ok(submit(capture), 201) == captured
    assert stock(client) == 0
    ok(accept(client, "accept_receiving", captured["entity_id"], captured["entity_version"]))
    latest = ok(client.get("/api/products"))[0]
    movement = {
        "product_id": sku["id"],
        "expected_stock_version": latest["stock_version"],
        "kind": "damage",
        "quantity": "0.5",
        "unit": "kg",
        "reference": "DAMAGE-OFF",
        "occurred_on": date.today().isoformat(),
        "reason": "Merchant checked damaged stock",
    }
    event = operation(
        "inventory_movement",
        {"movement": movement, "merchant_confirmed": True},
        sku["id"],
        latest["stock_version"],
    )
    applied = ok(submit(event), 201)
    assert ok(submit(event), 201) == applied
    assert stock(client) == 2


def test_smart_low_stock_reorder_and_whatsapp_po(client):
    sku = ok(
        client.post(
            "/api/products",
            json={
                "code": uuid.uuid4().hex,
                "name": "Britannia Good Day 100g",
                "unit": "pack",
                "reorder_threshold": "10",
            },
        ),
        201,
    )
    # Stock is currently 0 <= 10 (below threshold)
    res = ok(client.get("/api/inventory/reorder-suggestions"))
    assert res["count"] >= 1
    match = next(s for s in res["suggestions"] if s["product_id"] == sku["id"])
    assert match["product_name"] == "Britannia Good Day 100g"
    assert match["reorder_threshold"] == "10"
    # Expected reorder qty: 10 * 2 - 0 = 20
    assert Decimal(match["recommended_reorder_qty"]) >= 10
    assert "Britannia Good Day 100g" in match["po_message"]
    assert "https://wa.me/" in match["whatsapp_url"]


def test_expiry_liquidation_radar(client):
    from datetime import timedelta

    sku = ok(
        client.post(
            "/api/products",
            json={
                "code": uuid.uuid4().hex,
                "name": "Amul Fresh Paneer 200g",
                "unit": "pack",
                "expiry_tracking": True,
            },
        ),
        201,
    )
    exp = (date.today() + timedelta(days=5)).isoformat()
    body = {
        "action_type": "inventory_movement",
        "entity_id": sku["id"],
        "expected_version": 0,
        "payload": {
            "product_id": sku["id"],
            "expected_stock_version": 0,
            "kind": "count",
            "quantity": "12",
            "unit": "pack",
            "reference": "INIT-EXP-LOT",
            "occurred_on": date.today().isoformat(),
            "expiry_date": exp,
            "batch_reference": "LOT-EXP-101",
            "reason": "Initial stock with expiry",
        },
    }
    a = ok(client.post("/api/commerce/proposals", json=body), 201)
    appr = ok(
        client.post(
            f"/api/actions/{a['id']}/approve",
            json={"version": 1, "payload_digest": a["payload_digest"]},
        )
    )
    ok(client.post(f"/api/actions/{a['id']}/execute", json={"version": appr["version"]}))

    radar = ok(client.get("/api/inventory/expiry"))
    assert radar["total_lots"] >= 1
    match = next(lot for lot in radar["lots"] if lot["product_id"] == sku["id"])
    assert match["product_name"] == "Amul Fresh Paneer 200g"
    assert match["days_until_expiry"] == 5
    assert match["urgency"] == "critical"
    assert match["suggested_discount_percent"] == 50
    assert "clearance" in match["suggested_action"].lower()
    assert "whatsapp_liquidation_draft" in match
    assert "Amul Fresh Paneer 200g" in match["whatsapp_liquidation_draft"]
