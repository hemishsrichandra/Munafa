import copy
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from backend import payments, models as m, auth, store
from backend.db import engine
from backend.tests.test_trust import other_client


def scenario():
    events, batches = payments.DemoAdapter().snapshot()
    batch = {
        "id": "batch",
        "mode": "demo",
        "provider": "fixture",
        **batches[0].model_dump(exclude={"lines"}),
    }
    lines = [{"id": f"line{i}", **line.model_dump()} for i, line in enumerate(batches[0].lines)]
    rows = [{"id": f"event{i}", **e.model_dump()} for i, e in enumerate(events)]
    return batch, lines, rows


def test_component_math_never_labels_missing_money():
    b, lines, e = scenario()
    r = payments.reconcile(b, lines, e)
    assert r["expected_net_paise"] == 93820
    assert r["difference_paise"] == -820
    assert r["bank_receipt_verified"] is False
    assert {"fees", "refunds", "unexplained_difference"} <= {x["code"] for x in r["reasons"]}
    assert "missing money" not in str(r).lower()
    lines[0]["gst_paise"] = None
    r = payments.reconcile(b, lines, e)
    assert r["expected_net_paise"] is None and r["difference_paise"] is None
    assert "DEMO-LINE-1:gst_paise" in r["missing_fields"]


def test_out_of_order_status_and_multiple_refunds():
    b, lines, e = scenario()
    pending = {
        **e[0],
        "id": "old",
        "source_id": "old",
        "status": "pending",
        "occurred_at": e[0]["occurred_at"] - timedelta(minutes=1),
    }
    second = {
        **e[1],
        "id": "second",
        "source_id": "second",
        "event_id": "refund2",
        "amount_paise": 2000,
    }
    lines[0]["refund_paise"] = 7000
    for rows in ([*e, pending, second], [second, pending, *e]):
        r = payments.reconcile(b, lines, rows)
        assert "uncorrelated_payment" not in {x["code"] for x in r["reasons"]}
        assert "uncorrelated_refund" not in {x["code"] for x in r["reasons"]}
        assert {"event0", "event1", "second"} <= set(r["source_entity_ids"])
    conflict = {**e[0], "id": "conflict", "source_id": "conflict", "amount_paise": 500}
    assert "conflicting_observations" in {
        x["code"] for x in payments.reconcile(b, lines, e + [conflict])["reasons"]
    }


def test_timing_reversal_missing_and_stale():
    b, lines, e = scenario()
    b["status"] = "pending"
    b["payout_at"] = datetime.now(timezone.utc) + timedelta(days=1)
    b["observed_at"] = datetime.now(timezone.utc) - timedelta(days=3)
    b["cutoff_at"] = e[0]["occurred_at"] - timedelta(minutes=1)
    lines[0]["reversal_paise"] = 100
    e.append(
        {
            **e[0],
            "id": "reverse",
            "source_id": "reverse",
            "event_id": "reverse",
            "kind": "reversal",
            "amount_paise": 100,
        }
    )
    r = payments.reconcile(b, lines, e)
    assert {"timing_pending", "reversals", "stale", "cutoff"} <= {x["code"] for x in r["reasons"]}
    assert r["stale"]
    assert payments.reconcile(b, lines, [])["needs_review"]


@pytest.mark.parametrize("value", [True, 1.2, "100", -1])
def test_strict_money(value):
    with pytest.raises(ValidationError):
        payments.PaymentEvent(
            source_id="a",
            event_id="a",
            transaction_id="t",
            kind="payment",
            status="succeeded",
            amount_paise=value,
            occurred_at=datetime.now(timezone.utc),
        )


def test_demo_ingestion_replay_permissions_isolation_and_immutable(client):
    r = client.post("/api/payments/demo")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["mode"] == "demo" and data["live_enabled"] is False
    assert client.post("/api/payments/demo").json()["settlements"] == data["settlements"]
    assert client.get("/api/payments").json()["settlements"] == []
    bid = data["settlements"][0]["batch_id"]
    assert client.get("/api/payments/" + bid + "?mode=demo").status_code == 200
    other, _ = other_client()
    assert other.get("/api/payments?mode=demo").json()["settlements"] == []
    assert other.get("/api/payments/" + bid + "?mode=demo").status_code == 404
    real, _ = other_client(demo=False)
    assert real.post("/api/payments/demo").status_code == 409
    assert real.get("/api/payments?mode=demo").status_code == 403
    viewer, _ = other_client("viewer")
    assert viewer.post("/api/payments/demo").status_code == 403
    for table in ("payment_events", "settlement_batches", "settlement_lines"):
        with pytest.raises(DBAPIError):
            with engine().begin() as db:
                db.execute(text(f"DELETE FROM {table}"))
    assert client.post("/api/payments/live/connect").status_code == 503
    assert client.post("/api/payments/webhook", json={}).status_code == 405


def test_duplicate_source_id_conflict_and_replay(client):
    me = client.get("/api/auth/me").json()
    with engine().connect() as db:
        p = auth.membership(db, me["user_id"], me["store"]["id"])
    token = auth.principal.set(p)
    try:
        events, batches = payments.DemoAdapter().snapshot()
        with store.connect("admin") as db:
            payments.ingest(
                db,
                mode="demo",
                provider="fixture",
                events=events,
                batches=batches,
                provenance={"synthetic": True},
            )
        with store.connect("admin") as db:
            payments.ingest(
                db,
                mode="demo",
                provider="fixture",
                events=list(reversed(events)),
                batches=batches,
                provenance={"synthetic": True},
            )
            assert db.execute(select(func.count()).select_from(m.payment_events)).scalar() == 2
        changed = copy.deepcopy(events)
        changed[0].amount_paise = 111
        with pytest.raises(payments.RuleError, match="different content"):
            with store.connect("admin") as db:
                payments.ingest(
                    db,
                    mode="demo",
                    provider="fixture",
                    events=changed,
                    batches=[],
                    provenance={"synthetic": True},
                )
    finally:
        auth.principal.reset(token)


def test_brief_only_source_records_and_valid_routes(client):
    r = client.get("/api/brief")
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []
    assert r.json()["yesterday"]["recorded_collections_paise"] is None
    p = client.post(
        "/api/products",
        json={"code": "LOW", "name": "Rice", "unit": "kg", "reorder_threshold": "2"},
    ).json()
    assert client.post("/api/payments/demo").status_code == 201
    data = client.get("/api/brief").json()
    assert {x["type"] for x in data["items"]} == {"low_stock", "reconciliation"}
    for item in data["items"]:
        assert (
            item["source_entity_ids"]
            and item["action_id"]
            and item["data_freshness"]["source_updated_at"]
        )
        if item["type"] == "low_stock":
            assert item["source_entity_ids"] == [p["id"]]
            assert item["route"] == "/stock/" + p["id"]
            assert client.get("/api/products/" + p["id"] + "/movements").status_code == 200
        else:
            assert client.get("/api" + item["route"]).status_code == 200
    other, _ = other_client()
    assert other.get("/api/brief").json()["items"] == []
