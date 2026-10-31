from backend.tests.test_workflow import shared, resolution
from backend.tests.test_trust import other_client
from backend.tests.test_commerce import purchase, receive, receiving, ok


def test_supplier_outcomes_are_scoped_and_promises_are_not_recovery(client):
    c = shared(client)
    report = client.get("/api/supplier-performance")
    assert report.status_code == 200
    row = report.json()["suppliers"][0]["cases"][0]
    assert row["remaining_paise"] == 8000
    assert row["shortages"]
    assert row["first_recovery_hours"] is None
    assert row["full_recovery_hours"] is None
    assert row["damage"] == []
    other, _ = other_client()
    assert other.get("/api/supplier-performance").json()["suppliers"] == []
    result = client.post(f"/api/cases/{c['id']}/resolve", json=resolution(client, c))
    assert result.status_code == 200, result.text
    final = client.get("/api/supplier-performance").json()["suppliers"][0]["cases"][0]
    assert final["remaining_paise"] == 0
    assert final["recovered_paise"] == 8000
    assert final["first_recovery_hours"] >= 0
    assert final["full_recovery_hours"] >= 0


def test_unapproved_quantities_are_not_performance_claims(client):
    client.post("/api/invoices/sample")
    row = client.get("/api/supplier-performance").json()["suppliers"][0]["cases"][0]
    assert not row["approved"]
    assert row["remaining_paise"] is None
    assert row["shortages"] == []


def test_accepted_damage_is_linked_without_mixing_units(client):
    p, _ = purchase(client)
    ok(receive(client, p, receiving(p, qty="2.5", damaged="0.5")))
    rows = client.get("/api/supplier-performance").json()["suppliers"]
    case = next(c for s in rows for c in s["cases"] if c["damage"])
    assert case["damage"][0]["unit"] == "kg"
    assert float(case["damage"][0]["quantity"]) == 0.5
    assert case["damage"][0]["receipt_id"]
