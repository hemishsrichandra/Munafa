"""Bounded Sarvam-only synthetic benchmark. Raw outputs stay in ignored private storage.

No real documents, DB writes, human-time claims or inferred billable costs. This
requires explicit paid-call opt-in even with a configured server key.
"""

import argparse
import hashlib
import json
import math
import struct
import sys
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_ai import flatten, equivalent  # noqa: E402 — direct CLI root setup


class Pricing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model: str
    source_url: str
    verified_on: str
    input_rupees_per_million: Decimal = Field(gt=0)
    output_rupees_per_million: Decimal = Field(gt=0)
    excludes_gst: bool


def read_cases(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    value = json.loads(manifest_path.read_text())
    if value.get("mode") != "synthetic" or value.get("schema_version") != 2:
        raise ValueError(
            "This approved runner accepts only explicitly labelled synthetic v2 cases. Real-data runs require a separate consented protocol."
        )
    ids = set()
    for case in value["cases"]:
        if case["id"] in ids or case.get("evidence_class") != "owned_programmatic_synthetic":
            raise ValueError("Duplicate ID or unsupported document provenance")
        ids.add(case["id"])
        image = (manifest_path.parent / case["image"]).resolve()
        if not image.is_relative_to(manifest_path.parent) or image.suffix != ".png":
            raise ValueError("Only corpus-local PNG files are allowed")
        data = image.read_bytes()
        if len(data) > 512 * 1024 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid/oversized synthetic PNG")
        width, height = struct.unpack(">II", data[16:24])
        if width * height > 1000000:
            raise ValueError("Synthetic image pixel budget exceeded")
        case["image_path"] = str(image)
        case["sha256"] = hashlib.sha256(data).hexdigest()
    return value


def projection(draft):
    return {
        key: draft.get(key)
        for key in (
            "supplier",
            "reference",
            "date",
            "subtotal_paise",
            "tax_paise",
            "discount_paise",
            "total_paise",
        )
    } | {
        "lines": [
            {
                key: row.get(key)
                for key in ("description", "billed_quantity", "unit", "unit_price_paise")
            }
            for row in draft.get("lines", [])
        ]
    }


def normalize(value):
    if isinstance(value, str):
        return " ".join(unicodedata.normalize("NFC", value).split())
    return value


def estimate_paise(usage, pricing):
    if (
        type(usage.get("prompt_tokens")) is not int
        or type(usage.get("completion_tokens")) is not int
        or min(usage["prompt_tokens"], usage["completion_tokens"]) < 0
    ):
        return None
    # Reported API counters, not LLM-generated amounts. Ignore cache discounts conservatively.
    value = (
        (
            Decimal(usage["prompt_tokens"]) * pricing.input_rupees_per_million
            + Decimal(usage["completion_tokens"]) * pricing.output_rupees_per_million
        )
        * 100
        / Decimal(1000000)
    )
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def score(cases, results):
    fields = {}
    scored = []
    for case in cases:
        result = results.get(case["id"])
        if result is None:
            scored.append(
                {
                    "id": case["id"],
                    "condition": case["condition"],
                    "language": case["language"],
                    "status": "not_measured",
                }
            )
            continue
        expected = flatten(case["ground_truth"])
        actual = flatten(projection(result["draft"]))
        wrong = []
        unexpected = [
            key for key, value in actual.items() if key not in expected and value not in (None, "")
        ]
        for name, value in expected.items():
            match = equivalent(normalize(value), normalize(actual.get(name)), name)
            metric = fields.setdefault(name, {"correct": 0, "reviewed": 0})
            metric["reviewed"] += 1
            metric["correct"] += int(match)
            if not match:
                wrong.append(name)
        scored.append(
            {
                "id": case["id"],
                "condition": case["condition"],
                "language": case["language"],
                "status": result["status"],
                "fields": len(expected),
                "exact_fields": len(expected) - len(wrong),
                "fields_needing_correction": wrong,
                "unexpected_fields": unexpected,
                "emitted_fields": sum(value not in (None, "") for value in actual.values()),
                "latency_ms": result["latency_ms"],
                "usage_estimate_paise_excluding_gst": result["usage_estimate_paise_excluding_gst"],
                "human_correction_time_ms": None,
                "merchant_accepted": None,
                "real_handwriting": False,
            }
        )
    measured = [r for r in scored if r["status"] != "not_measured"]
    times = sorted(r["latency_ms"] for r in measured)

    def percentile(q):
        return times[max(0, math.ceil(len(times) * q) - 1)] if times else None

    total = sum(v["reviewed"] for v in fields.values())
    return {
        "schema_version": 2,
        "synthetic": True,
        "sample_size": len(cases),
        "measured_documents": len(measured),
        "field_exact_match": sum(v["correct"] for v in fields.values()) / total if total else None,
        "field_metrics": fields,
        "field_recall": sum(v["correct"] for v in fields.values()) / total if total else None,
        "field_precision": sum(v["correct"] for v in fields.values())
        / sum(r["emitted_fields"] for r in measured)
        if sum(r["emitted_fields"] for r in measured)
        else None,
        "field_difference_rate": sum(len(r["fields_needing_correction"]) for r in measured) / total
        if total
        else None,
        "failure_rate": sum(r["status"] != "valid" for r in measured) / len(measured)
        if measured
        else None,
        "p50_latency_ms": percentile(0.5),
        "p95_latency_ms": percentile(0.95),
        "usage_estimate_paise_excluding_gst": sum(
            r["usage_estimate_paise_excluding_gst"] for r in measured
        )
        if measured and all(r["usage_estimate_paise_excluding_gst"] is not None for r in measured)
        else None,
        "verified_billed_cost_paise": None,
        "cost_per_accepted_invoice_paise": None,
        "human_correction_rate": None,
        "correction_adjusted_task_time_ms": None,
        "actual_merchant_pilot": False,
        "results": scored,
        "limitations": [
            "Five controlled synthetic layouts are not a representative real-invoice sample.",
            "Thermal/handwriting typography proxies are not actual thermal photographs or handwritten invoices.",
            "Field errors versus programmatic ground truth are not observed human corrections or timing.",
            "No merchant acceptances, human correction time, verified billing or real pilot are measured.",
        ],
    }


def run_cases(
    manifest_path, pricing, output, budget_paise, max_documents, allow_paid=False, call=None
):
    from backend import ai
    from backend.providers import SarvamDocument
    import os

    corpus = read_cases(manifest_path)
    if not allow_paid:
        raise ValueError("Explicit --allow-paid-calls is required")
    if not 1 <= max_documents <= 5 or not 200 <= budget_paise <= 1000:
        raise ValueError("Approved maximum: five images and 1000 paise reserved budget")
    if (
        pricing.provider != "sarvam"
        or pricing.model != "gemma4"
        or os.getenv("SARVAM_VISION_MODEL", "gemma4") != pricing.model
    ):
        raise ValueError("This approval/pricing snapshot covers Sarvam-hosted gemma4 only")
    if call is None and not ai.configured():
        raise ValueError("Server-side Sarvam key is unavailable; no calls made")
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "evaluation/private").resolve()):
        raise ValueError("Raw evaluation outputs must remain in ignored evaluation/private")
    # Refuse a second run in the same directory, including after a crash. Spending
    # cannot be retried merely by rerunning this command.
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    call = call or SarvamDocument().extract
    results = {}
    reserved = 0
    stop = None
    for case in corpus["cases"][:max_documents]:
        if reserved + 200 > budget_paise:
            stop = "Authorised reservation budget exhausted"
            break
        reserved += 200
        (output / "reservation.json").write_text(
            json.dumps({"reserved_paise": reserved, "attempted_case": case["id"]})
        )
        (output / "reservation.json").chmod(0o600)
        start = time.monotonic()
        try:
            draft, meta = call(data=Path(case["image_path"]).read_bytes(), mime="image/png")
        except Exception:
            draft, meta = {}, {"failure_kind": "provider_error"}
        estimate = estimate_paise(meta.get("provider_reported_usage", {}), pricing)
        status = (
            "invalid"
            if meta.get("failure_kind") == "invalid"
            else "provider_error"
            if meta.get("failure_kind") or meta.get("warning")
            else "valid"
        )
        results[case["id"]] = {
            "draft": draft,
            "status": status,
            "latency_ms": int((time.monotonic() - start) * 1000),
            "source_sha256": case["sha256"],
            "usage": meta.get("provider_reported_usage", {}),
            "usage_estimate_paise_excluding_gst": estimate,
            "provider_metadata": meta,
        }
        (output / "responses.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n"
        )
        (output / "responses.json").chmod(0o600)
        # Unknown usage/billing is never assumed free; stop rather than retry/spend blindly.
        if estimate is None or estimate > 200:
            stop = "Usage unavailable or exceeded conservative reservation; further calls stopped"
            break
    report = score(corpus["cases"], results)
    report.update(
        provider="sarvam",
        model=pricing.model,
        pricing=pricing.model_dump(mode="json"),
        created_at=datetime.now(timezone.utc).isoformat(),
        reserved_budget_paise=reserved,
        authorised_budget_paise=budget_paise,
        stop_reason=stop,
        accepted_invoices=0,
        request_retries=0,
    )
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (output / "report.json").chmod(0o600)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "evaluation/validation-v2/manifest.json"))
    parser.add_argument(
        "--pricing", default=str(ROOT / "evaluation/validation-v2/pricing-snapshot.json")
    )
    parser.add_argument("--output", default=str(ROOT / "evaluation/private/validation-v2"))
    parser.add_argument("--budget-paise", type=int, default=1000)
    parser.add_argument("--max-documents", type=int, default=5)
    parser.add_argument("--allow-paid-calls", action="store_true")
    args = parser.parse_args()
    try:
        report = run_cases(
            args.manifest,
            Pricing.model_validate_json(Path(args.pricing).read_text()),
            args.output,
            args.budget_paise,
            args.max_documents,
            args.allow_paid_calls,
        )
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "measured_documents",
                        "sample_size",
                        "field_exact_match",
                        "p50_latency_ms",
                        "p95_latency_ms",
                        "usage_estimate_paise_excluding_gst",
                        "verified_billed_cost_paise",
                        "stop_reason",
                    )
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "detail": "Evaluation stopped. Inspect private configuration/results; no success or zero cost is inferred.",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
