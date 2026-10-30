"""P2 prerequisite gates are working safeguards, not simulated P2 integrations."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from backend import models as m
from backend.db import engine
from backend.tests.test_trust import other_client
from backend.tests.test_commerce import product, purchase

FLAGS = ("ENABLE_P2_PROCUREMENT", "ENABLE_P2_FINANCIAL_PLANNING", "ENABLE_P2_BENCHMARKING")


@pytest.fixture(autouse=True)
def flags_off(monkeypatch):
    for key in FLAGS:
        monkeypatch.delenv(key, raising=False)


def inspect(client, capability="procurement", intent="purchase_order_draft", **kw):
    return client.post(
        "/api/planning/assess", json={"capability": capability, "intent": intent, **kw}
    )


def truth_counts():
    with engine().connect() as db:
        return {
            t.name: db.execute(select(func.count()).select_from(t)).scalar_one()
            for t in (
                m.purchases,
                m.receipts,
                m.inventory_events,
                m.financial_events,
                m.resolutions,
                m.actions,
            )
        }


def test_default_flags_no_fake_data_no_quality_or_peer_claims(client):
    result = client.get("/api/planning/readiness")
    assert result.status_code == 200, result.text
    data = result.json()
    assert all(
        c["status"] == "disabled" and not c["available"] and not c["external_execution_enabled"]
        for c in data["capabilities"]
    )
    assert all(value == 0 for value in data["record_counts"].values())
    assert data["source_samples"] == [] and data["counts_are_quality_proof"] is False
    assert data["peer_comparison"]["suppressed"] and data["peer_comparison"]["cohort_size"] is None
    assert data["mode"] == "demo"
    assert (
        TestClient(__import__("backend.app", fromlist=["app"]).app)
        .get("/api/planning/readiness")
        .status_code
        == 401
    )


@pytest.mark.parametrize(
    "capability,flag,intent",
    [
        ("procurement", FLAGS[0], "purchase_order_draft"),
        ("financial_planning", FLAGS[1], "financial_summary"),
        ("benchmarking", FLAGS[2], "peer_comparison"),
    ],
)
def test_enabled_flag_cannot_manufacture_prerequisites_or_execute(
    client, monkeypatch, capability, flag, intent
):
    monkeypatch.setenv(flag, "1")
    result = inspect(client, capability, intent)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["capability"]["status"] == "blocked"
    assert data["capability"]["proposal_generation_enabled"] is False
    assert data["proposal_created"] is False and data["external_action_performed"] is False
    assert data["financial_decision"] is None and data["peer_statistics"] is None
    before = truth_counts()
    r = client.post(f"/api/planning/{capability}/execute", json={"approved": True, "version": 999})
    assert r.status_code == 409, r.text
    assert truth_counts() == before


def test_invalid_flag_fails_closed_and_isolated_from_other_flags(client, monkeypatch):
    monkeypatch.setenv(FLAGS[0], "true")
    data = client.get("/api/planning/readiness").json()
    assert all(c["status"] == "disabled" for c in data["capabilities"])
    assert "invalid_flag" in {b["code"] for b in data["capabilities"][0]["blockers"]}


def test_duplicate_order_requests_only_replay_readiness_audit(client):
    before = truth_counts()
    body = {"capability": "procurement", "intent": "purchase_order_draft"}
    key = {"Idempotency-Key": "planning-order-retry"}
    first = client.post("/api/planning/assess", json=body, headers=key)
    retry = client.post("/api/planning/assess", json=body, headers=key)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json() and retry.headers["Idempotency-Replayed"] == "true"
    assert not first.json()["proposal_created"]
    assert truth_counts() == before
    with engine().connect() as db:
        assert (
            db.execute(
                select(func.count())
                .select_from(m.audit_events)
                .where(m.audit_events.c.entity_type == "planning_check")
            ).scalar_one()
            == 1
        )
    # A new request creates another check only, never a duplicate order.
    assert inspect(client).json()["proposal_created"] is False
    assert truth_counts() == before
    changed = client.post(
        "/api/planning/assess",
        json={"capability": "benchmarking", "intent": "peer_comparison"},
        headers=key,
    )
    assert changed.status_code == 409


def test_stale_offer_missing_supplier_and_untrusted_current_claim(client):
    now = datetime.now(timezone.utc)
    result = inspect(
        client,
        offer_timing_claim={
            "observed_at": (now - timedelta(days=3)).isoformat(),
            "valid_until": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert result.status_code == 200, result.text
    codes = {c["code"] for c in result.json()["checks"]}
    assert {"stale_offer_claim", "supplier_source_missing", "supplier_evidence_missing"} <= codes
    fresh = inspect(
        client,
        offer_timing_claim={
            "observed_at": (now - timedelta(minutes=1)).isoformat(),
            "valid_until": (now + timedelta(days=1)).isoformat(),
        },
    ).json()
    assert "unverified_offer_claim" in {c["code"] for c in fresh["checks"]}
    assert not fresh["proposal_created"]
    future = inspect(
        client,
        offer_timing_claim={
            "observed_at": (now + timedelta(days=2)).isoformat(),
            "valid_until": (now + timedelta(days=1)).isoformat(),
        },
    ).json()
    assert "invalid_offer_dates" in {c["code"] for c in future["checks"]}
    assert inspect(client, unit_price_paise=100, price_verified=True).status_code == 422


def test_record_versions_units_and_need_confirmation_are_checked(client):
    p = product(client)
    context = {
        "product_id": p["id"],
        "expected_product_version": p["version"],
        "expected_stock_version": p["stock_version"],
        "unit": p["unit"],
        "merchant_confirmed_need": False,
    }
    initial = inspect(client, product=context).json()
    assert initial["source_records"][0]["id"] == p["id"]
    assert "need_unconfirmed" in {c["code"] for c in initial["checks"]}
    context.update(
        expected_product_version=p["version"] + 1,
        expected_stock_version=999,
        unit="piece",
        merchant_confirmed_need=True,
    )
    stale = inspect(client, product=context).json()
    assert {"stale_source_version", "unit_mismatch"} <= {c["code"] for c in stale["checks"]}
    assert stale["capability"]["prerequisites_proven"] is False
    assert not stale["proposal_created"]


def test_tenant_isolation_source_samples_supplier_and_evidence(client):
    p = product(client)
    case = client.post("/api/invoices/sample").json()
    proof = client.post(
        f"/api/cases/{case['id']}/proof",
        files={"file": ("proof.pdf", b"%PDF-1.4\nSynthetic P2 evidence", "application/pdf")},
    ).json()
    with engine().connect() as db:
        supplier = db.execute(select(m.suppliers.c.id)).scalar_one()
    own = inspect(
        client, supplier_id=supplier, evidence_attachment_id=proof["attachment_id"]
    ).json()
    assert {r["type"] for r in own["source_records"]} == {"supplier", "attachment"}
    assert not own["proposal_created"]  # Existing proof does not verify a current offer.
    other, _ = other_client()
    data = other.get("/api/planning/readiness").json()
    assert data["source_samples"] == [] and data["record_counts"]["catalog_records"] == 0
    for kwargs in (
        {
            "product": {
                "product_id": p["id"],
                "expected_product_version": p["version"],
                "expected_stock_version": p["stock_version"],
                "unit": p["unit"],
            }
        },
        {"supplier_id": supplier},
        {"evidence_attachment_id": proof["attachment_id"]},
    ):
        r = inspect(other, **kwargs)
        assert r.status_code == 404, r.text
        assert p["id"] not in r.text and supplier not in r.text
        other.headers["Idempotency-Key"] = uuid.uuid4().hex
    own_data = client.get("/api/planning/readiness").json()
    assert own_data["source_samples"][0]["route"] == f"/stock/{p['id']}"
    assert client.get(f"/api/products/{p['id']}/movements").status_code == 200


def test_record_counts_and_historical_invoices_do_not_verify_offers_or_debt(client):
    purchase(client)
    data = client.get("/api/planning/readiness").json()
    assert data["record_counts"]["accepted_purchases"] == 1
    assert data["record_counts"]["accepted_physical_receipts"] == 0
    assert not data["counts_are_quality_proof"]
    assert all(not c["available"] for c in data["capabilities"])
    assert "verified_offers_absent" in {b["code"] for b in data["capabilities"][0]["blockers"]}
    assert "payables_receivables_absent" in {b["code"] for b in data["capabilities"][1]["blockers"]}


def test_roles_purpose_and_lending_consent_cannot_enable_submission(client):
    viewer, _ = other_client("viewer")
    assert viewer.get("/api/planning/readiness").status_code == 200
    assert inspect(viewer).status_code == 403
    staff, _ = other_client("staff")
    assert inspect(staff, "financial_planning", "lender_checklist").status_code == 403
    assert (
        client.post("/api/planning/procurement/execute", headers={"X-CSRF-Token": ""}).status_code
        == 403
    )
    missing = inspect(client, "financial_planning", "lender_checklist").json()
    assert "consent_missing" in {c["code"] for c in missing["checks"]}
    claim = {
        "purpose": "lender_document_readiness",
        "process_reference": "PRIVATE-REFERENCE-NOT-TO-AUDIT",
        "granted": True,
    }
    result = inspect(client, "financial_planning", "lender_checklist", lending_consent_claim=claim)
    assert result.status_code == 200, result.text
    assert not result.json()["consent_verified"] and result.json()["financial_decision"] is None
    assert "consent_unverified" in {c["code"] for c in result.json()["checks"]}
    assert "PRIVATE-REFERENCE" not in result.text
    with engine().connect() as db:
        assert "PRIVATE-REFERENCE" not in str(list(db.execute(select(m.audit_events)).mappings()))
    claim["purpose"] = "marketing"
    assert (
        inspect(
            client, "financial_planning", "lender_checklist", lending_consent_claim=claim
        ).status_code
        == 422
    )
    assert (
        inspect(
            client,
            "financial_planning",
            "financial_summary",
            lending_consent_claim={
                "purpose": "lender_document_readiness",
                "process_reference": "x",
                "granted": True,
            },
        ).status_code
        == 422
    )


@pytest.mark.parametrize("size", [0, 1, 2, 1000000])
def test_all_unapproved_cohorts_suppressed_even_if_client_claims_large_size(
    client, monkeypatch, size
):
    monkeypatch.setenv(FLAGS[2], "1")
    r = inspect(client, "benchmarking", "peer_comparison", claimed_cohort_size=size)
    assert r.status_code == 200, r.text
    assert r.json()["peer_statistics"] is None
    assert "cohort_suppressed" in {c["code"] for c in r.json()["checks"]}
    assert client.get("/api/planning/readiness").json()["peer_comparison"]["cohort_size"] is None


@pytest.mark.parametrize(
    "extra",
    [
        {"store_id": "spoof"},
        {"credit_score": 999},
        {"eligible": True},
        {"loan_terms": {"rate": 0}},
        {"send_message": True},
        {"submit_application": True},
        {"cohort_members": ["another-store"]},
    ],
)
def test_forbidden_underwriting_external_actions_and_client_tenant(client, extra):
    assert inspect(client, **extra).status_code == 422


def test_central_approval_allowlist_cannot_be_used_to_bypass_p2_gate(client):
    for action in ("place_order", "approve_credit", "submit_lender_application", "peer_comparison"):
        r = client.post("/api/actions", json={"action_type": action})
        assert r.status_code in (409, 422), r.text
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.actions)).scalar_one() == 0


def test_synthetic_payments_never_prove_live_financial_readiness(client):
    assert client.post("/api/payments/demo").status_code == 201
    data = client.get("/api/planning/readiness").json()
    assert data["record_counts"]["demo_settlement_observations"] == 1
    assert data["record_counts"]["live_settlement_observations"] == 0
    assert not data["counts_are_quality_proof"]
    real, _ = other_client(demo=False)
    live = real.get("/api/planning/readiness").json()
    assert live["mode"] == "merchant_records" and live["label"] == "Your recorded store"
    assert all(value == 0 for value in live["record_counts"].values())
    assert all(not cap["available"] for cap in live["capabilities"])


def test_source_sample_limit_does_not_silently_misstate_counts(client):
    for _ in range(6):
        product(client)
    data = client.get("/api/planning/readiness").json()
    assert data["record_counts"]["catalog_records"] == 6
    assert len(data["source_samples"]) == 5 and data["source_samples_truncated"]
    assert all(
        s["timestamp_basis"] == "catalogue creation (no inventory event)"
        for s in data["source_samples"]
    )
    assert all(
        set(s)
        == {
            "type",
            "id",
            "label",
            "unit",
            "product_version",
            "stock_version",
            "route",
            "source_recorded_at",
            "timestamp_basis",
        }
        for s in data["source_samples"]
    )
