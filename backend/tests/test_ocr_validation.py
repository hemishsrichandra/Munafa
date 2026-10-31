"""No paid providers or real documents. Test evaluation evidence and fallback boundaries."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from backend import purchase_extraction as extraction
from backend.pdf_text import text_pages
from backend.tests.test_assistant import mock_chat
from scripts import ocr_benchmark as bench

ROOT = Path(__file__).resolve().parents[2]


def pricing():
    return bench.Pricing.model_validate_json(
        (ROOT / "evaluation/validation-v2/pricing-snapshot.json").read_text()
    )


def test_pdf_bounded_text_never_silently_drops_pages_or_characters(monkeypatch):
    reader = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: "x" * 18001)])
    result = text_pages(reader)
    assert result["truncated"] and not result["text_complete"]
    assert len(result["pages"][0]["text"]) == 18000
    reader.pages = [
        SimpleNamespace(extract_text=lambda: "x" * 18000),
        SimpleNamespace(extract_text=lambda: "last"),
    ]
    assert text_pages(reader)["truncated"]
    reader.pages = [SimpleNamespace(extract_text=lambda: "x" * 18000)]
    assert text_pages(reader)["text_complete"]
    monkeypatch.setattr(extraction, "pdf_text", lambda data: result)
    monkeypatch.setattr(
        extraction.ai, "post", lambda *a: pytest.fail("Incomplete PDF must not call cloud")
    )
    draft, meta = extraction._extract_once(data=b"synthetic", mime="application/pdf")
    assert meta["manual_required"] and meta["truncated"]
    assert not draft["supplier"] and draft["total_paise"] is None


def test_invalid_output_preserves_sanitized_usage_for_failure_cost(client, monkeypatch):
    mock_chat(monkeypatch, {"received_quantity": "10"})
    _, meta = extraction._extract_once(text="synthetic untrusted invoice")
    assert meta["failure_kind"] == "invalid"
    assert meta["provider_reported_usage"] == {"total_tokens": 123}
    assert "secret" not in meta["provider_reported_usage"]


def test_synthetic_score_does_not_invent_human_results_or_billed_cost():
    corpus = bench.read_cases(ROOT / "evaluation/validation-v2/manifest.json")
    cases = corpus["cases"]
    draft = copy.deepcopy(cases[0]["ground_truth"])
    draft["lines"][0]["billed_quantity"] = "2.500"
    report = bench.score(
        cases,
        {
            cases[0]["id"]: {
                "draft": draft,
                "status": "valid",
                "latency_ms": 42,
                "usage_estimate_paise_excluding_gst": 1,
            }
        },
    )
    assert report["measured_documents"] == 1 and report["field_exact_match"] == 1
    for key in (
        "human_correction_rate",
        "correction_adjusted_task_time_ms",
        "verified_billed_cost_paise",
        "cost_per_accepted_invoice_paise",
    ):
        assert report[key] is None
    draft["total_paise"] = 3
    result = bench.score(
        cases[:1],
        {
            cases[0]["id"]: {
                "draft": draft,
                "status": "valid",
                "latency_ms": 42,
                "usage_estimate_paise_excluding_gst": None,
            }
        },
    )
    assert result["results"][0]["fields_needing_correction"] == ["total_paise"]
    assert result["usage_estimate_paise_excluding_gst"] is None
    draft["lines"].append(copy.deepcopy(draft["lines"][0]))
    extra = bench.score(
        cases[:1],
        {
            cases[0]["id"]: {
                "draft": draft,
                "status": "valid",
                "latency_ms": 1,
                "usage_estimate_paise_excluding_gst": None,
            }
        },
    )
    assert extra["results"][0]["unexpected_fields"]
    assert extra["field_precision"] < extra["field_recall"]


def test_runner_requires_explicit_budget_optin_and_never_retries(tmp_path, monkeypatch):
    # Redirect only test output, never write into a user's benchmark directory.
    monkeypatch.setattr(bench, "ROOT", tmp_path)
    manifest = ROOT / "evaluation/validation-v2/manifest.json"
    calls = []

    def call(**kw):
        calls.append(kw)
        return {}, {"failure_kind": "invalid", "provider_reported_usage": {}}

    output = tmp_path / "evaluation/private/run"
    with pytest.raises(ValueError, match="allow-paid"):
        bench.run_cases(manifest, pricing(), output, 1000, 5, call=call)
    with pytest.raises(ValueError, match="maximum"):
        bench.run_cases(manifest, pricing(), output, 1001, 5, True, call)
    assert not calls
    report = bench.run_cases(manifest, pricing(), output, 1000, 5, True, call)
    assert len(calls) == 1 and report["stop_reason"] and report["request_retries"] == 0
    assert report["failure_rate"] == 1 and report["reserved_budget_paise"] == 200
    with pytest.raises(FileExistsError):
        bench.run_cases(manifest, pricing(), output, 1000, 5, True, call)
    assert len(calls) == 1
    assert (output / "responses.json").stat().st_mode & 0o777 == 0o600


def test_manifest_rejects_real_or_external_source_and_usage_validation(tmp_path):
    value = {"mode": "live", "schema_version": 2, "cases": []}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="synthetic"):
        bench.read_cases(path)
    value.update(
        mode="synthetic",
        cases=[
            {"id": "x", "image": "../private.png", "evidence_class": "owned_programmatic_synthetic"}
        ],
    )
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="corpus-local"):
        bench.read_cases(path)
    assert (
        bench.estimate_paise({"prompt_tokens": 1000000, "completion_tokens": 1000000}, pricing())
        == 12500
    )
    assert bench.estimate_paise({"prompt_tokens": True, "completion_tokens": 1}, pricing()) is None
    assert bench.estimate_paise({"prompt_tokens": -1, "completion_tokens": 1}, pricing()) is None
