"""Owned synthetic OCR cases. Typography/thermal proxies are not field photographs."""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evaluation" / "validation-v2"


def build(folder=FOLDER):
    folder.mkdir(parents=True, exist_ok=True)
    inputs = [
        (
            "printed-en",
            "printed_synthetic",
            "en",
            "Synthetic Kirana Wholesale",
            "Rice",
            False,
            False,
        ),
        (
            "thermal-en",
            "thermal_typography_proxy",
            "en",
            "Synthetic Kirana Wholesale",
            "Tea",
            True,
            False,
        ),
        (
            "handwriting-proxy",
            "handwriting_typography_proxy",
            "en",
            "Synthetic Kirana Wholesale",
            "Sugar",
            False,
            True,
        ),
        ("printed-hi", "printed_synthetic", "hi", "सिंथेटिक किराना", "चावल", False, False),
        ("printed-kn", "printed_synthetic", "kn", "ಸಿಂಥೆಟಿಕ್ ಕಿರಾಣಿ", "ಅಕ್ಕಿ", False, False),
    ]
    cases = []
    for identifier, condition, language, supplier, item, thermal, handwriting in inputs:
        reference = "SYN-" + identifier.upper()
        text = [
            supplier,
            "SYNTHETIC TEST — NOT A REAL BILL",
            f"Reference: {reference}",
            "Date: 2026-10-31",
            "Item / वस्तु / ವಸ್ತು: " + item if language != "en" else "Item: " + item,
            "Quantity: 2.5 kg",
            "Unit price INR: 80.00",
            "Subtotal INR: 200.00",
            "Tax INR: 0.00",
            "Discount INR: 0.00",
            "Total INR: 200.00",
            "No delivery or payment is confirmed.",
        ]
        family = (
            "'Bradley Hand','Comic Sans MS',cursive"
            if handwriting
            else "monospace"
            if thermal
            else "'Kohinoor Devanagari','Kannada Sangam MN','Noto Sans Devanagari','Noto Sans Kannada',sans-serif"
        )
        colour = "#777" if thermal else "#18221b"
        transform = 'transform="rotate(-1 320 380)"' if handwriting else ""
        rows = "".join(
            f'<text x="35" y="{65 + i * 50}" font-size="{24 if i == 0 else 18}">{html.escape(line)}</text>'
            for i, line in enumerate(text)
        )
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="700"><rect width="640" height="700" fill="{"#eee" if thermal else "white"}"/><g {transform} fill="{colour}" font-family="{html.escape(family, quote=True)}">{rows}</g></svg>'
        (folder / (identifier + ".svg")).write_text(svg)
        gt = {
            "supplier": supplier,
            "reference": reference,
            "date": "2026-10-31",
            "lines": [
                {
                    "description": item,
                    "billed_quantity": "2.5",
                    "unit": "kg",
                    "unit_price_paise": 8000,
                }
            ],
            "subtotal_paise": 20000,
            "tax_paise": 0,
            "discount_paise": 0,
            "total_paise": 20000,
        }
        cases.append(
            {
                "id": identifier,
                "split": "held_out",
                "condition": condition,
                "language": language,
                "image": identifier + ".png",
                "ground_truth": gt,
                "evidence_class": "owned_programmatic_synthetic",
                "independently_adjudicated": False,
                "real_handwriting": False,
            }
        )
    manifest = {
        "schema_version": 2,
        "mode": "synthetic",
        "source": "project-owned generated text, not merchant documents",
        "consent_required_for_real_data": True,
        "human_review_observations": 0,
        "cases": cases,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"synthetic_cases": len(cases), "real_documents": 0, "human_reviews": 0}))


if __name__ == "__main__":
    build()
