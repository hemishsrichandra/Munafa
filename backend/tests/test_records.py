"""Manual ledgers never infer debt from payments or overwrite financial evidence."""

import uuid
from datetime import timedelta
from backend.tests.clock import merchant_today
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from backend import models as m
from backend.db import engine
from backend.tests.test_commerce import ok
from backend.tests.test_trust import other_client


def fresh_client(*args):
    c, sid = other_client(*args)
    original = c.request

    def request(method, url, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Idempotency-Key", uuid.uuid4().hex)
        return original(method, url, headers=headers, **kwargs)

    c.request = request
    return c, sid


def customer(c, **kw):
    return ok(
        c.post(
            "/api/records/customers",
            json={"name": "Manual customer", "reference": uuid.uuid4().hex, **kw},
        ),
        201,
    )


def entry(c, kind="credit_sale", amount=10000, **kw):
    return c.post(
        "/api/records/entries",
        json={
            "kind": kind,
            "reference": uuid.uuid4().hex,
            "amount_paise": amount,
            "occurred_on": merchant_today(c).isoformat(),
            "note": "Reviewed paper source",
            "merchant_confirmed": True,
            **kw,
        },
    )


def reverse(c, e, **kw):
    return c.post(
        f"/api/records/entries/{e['id']}/reverse",
        json={
            "reference": uuid.uuid4().hex,
            "reason": "Corrected paper entry",
            "merchant_confirmed": True,
            **kw,
        },
    )


def summary(c):
    return ok(c.get("/api/records/summary"))


def test_manual_dues_allocations_reversals_and_cash_are_distinct(client):
    p = customer(client)
    debt = ok(entry(client, customer_id=p["id"]), 201)
    assert summary(client)["customers"][0]["outstanding_paise"] == 10000
    assert summary(client)["cash"]["recorded_balance_paise"] is None
    ok(entry(client, "opening_cash", 2000), 201)
    pay = ok(entry(client, "collection", 3000, customer_id=p["id"], target_id=debt["id"]), 201)
    s = summary(client)
    assert s["customers"][0]["outstanding_paise"] == 7000
    assert s["cash"]["recorded_balance_paise"] == 5000
    assert s["sales_paise"] == 10000
    assert reverse(client, debt).status_code == 409
    ok(reverse(client, pay), 201)
    assert summary(client)["cash"]["recorded_balance_paise"] == 2000
    assert summary(client)["customers"][0]["outstanding_paise"] == 10000
    ok(reverse(client, debt), 201)
    assert summary(client)["customers"][0]["outstanding_paise"] == 0
    assert reverse(client, debt).status_code == 409
    assert (
        entry(client, "collection", 1, customer_id=p["id"], target_id=debt["id"]).status_code == 409
    )


@pytest.mark.parametrize("amount", [0, -1, True, 1.5, "100", 1000000000001])
def test_invalid_amount_never_posts(client, amount):
    assert entry(client, "cash_sale", amount).status_code == 422
    assert summary(client)["entries"] == []


def test_allocation_target_customer_date_and_overpayment_checks(client):
    a, b = customer(client), customer(client)
    debt = ok(entry(client, customer_id=a["id"]), 201)
    assert (
        entry(client, "collection", 1, customer_id=b["id"], target_id=debt["id"]).status_code == 409
    )
    assert (
        entry(client, "collection", 10001, customer_id=a["id"], target_id=debt["id"]).status_code
        == 409
    )
    assert entry(client, "collection", 1, customer_id=a["id"]).status_code == 409
    assert entry(client, "cash_sale", 100, target_id=debt["id"]).status_code == 409
    assert (
        entry(
            client,
            "cash_sale",
            100,
            occurred_on=(merchant_today(client) + timedelta(days=1)).isoformat(),
        ).status_code
        == 409
    )
    assert entry(client, "cash_sale", 100, merchant_confirmed=False).status_code == 409
    assert (
        entry(
            client,
            customer_id=a["id"],
            due_on=(merchant_today(client) - timedelta(days=1)).isoformat(),
        ).status_code
        == 409
    )
    assert entry(client, "expense", 100, customer_id=a["id"]).status_code == 409


def test_reference_guard_idempotent_response_and_append_only_database(client):
    ref = uuid.uuid4().hex
    op = uuid.uuid4().hex
    body = {
        "kind": "cash_sale",
        "reference": ref,
        "amount_paise": 101,
        "occurred_on": merchant_today(client).isoformat(),
        "note": "Checked original",
        "merchant_confirmed": True,
    }
    headers = {"Idempotency-Key": op}
    a = ok(client.post("/api/records/entries", json=body, headers=headers), 201)
    assert ok(client.post("/api/records/entries", json=body, headers=headers), 201) == a
    assert (
        client.post(
            "/api/records/entries", json={**body, "amount_paise": 102}, headers=headers
        ).status_code
        == 409
    )
    assert entry(client, "cash_sale", 101, reference=ref.upper()).status_code == 409
    assert summary(client)["sales_paise"] == 101
    with pytest.raises(DBAPIError), engine().begin() as db:
        db.execute(
            update(m.business_entries)
            .where(m.business_entries.c.id == a["id"])
            .values(amount_paise=1)
        )


def test_simultaneous_collections_cannot_overallocate(client):
    p = customer(client)
    debt = ok(entry(client, customer_id=p["id"]), 201)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: (
                    entry(
                        client, "collection", 8000, customer_id=p["id"], target_id=debt["id"]
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [201, 409]
    assert summary(client)["customers"][0]["outstanding_paise"] == 2000


def test_payables_and_expenses_affect_only_explicit_cash_movements(client):
    ok(entry(client, "opening_cash", 10000), 201)
    bill = ok(
        entry(
            client, "payable", 8000, due_on=(merchant_today(client) + timedelta(days=7)).isoformat()
        ),
        201,
    )
    assert summary(client)["cash"]["recorded_balance_paise"] == 10000
    ok(entry(client, "payable_payment", 3000, target_id=bill["id"]), 201)
    ok(entry(client, "expense", 500, category="rent"), 201)
    s = summary(client)
    assert s["cash"]["recorded_balance_paise"] == 6500
    assert s["obligations"][0]["remaining_paise"] == 5000
    assert s["expenses_by_category"]["rent"] == 500
    assert entry(client, "opening_cash", 1).status_code == 409
    assert s["forecast_enabled"] is False


def test_marketing_requires_recorded_choice_and_revocation_invalidates_recipient(client):
    p = customer(client)
    body = {
        "title": "Reviewed offer",
        "text": "Rice offer for your review",
        "recipient_ids": [p["id"]],
        "merchant_confirmed": True,
    }
    assert client.post("/api/records/campaigns", json=body).status_code == 409
    change = {
        k: p[k]
        for k in ("name", "reference", "phone", "version", "marketing_consent", "consent_note")
    }
    assert (
        client.patch(
            f"/api/records/customers/{p['id']}", json={**change, "marketing_consent": True}
        ).status_code
        == 422
    )
    p = ok(
        client.patch(
            f"/api/records/customers/{p['id']}",
            json={
                **change,
                "marketing_consent": True,
                "consent_note": "Customer agreed today in store",
            },
        )
    )
    ok(client.post("/api/records/campaigns", json=body), 201)
    assert client.get("/api/records/campaigns").json()[0]["sent"] is False
    assert (
        client.post(
            "/api/records/campaigns", json={**body, "recipient_ids": [p["id"], p["id"]]}
        ).status_code
        == 409
    )
    change = {
        k: p[k]
        for k in ("name", "reference", "phone", "version", "marketing_consent", "consent_note")
    }
    ok(
        client.patch(
            f"/api/records/customers/{p['id']}",
            json={**change, "marketing_consent": False, "consent_note": "Customer withdrew today"},
        )
    )
    campaign = client.get("/api/records/campaigns").json()[0]
    assert (
        campaign["currently_eligible_recipient_ids"] == [] and campaign["requires_recipient_review"]
    )
    assert client.patch(f"/api/records/customers/{p['id']}", json=change).status_code == 409


def test_tasks_assignment_role_versions_and_tenant_scope(client):
    staff, sid = fresh_client("staff")
    foreign_task = ok(
        staff.post(
            "/api/records/tasks",
            json={"title": "Open shop", "due_on": merchant_today(client).isoformat()},
        ),
        201,
    )
    assert (
        client.patch(
            f"/api/records/tasks/{foreign_task['id']}", json={"version": 1, "status": "done"}
        ).status_code
        == 404
    )
    assert (
        staff.post(
            "/api/records/tasks",
            json={
                "title": "Bad assignment",
                "due_on": merchant_today(client).isoformat(),
                "assignee_id": client.get("/api/auth/me").json()["user_id"],
            },
        ).status_code
        == 403
    )
    ok(
        staff.patch(
            f"/api/records/tasks/{foreign_task['id']}", json={"version": 1, "status": "done"}
        )
    )
    assert (
        staff.patch(
            f"/api/records/tasks/{foreign_task['id']}", json={"version": 1, "status": "open"}
        ).status_code
        == 409
    )
    assert staff.get("/api/records/staff").status_code == 403
    viewer, _ = fresh_client("viewer", sid)
    assert (
        viewer.post(
            "/api/records/tasks",
            json={"title": "Bad", "due_on": merchant_today(client).isoformat()},
        ).status_code
        == 403
    )


def test_customer_and_financial_cross_store_guards(client):
    p = customer(client)
    d = ok(entry(client, customer_id=p["id"]), 201)
    other, _ = fresh_client()
    assert other.get("/api/records/summary").json()["customers"] == []
    assert entry(other, customer_id=p["id"]).status_code == 404
    assert reverse(other, d).status_code == 404
    assert other.post(f"/api/records/customers/{p['id']}/reminder").status_code == 404
    staff, _ = fresh_client("staff", client.get("/api/auth/me").json()["store"]["id"])
    assert reverse(staff, d).status_code == 403
    assert staff.post(f"/api/records/customers/{p['id']}/reminder").status_code == 403
    assert (
        entry(staff, "collection", 1000, customer_id=p["id"], target_id=d["id"]).status_code == 201
    )


def test_reminder_amount_is_exact_and_no_payment_link_or_send_is_invented(client):
    p = customer(client)
    assert client.post(f"/api/records/customers/{p['id']}/reminder").status_code == 409
    ok(entry(client, amount=101, customer_id=p["id"]), 201)
    r = ok(client.post(f"/api/records/customers/{p['id']}/reminder"))
    assert "INR 1.01" in r["text"] and r["amount_paise"] == 101
    assert r["payment_link"] is None and r["sent"] is False


def test_offline_manual_record_replay_and_target_checks(client):
    body = {
        "operation_id": str(uuid.uuid4()),
        "operation_type": "business_entry_create",
        "payload_schema_version": 1,
        "client_created_at": merchant_today(client).isoformat() + "T12:00:00+05:30",
        "dependency_ids": [],
        "entity_id": None,
        "expected_version": None,
        "payload": {
            "kind": "cash_sale",
            "reference": "OFF-CASH",
            "amount_paise": 101,
            "occurred_on": merchant_today(client).isoformat(),
            "note": "Reviewed offline source",
            "merchant_confirmed": True,
        },
    }
    headers = {"Idempotency-Key": body["operation_id"]}
    a = ok(client.post("/api/sync/operations", json=body, headers=headers), 201)
    assert ok(client.post("/api/sync/operations", json=body, headers=headers), 201) == a
    assert summary(client)["sales_paise"] == 101
    body.update(operation_id=str(uuid.uuid4()), entity_id=a["entity_id"])
    assert (
        client.post(
            "/api/sync/operations", json=body, headers={"Idempotency-Key": body["operation_id"]}
        ).status_code
        == 409
    )


def test_noncash_manual_payment_reduces_debt_without_inventing_cash(client):
    p = customer(client)
    ok(entry(client, "opening_cash", 10000), 201)
    debt = ok(entry(client, customer_id=p["id"]), 201)
    pay = ok(
        entry(
            client,
            "collection",
            3000,
            customer_id=p["id"],
            target_id=debt["id"],
            payment_channel="upi",
        ),
        201,
    )
    s = summary(client)
    assert s["customers"][0]["outstanding_paise"] == 7000
    assert s["cash"]["recorded_balance_paise"] == 10000
    ok(entry(client, "expense", 500, payment_channel="bank"), 201)
    assert summary(client)["expenses_by_category"]["other"] == 500
    assert summary(client)["cash"]["recorded_balance_paise"] == 10000
    ok(reverse(client, pay), 201)
    assert summary(client)["cash"]["recorded_balance_paise"] == 10000
    assert summary(client)["customers"][0]["outstanding_paise"] == 10000
    assert entry(client, "opening_cash", 1, payment_channel="bank").status_code == 409


def test_store_settings_and_whatsapp_upi_reminder(client):
    settings = ok(client.get("/api/records/store-settings"))
    assert settings["upi_vpa"] is None
    assert settings["reminder_language"] == "en"

    updated = ok(
        client.patch(
            "/api/records/store-settings",
            json={"upi_vpa": "lakshmi@paytm", "reminder_language": "hi"},
        )
    )
    assert updated["upi_vpa"] == "lakshmi@paytm"
    assert updated["reminder_language"] == "hi"

    p = customer(client)
    ok(entry(client, amount=125000, customer_id=p["id"]), 201)
    r = ok(client.post(f"/api/records/customers/{p['id']}/reminder"))
    assert r["amount_paise"] == 125000
    assert r["upi_vpa"] == "lakshmi@paytm"
    assert "upi://pay?pa=lakshmi@paytm" in r["payment_link"]
    assert "1250" in r["payment_link"]
    assert "upi://pay?pa=lakshmi@paytm" in r["text"]
    assert "1250" in r["text"]
    assert r["sent"] is False


def test_galla_hisab_expected_calculation_and_verification(client):
    # Starting cash: ₹2,000 (200000 paise)
    ok(entry(client, "opening_cash", 200000), 201)
    # Cash sales today: ₹8,450 (845000 paise)
    ok(entry(client, "cash_sale", 845000, payment_channel="cash"), 201)
    # Cash expenses today: ₹1,200 (120000 paise)
    ok(entry(client, "expense", 120000, category="transport", payment_channel="cash"), 201)

    hisab = ok(client.get("/api/records/galla-hisab"))
    # Expected: 2000 + 8450 - 1200 = 9250 (925000 paise)
    assert hisab["opening_cash_paise"] == 200000
    assert hisab["cash_sales_today_paise"] == 845000
    assert hisab["cash_expenses_today_paise"] == 120000
    assert hisab["expected_cash_paise"] == 925000

    # Counted cash: ₹9,100 (910000 paise) -> shortage of ₹150 (15000 paise)
    res = ok(client.post("/api/records/galla-hisab/verify", json={"counted_cash_paise": 910000}))
    assert res["status"] == "shortage"
    assert res["difference_paise"] == -15000
    assert "Shortage of ₹150" in res["badge"]

    # Counted cash: ₹9,250 (925000 paise) -> exact match
    res_exact = ok(client.post("/api/records/galla-hisab/verify", json={"counted_cash_paise": 925000}))
    assert res_exact["status"] == "balanced"
    assert res_exact["difference_paise"] == 0
    assert "Exact match" in res_exact["badge"]
