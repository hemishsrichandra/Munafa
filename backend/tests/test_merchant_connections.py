"""Exact display proposals use accepted records; they never send or mutate stock."""

from datetime import timedelta
from backend.domain import local_today
from backend.tests.test_commerce import product, draft, accept, ok


def test_fractional_expiry_estimate_and_clearance_preserve_paise(client):
    p = product(client)
    bill = draft(p, "1")
    bill["reference"] = "EXACT-EXPIRY"
    bill["lines"][0].update(unit_price_paise=1, effective_price_paise=1)
    bill["total_paise"] = 1
    invoice = ok(client.post("/api/purchases/manual", json=bill), 201)
    ok(accept(client, "accept_purchase", invoice["id"], invoice["version"]))
    today = local_today()
    ok(
        accept(
            client,
            "inventory_movement",
            p["id"],
            0,
            {
                "product_id": p["id"],
                "expected_stock_version": 0,
                "kind": "count",
                "quantity": "2.5",
                "unit": p["unit"],
                "reference": "EXP-BATCH",
                "occurred_on": today.isoformat(),
                "expiry_date": (today + timedelta(days=2)).isoformat(),
                "batch_reference": "SYN-EXACT",
                "reason": "Synthetic counted physical stock",
            },
        )
    )
    result = ok(client.get("/api/inventory/expiry"))
    lot = next(row for row in result["lots"] if row["product_id"] == p["id"])
    assert lot["loss_risk_paise"] == 3
    assert lot["suggested_clearance_price_paise"] == 1
    assert "₹0.01" in lot["whatsapp_liquidation_draft"]
    assert "Fresh " not in lot["whatsapp_liquidation_draft"]
    assert (
        client.get(f"/api/products/{p['id']}/movements").json()["events"][0]["quantity_delta"]
        == "2.5"
    )


def test_brief_overdue_amount_preserves_cents(client):
    from backend.tests.test_records import customer, entry

    p = customer(client)
    today = local_today()
    ok(
        entry(
            client,
            customer_id=p["id"],
            amount=65005,
            occurred_on=(today - timedelta(days=8)).isoformat(),
            due_on=(today - timedelta(days=7)).isoformat(),
        ),
        201,
    )
    item = next(
        x
        for x in client.get("/api/brief").json()["items"]
        if x["type"] == "customer_credit_collection"
    )
    assert "650.05 INR" in item["reason"]
    assert item["top_customer"]["amount_paise"] == 65005
