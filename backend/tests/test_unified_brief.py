"""Onboarding and home items must point at existing, store-scoped evidence."""

import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from backend.tests.clock import merchant_today
from backend.tests.test_records import customer, entry, reverse, ok, fresh_client
from backend.tests.test_workflow import sample, review, approve


def test_sample_reuse_preserves_review_and_approval_without_duplicate_history(client):
    original = approve(client, review(client, sample(client)))
    again = client.post("/api/invoices/sample").json()
    assert again["id"] == original["id"] and again["sample_reused"] is True
    assert again["version"] == original["version"]
    assert again["history"] == original["history"]
    assert again["approved_amount_paise"] == original["approved_amount_paise"]
    assert len(client.get("/api/cases").json()) == 1
    assert client.post("/api/invoices/manual", json=original["invoice"]).status_code == 409


def test_concurrent_explicit_samples_return_one_case(client):
    sid = client.get("/api/auth/me").json()["store"]["id"]
    a, _ = fresh_client("owner", sid)
    b, _ = fresh_client("owner", sid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda c: c.post("/api/invoices/sample"), [a, b]))
    assert all(r.status_code == 201 for r in responses)
    assert len({r.json()["id"] for r in responses}) == 1
    assert len(client.get("/api/cases").json()) == 1


def test_seeded_review_is_an_action_and_walkthrough_never_confirms_quantities(client):
    c = sample(client)
    brief = client.get("/api/brief").json()
    item = next(x for x in brief["items"] if x["type"] == "invoice_review")
    assert item["source_entity_ids"] == [c["id"]]
    assert client.get("/api" + item["route"]).status_code == 200
    assert brief["onboarding"]["route"] == item["route"]
    assert not any(s["complete"] for s in brief["onboarding"]["steps"])
    assert all(line["received"] is None for line in c["invoice"]["lines"])


def test_manual_totals_do_not_double_count_collections_or_reversed_sales(client):
    person = customer(client)
    date = merchant_today(client)
    debt = ok(entry(client, customer_id=person["id"], due_on=date.isoformat()), 201)
    payment = ok(
        entry(
            client,
            "collection",
            2000,
            customer_id=person["id"],
            target_id=debt["id"],
            payment_channel="upi",
        ),
        201,
    )
    sale = ok(entry(client, "cash_sale", 5000), 201)
    ok(entry(client, "expense", 1234, payment_channel="bank"), 201)
    undone = ok(entry(client, "cash_sale", 999), 201)
    ok(reverse(client, undone), 201)
    data = client.get("/api/brief").json()
    totals = data["manual_totals"]
    assert totals["sales_paise"] == 15000
    assert totals["expenses_paise"] == 1234
    assert totals["customer_dues_paise"] == 8000
    assert totals["cash"]["recorded_balance_paise"] is None
    assert totals["today"] == {"sales_paise": 15000, "expenses_paise": 1234}
    due = next(x for x in data["items"] if x["type"] == "customer_due")
    assert due["source_entity_ids"] == [debt["id"], person["id"], payment["id"]]
    original = client.get("/api" + due["route"]).json()
    assert original["id"] == debt["id"] and original["remaining_paise"] == 8000
    assert [r["id"] for r in original["allocations"]] == [payment["id"]]
    sources = client.get("/api/records/entries?group=sales").json()
    assert {x["id"] for x in sources["items"]} == {debt["id"], sale["id"]}
    assert sources["total_count"] == 2 and sources["next_offset"] is None


