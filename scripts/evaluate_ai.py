"""Reproducible offline evaluation. No hidden cloud calls or invented human timings.

python scripts/evaluate_ai.py --predictions PRIVATE_JSON --provider NAME --output PATH
Prediction map: case_id -> {draft: PurchaseDraft, latency_ms, billed_cost_paise,
merchant_accepted, task_time_seconds, correction_time_seconds, failed}.
Missing fields/metrics stay null. --baseline uses text-layer parsing, never OCR.
"""

import argparse
import json
import math
import re
import time
from pathlib import Path
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]


def flatten(value, prefix=""):
    if isinstance(value, dict):
        return {
            key: val
            for k, v in value.items()
            for key, val in flatten(v, f"{prefix}.{k}" if prefix else k).items()
        }
    if isinstance(value, list):
        return {
            key: val
            for i, v in enumerate(value)
            for key, val in flatten(v, f"{prefix}[{i}]").items()
        }
    return {prefix: value}


def equivalent(expected, actual, key):
    if "quantity" in key and expected is not None and actual is not None:
        try:
            return Decimal(str(expected)) == Decimal(str(actual))
        except Exception:
            return False
    return type(expected) is type(actual) and expected == actual


def baseline(source):
    fields = dict(re.findall(r"^([^:\n]+): (.*)$", source, re.M))

    def money(k):
        v = fields.get(k, "")
        return int(Decimal(v) * 100) if re.fullmatch(r"\d+\.\d{2}", v) else None

    return {
        "supplier": fields.get("Supplier"),
        "reference": fields.get("Reference"),
        "date": fields.get("Date"),
        "lines": [
            {
                "description": fields.get("Item"),
                "billed_quantity": fields.get("Quantity"),
                "unit": fields.get("Unit"),
                "unit_price_paise": money("Unit price INR"),
            }
        ],
        **{
            k + "_paise": money(name + " INR")
            for k, name in [
                ("subtotal", "Subtotal"),
                ("tax", "Tax"),
                ("discount", "Discount"),
                ("total", "Total"),
            ]
        },
    }


def quantile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)] if values else None


def evaluate(cases, predictions, provider):
    results = []
    for case in cases:
        expected = flatten(case["ground_truth"])
        entry = predictions.get(case["id"])
        actual = flatten(entry.get("draft", {})) if entry else {}
        correct = sum(1 for k, v in expected.items() if equivalent(v, actual.get(k), k))
        # Null GT means explicitly unreadable; evaluate abstention separately.
        known = {k: v for k, v in expected.items() if v is not None}
        tp = sum(1 for k, v in known.items() if equivalent(v, actual.get(k), k))
        emitted = sum(1 for k in expected if actual.get(k) is not None)
        unsupported = sum(
            1
            for k in actual
            if k not in expected
            and k.split(".")[0] not in ("pricing_note", "supplier_phone", "rounding_paise")
        )
        results.append(
            {
                "id": case["id"],
                "split": case["split"],
                "condition": case["condition"],
                "availability": "measured" if entry else "not_measured",
                "fields": len(expected),
                "exact_fields": correct if entry else None,
                "known_fields": len(known),
                "true_positives": tp if entry else None,
                "emitted_known_fields": emitted if entry else None,
                "unsupported_fields": unsupported if entry else None,
                "corrections_needed": len(expected) - correct if entry else None,
                "latency_ms": entry.get("latency_ms") if entry else None,
                "cost_paise": entry.get("billed_cost_paise") if entry else None,
                "merchant_accepted": entry.get("merchant_accepted") if entry else None,
                "correction_adjusted_seconds": entry.get("task_time_seconds", 0)
                + entry.get("correction_time_seconds", 0)
                if entry
                and entry.get("task_time_seconds") is not None
                and entry.get("correction_time_seconds") is not None
                else None,
                "failed": entry.get("failed", False) if entry else None,
            }
        )
    measured = [r for r in results if r["availability"] == "measured"]
    known = sum(r["known_fields"] for r in measured)
    emitted = sum(r["emitted_known_fields"] for r in measured)
    tp = sum(r["true_positives"] for r in measured)
    latencies = [r["latency_ms"] for r in measured if r["latency_ms"] is not None]
    accepted = sum(r["merchant_accepted"] is True for r in measured)
    return {
        "schema_version": 1,
        "provider": provider,
        "synthetic": True,
        "sample_size": len(cases),
        "measured_documents": len(measured),
        "not_measured_documents": len(cases) - len(measured),
        "field_precision": tp / emitted if emitted else None,
        "field_recall": tp / known if known else None,
        "field_exact_match": sum(r["exact_fields"] for r in measured)
        / sum(r["fields"] for r in measured)
        if measured
        else None,
        "field_difference_rate": sum(r["corrections_needed"] for r in measured)
        / sum(r["fields"] for r in measured)
        if measured
        else None,
        "human_correction_rate": None,
        "failure_rate": sum(r["failed"] is True for r in measured) / len(measured)
        if measured
        else None,
        "p50_latency_ms": quantile(latencies, 0.5),
        "p95_latency_ms": quantile(latencies, 0.95),
        "accepted_invoices": accepted,
        "cost_per_accepted_invoice_paise": sum(r["cost_paise"] for r in measured) / accepted
        if accepted and all(r["cost_paise"] is not None for r in measured)
        else None,
        "correction_adjusted_time_seconds": sum(r["correction_adjusted_seconds"] for r in measured)
        / len(measured)
        if measured and all(r["correction_adjusted_seconds"] is not None for r in measured)
        else None,
        "results": results,
        "limitations": [
            "No real merchant data or PII. Synthetic sample does not establish field performance.",
            "No human timing, correction or acceptance measurements are inferred.",
            "Missing provider runs are not counted as successful calls or provider failures.",
            "Text baseline is a fixture format parser, not OCR or an AI provider.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--provider", default="unconfigured-provider")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--split", choices=["all", "calibration", "held_out"], default="all")
    args = parser.parse_args()
    cases = json.loads((ROOT / "evaluation/corpus/invoices.json").read_text())["cases"]
    if args.split != "all":
        cases = [c for c in cases if c["split"] == args.split]
    predictions = json.loads(args.predictions.read_text()) if args.predictions else {}
    if args.baseline:
        predictions = {}
        for case in cases:
            start = time.perf_counter()
            draft = baseline(case["source_text"])
            predictions[case["id"]] = {
                "draft": draft,
                "latency_ms": round((time.perf_counter() - start) * 1000, 4),
            }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evaluate(cases, predictions, args.provider), ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
