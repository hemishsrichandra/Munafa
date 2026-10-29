import copy
import json
from datetime import date
import pytest
import httpx
from fastapi.testclient import TestClient
from backend import store
from backend.app import app
from backend.domain import calculate


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MUNAFA_SEED", "0")
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    with TestClient(app) as c:
        yield c


def sample(client):
    r = client.post("/api/invoices/sample")
    assert r.status_code == 201, r.text
    return r.json()


def review(client, c, received=(10, 6, 24), complete=True, pricing=True):
    invoice = copy.deepcopy(c["invoice"])
    for line, n in zip(invoice["lines"], received):
        line.update(received=n, unit="piece" if line["unit"] == "unknown" else line["unit"])
        line.update(received_unit=line["unit"], unit_confirmed=True)
    r = client.patch(
        f"/api/cases/{c['id']}/review",
        json={
            "version": c["version"],
            "invoice": invoice,
            "delivery_complete": complete,
            "pricing_confirmed": pricing,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def approve(client, c):
    r = client.post(f"/api/cases/{c['id']}/approve", json={"version": c["version"]})
    assert r.status_code == 200, r.text
    return r.json()


def shared(client):
    c = approve(client, review(client, sample(client)))
    r = client.post(f"/api/cases/{c['id']}/sent", json={"version": c["version"], "confirmed": True})
    assert r.status_code == 200, r.text
    return r.json()


def resolution(client, c, **overrides):
    fixture_args = {
        k: overrides[k]
        for k in ("amount_paise", "kind", "evidence_reference")
        if k in overrides and (k != "amount_paise" or 0 < overrides[k] <= c["remaining_paise"])
    }
    proof = client.post(f"/api/cases/{c['id']}/sample-proof", json=fixture_args).json()
    proof.pop("synthetic", None)
    return {**proof, "version": c["version"], "applied_confirmed": True, **overrides}


def test_complete_shortage_to_resolution_and_export(client):
    c = shared(client)
    assert c["approved_amount_paise"] == 8000
    assert c["status"] == "sent"
    promise = client.post(
        f"/api/cases/{c['id']}/promise",
        json={
            "version": c["version"],
            "note": "Adjust next bill",
            "follow_up": date.today().isoformat(),
        },
    )
    assert promise.status_code == 200
    c = promise.json()
    r = client.post(f"/api/cases/{c['id']}/resolve", json=resolution(client, c))
    assert r.status_code == 200, r.text
    c = r.json()
    assert (c["status"], c["recovered_paise"], c["remaining_paise"]) == ("resolved", 8000, 0)
    assert len(c["history"]) == 6
    ledger = client.get("/api/export")
    assert "80.00" in ledger.text
    assert "resolved" in ledger.text
    assert client.get(f"/api/cases/{c['id']}").json()["resolutions"] == c["resolutions"]


def test_draft_blocks_approval_and_message(client):
    c = sample(client)
    assert client.post(f"/api/cases/{c['id']}/approve", json={"version": 1}).status_code == 409
    assert client.post(f"/api/cases/{c['id']}/message", json={}).status_code == 409


@pytest.mark.parametrize("complete,pricing", [(False, True), (True, False), (False, False)])
def test_delivery_and_price_confirmation_required(client, complete, pricing):
    c = review(client, sample(client), complete=complete, pricing=pricing)
    assert not c["calculation"]["eligible"]
    assert (
        client.post(f"/api/cases/{c['id']}/approve", json={"version": c["version"]}).status_code
        == 409
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit", "unknown"),
        ("received_unit", "carton"),
        ("unit_confirmed", False),
        ("received", None),
        ("received", 13),
    ],
)
def test_units_missing_counts_and_over_delivery_block(client, field, value):
    c = review(client, sample(client))
    inv = copy.deepcopy(c["invoice"])
    inv["lines"][0][field] = value
    r = client.patch(
        f"/api/cases/{c['id']}/review",
        json={
            "version": c["version"],
            "invoice": inv,
            "delivery_complete": True,
            "pricing_confirmed": True,
        },
    )
    assert r.status_code == 200
    assert not r.json()["calculation"]["eligible"]


def test_exact_integer_money(client):
    c = sample(client)
    inv = c["invoice"]
    inv["lines"] = [
        {
            **inv["lines"][0],
            "price_paise": 123,
            "received": 9,
            "received_unit": "pack",
            "unit_confirmed": True,
        }
    ]
    assert calculate(inv["lines"], True, True)["amount_paise"] == 369
    inv["lines"][0]["billed"] = 1.5
    assert client.post("/api/invoices/manual", json=inv).status_code == 422


def test_no_shortage_cannot_approve(client):
    c = review(client, sample(client), received=(12, 6, 24))
    assert c["calculation"]["amount_paise"] == 0
    assert (
        client.post(f"/api/cases/{c['id']}/approve", json={"version": c["version"]}).status_code
        == 409
    )


def test_edit_invalidates_approval_and_preserves_audit(client):
    c = shared(client)
    c = review(client, c, received=(9, 6, 24))
    assert c["status"] == "review"
    assert c["approved_version"] is None
    assert c["approved_amount_paise"] is None
    assert any(h["action"] == "Sharing confirmed" for h in c["history"])
    assert (
        client.post(
            f"/api/cases/{c['id']}/sent", json={"version": c["version"], "confirmed": True}
        ).status_code
        == 409
    )
    c = approve(client, c)
    assert c["approved_amount_paise"] == 12000


def test_stale_version_is_rejected(client):
    c = sample(client)
    review(client, c)
    r = client.post(f"/api/cases/{c['id']}/approve", json={"version": 1})
    assert r.status_code == 409
    assert "another tab" in r.json()["detail"]


def test_sharing_requires_explicit_confirmation(client):
    c = approve(client, review(client, sample(client)))
    assert (
        client.post(
            f"/api/cases/{c['id']}/sent", json={"version": c["version"], "confirmed": False}
        ).status_code
        == 409
    )
    assert client.get(f"/api/cases/{c['id']}").json()["status"] == "ready"


@pytest.mark.parametrize(
    "overrides",
    [
        {"supplier": "Wrong Supplier"},
        {"invoice_reference": "WRONG"},
        {"amount_paise": 8001},
        {"amount_paise": 0},
        {"applied_confirmed": False},
        {"attachment_id": "missing"},
    ],
)
def test_resolution_must_match_and_have_proof(client, overrides):
    c = shared(client)
    r = client.post(f"/api/cases/{c['id']}/resolve", json=resolution(client, c, **overrides))
    assert r.status_code in (409, 422), r.text
    assert client.get(f"/api/cases/{c['id']}").json()["recovered_paise"] == 0


def test_partial_credit_duplicate_guard_and_refund(client):
    c = shared(client)
    payload = resolution(client, c, amount_paise=3000)
    r = client.post(f"/api/cases/{c['id']}/resolve", json=payload)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "partial" and c["remaining_paise"] == 5000
    duplicate = {**payload, "version": c["version"], "amount_paise": 2000}
    r = client.post(f"/api/cases/{c['id']}/resolve", json=duplicate)
    assert r.status_code == 409 and "already" in r.json()["detail"]
    assert client.get(f"/api/cases/{c['id']}").json()["version"] == c["version"]
    payload = resolution(
        client, c, kind="refund", amount_paise=5000, evidence_reference="REFUND-02"
    )
    r = client.post(f"/api/cases/{c['id']}/resolve", json=payload)
    assert r.json()["status"] == "resolved" and r.json()["recovered_paise"] == 8000
    inv = c["invoice"]
    assert (
        client.patch(
            f"/api/cases/{c['id']}/review",
            json={
                "version": r.json()["version"],
                "invoice": inv,
                "delivery_complete": True,
                "pricing_confirmed": True,
            },
        ).status_code
        == 409
    )


def test_no_synthetic_proof_for_manual_case(client):
    inv = sample(client)["invoice"]
    inv["reference"] = "REAL-01"
    c = client.post("/api/invoices/manual", json=inv).json()
    assert client.post(f"/api/cases/{c['id']}/sample-proof").status_code == 409


def test_duplicate_invoice_rejected(client):
    sample(client)
    assert client.post("/api/invoices/sample").status_code == 409


def test_invalid_date_and_followup(client):
    inv = sample(client)["invoice"]
    inv["date"] = "2026-99-99"
    inv["reference"] = "INVALID"
    assert client.post("/api/invoices/manual", json=inv).status_code == 409


def test_missing_key_and_invalid_upload(client):
    assert (
        client.post(
            "/api/invoices/extract-text",
            json={"text": "Supplier invoice A-104, biscuits 12 packs at 40 rupees"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/invoices/extract", files={"file": ("x.png", b"not an image", "image/png")}
        ).status_code
        == 409
    )
    assert client.get("/api/attachments/missing").status_code == 404
    assert client.get("/api/cases/missing").status_code == 404


def test_cross_origin_write_blocked(client):
    assert (
        client.post(
            "/api/invoices/sample", headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )


def test_sarvam_text_contract_and_untrusted_receiving_reset(client, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "unit-test-key")
    captured = {}

    def post(url, **kw):
        captured.update(url=url, **kw)
        inv = {
            "supplier": "Test",
            "reference": "TEST-1",
            "date": "2026-10-29",
            "lines": [
                {
                    "name": "Tea",
                    "billed": 6,
                    "unit": "pack",
                    "price_paise": 12500,
                    "received": 6,
                    "received_unit": "pack",
                    "unit_confirmed": True,
                }
            ],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(inv)}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    r = client.post(
        "/api/invoices/extract-text",
        json={"text": "Test supplier TEST-1 Tea 6 packs at INR 125.00 29 October 2026"},
    )
    assert r.status_code == 201, r.text
    assert captured["url"] == "https://api.sarvam.ai/v1/chat/completions"
    assert captured["headers"] == {"api-subscription-key": "unit-test-key"}
    assert captured["json"]["model"] == "sarvam-105b"
    assert r.json()["invoice"]["lines"][0]["received"] is None
    assert not r.json()["invoice"]["lines"][0]["unit_confirmed"]


def test_sarvam_vision_contract(client, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    captured = {}

    def post(url, **kw):
        captured.update(url=url, **kw)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "supplier": "Test",
                                    "reference": "IMG-1",
                                    "date": "2026-10-29",
                                    "lines": [
                                        {
                                            "name": "Tea",
                                            "billed": 6,
                                            "unit": "pack",
                                            "price_paise": 12500,
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    r = client.post(
        "/api/invoices/extract",
        files={"file": ("invoice.png", b"\x89PNG\r\n\x1a\n" + b"test-image", "image/png")},
    )
    assert r.status_code == 201, r.text
    assert captured["json"]["model"] == "gemma4"
    assert captured["url"].endswith("/v2/chat/completions")
    assert captured["json"]["messages"][1]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )
    assert r.json()["attachment_id"]


def test_sarvam_translation_and_failure_preserve_state(client, monkeypatch):
    c = shared(client)
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    captured = {}

    def post(url, **kw):
        captured.update(url=url, **kw)
        return httpx.Response(
            200,
            json={"translated_text": "कृपया बिल A-104 की जाँच करें।"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    r = client.post(f"/api/cases/{c['id']}/message", json={"language": "hi-IN"})
    assert r.status_code == 200 and r.json()["provider"] == "sarvam"
    assert captured["url"].endswith("/translate")
    assert captured["json"]["target_language_code"] == "hi-IN"
    assert client.get(f"/api/cases/{c['id']}").json()["version"] == c["version"]

    def failed(url, **kw):
        return httpx.Response(403, json={"error": {}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", failed)
    r = client.post(f"/api/cases/{c['id']}/message", json={"language": "kn-IN"})
    assert r.status_code == 409 and "403" in r.json()["detail"]
    assert "test-key" not in r.text
    assert client.get(f"/api/cases/{c['id']}").json()["status"] == "sent"


def test_same_proof_cannot_count_twice_under_another_reference(client):
    c = shared(client)
    payload = resolution(client, c, amount_paise=3000)
    r = client.post(f"/api/cases/{c['id']}/resolve", json=payload)
    c = r.json()
    payload.update(version=c["version"], evidence_reference="DIFFERENT-REF")
    r = client.post(f"/api/cases/{c['id']}/resolve", json=payload)
    assert r.status_code == 409 and "file has already" in r.json()["detail"]
    assert client.get(f"/api/cases/{c['id']}").json()["recovered_paise"] == 3000


def test_approved_snapshot_survives_later_edits(client):
    c = approve(client, review(client, sample(client)))
    approved_version = c["approved_version"]
    original = client.get(f"/api/cases/{c['id']}/approvals/{approved_version}").json()
    c = review(client, c, received=(9, 6, 24))
    stored = client.get(f"/api/cases/{c['id']}/approvals/{approved_version}").json()
    assert stored == original
    assert stored["invoice"]["lines"][0]["received"] == 10
    assert stored["amount_paise"] == 8000
    assert c["invoice"]["lines"][0]["received"] == 9


def test_proof_from_another_case_is_rejected(client):
    c = shared(client)
    p = resolution(client, c)
    inv = copy.deepcopy(c["invoice"])
    inv["reference"] = "A-105"
    another = client.post("/api/invoices/manual", json=inv).json()
    another = approve(client, review(client, another))
    another = client.post(
        f"/api/cases/{another['id']}/sent", json={"version": another["version"], "confirmed": True}
    ).json()
    p.update(version=another["version"], invoice_reference="A-105")
    r = client.post(f"/api/cases/{another['id']}/resolve", json=p)
    assert r.status_code == 409 and "belonging to this case" in r.json()["detail"]


def test_same_origin_on_custom_loopback_port_is_allowed(client):
    with TestClient(app, base_url="http://127.0.0.1:8001") as local:
        assert (
            local.post(
                "/api/invoices/sample", headers={"Origin": "http://127.0.0.1:8001"}
            ).status_code
            == 201
        )


def test_synthetic_proof_fields_must_match_document(client):
    c = shared(client)
    payload = resolution(client, c)
    payload["amount_paise"] = 3000
    r = client.post(f"/api/cases/{c['id']}/resolve", json=payload)
    assert r.status_code == 409 and "does not match the synthetic evidence" in r.json()["detail"]


def test_reset_removes_only_synthetic_cases(client, monkeypatch):
    import sys
    from backend.reset_demo import main

    c = shared(client)
    r = client.post(f"/api/cases/{c['id']}/resolve", json=resolution(client, c))
    assert r.status_code == 200
    invoice = copy.deepcopy(c["invoice"])
    invoice["reference"] = "KEEP-THIS"
    merchant = client.post("/api/invoices/manual", json=invoice).json()
    monkeypatch.setenv("MUNAFA_DB", store.DB_PATH)
    monkeypatch.setattr(sys, "argv", ["reset_demo", "--yes"])
    main()
    cases = client.get("/api/cases").json()
    assert len(cases) == 1 and cases[0]["id"] == merchant["id"]
    assert client.get(f"/api/cases/{c['id']}").status_code == 404
    assert client.post("/api/invoices/sample").status_code == 201