def test_undated_future_paid_obligations_and_done_tasks_not_due_actions(client):
    person = customer(client)
    date = merchant_today(client)
    ok(entry(client, customer_id=person["id"]), 201)
    future = ok(
        entry(client, customer_id=person["id"], due_on=(date + timedelta(days=2)).isoformat()), 201
    )
    paid = ok(entry(client, customer_id=person["id"], due_on=date.isoformat()), 201)
    ok(
        entry(
            client,
            "collection",
            paid["amount_paise"],
            customer_id=person["id"],
            target_id=paid["id"],
        ),
        201,
    )
    task = ok(
        client.post(
            "/api/records/tasks", json={"title": "Close the shop", "due_on": date.isoformat()}
        ),
        201,
    )
    data = client.get("/api/brief").json()
    assert not any(x["type"] == "customer_due" for x in data["items"])
    task_item = next(x for x in data["items"] if x["type"] == "store_task")
    assert task_item["source_entity_ids"] == [task["id"]]
    assert client.get("/api" + task_item["route"]).json()["title"] == task["title"]
    ok(
        client.patch(
            "/api/records/tasks/" + task["id"], json={"version": task["version"], "status": "done"}
        )
    )
    assert not any(x["type"] == "store_task" for x in client.get("/api/brief").json()["items"])
    assert client.get("/api/records/entries/" + future["id"]).status_code == 200


def test_source_endpoints_and_aggregate_actions_are_tenant_scoped(client):
    person = customer(client)
    debt = ok(
        entry(client, customer_id=person["id"], due_on=merchant_today(client).isoformat()), 201
    )
    task = ok(
        client.post(
            "/api/records/tasks",
            json={"title": "Count stock", "due_on": merchant_today(client).isoformat()},
        ),
        201,
    )
    other, _ = fresh_client()
    for path in (
        f"/records/entries/{debt['id']}",
        f"/records/customers/{person['id']}",
        f"/records/tasks/{task['id']}",
    ):
        assert other.get("/api" + path).status_code == 404
    assert other.get("/api/records/entries").json()["items"] == []
    brief = other.get("/api/brief").json()
    assert brief["items"] == [] and brief["manual_totals"]["sales_paise"] == 0
    assert brief["manual_totals"]["record_count"] == 0
    assert brief["yesterday"]["recorded_collections_paise"] is None


def test_source_pagination_has_no_silent_last_100_limit(client):
    # Normal repository paths create immutable records; paging never invents aggregates.
    for _ in range(52):
        ok(entry(client, "cash_sale", 1, reference="page-" + uuid.uuid4().hex), 201)
    a = client.get("/api/records/entries?group=sales").json()
    b = client.get("/api/records/entries?group=sales&offset=50").json()
    assert len(a["items"]) == 50 and len(b["items"]) == 2
    assert a["total_count"] == 52 and a["next_offset"] == 50 and b["next_offset"] is None
    assert not ({x["id"] for x in a["items"]} & {x["id"] for x in b["items"]})


def test_overdue_customer_credit_collection_elevated_in_brief(client):
    person1 = customer(client, name="Suresh Kumar")
    person2 = customer(client, name="Anita Devi")
    t = merchant_today(client)

    # Suresh owes ₹2,400 overdue by 7 days (recorded 14 days ago)
    ok(
        entry(
            client,
            customer_id=person1["id"],
            amount=240000,
            occurred_on=(t - timedelta(days=14)).isoformat(),
            due_on=(t - timedelta(days=7)).isoformat(),
        ),
        201,
    )
    # Anita owes ₹850 overdue by 5 days (recorded 10 days ago)
    ok(
        entry(
            client,
            customer_id=person2["id"],
            amount=85000,
            occurred_on=(t - timedelta(days=10)).isoformat(),
            due_on=(t - timedelta(days=5)).isoformat(),
        ),
        201,
    )

    data = client.get("/api/brief").json()
    p1 = next(x for x in data["items"] if x["type"] == "customer_credit_collection")
    assert p1["priority"] == 1
    assert "Suresh Kumar" in p1["reason"]
    assert "2400 INR" in p1["reason"]
    assert "7 days overdue" in p1["reason"]
    assert "Anita Devi" in p1["reason"]
    assert p1["top_customer"]["customer_name"] == "Suresh Kumar"
    assert p1["top_customer"]["amount_paise"] == 240000
