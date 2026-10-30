"""Money and state rules. Models never decide claim or recovery amounts."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from copy import deepcopy
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, PlainSerializer
from typing import Annotated
from decimal import Decimal, ROUND_HALF_UP


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def exact_quantity(value):
    if isinstance(value, (float, bool)):
        raise ValueError(
            "Use an integer or decimal string; binary floating quantities are not accepted."
        )
    quantity = Decimal(str(value))
    if not quantity.is_finite() or quantity.as_tuple().exponent < -6:
        raise ValueError("Quantities support at most six decimal places.")
    return quantity


Quantity = Annotated[
    Decimal,
    BeforeValidator(exact_quantity),
    PlainSerializer(lambda q: int(q) if q == q.to_integral() else str(q)),
]


class Line(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    billed: Quantity = Field(gt=0, le=100000)
    unit: Literal["pack", "piece", "carton", "kg", "unknown"] = "unknown"
    price_paise: int = Field(ge=1, le=100000000, strict=True)
    received: Quantity | None = Field(default=None, ge=0, le=100000)
    received_unit: Literal["pack", "piece", "carton", "kg", "unknown"] = "unknown"
    unit_confirmed: bool = False
    note: str = Field(default="", max_length=300)


class Invoice(StrictModel):
    supplier: str = Field(min_length=1, max_length=100)
    supplier_phone: str = Field(default="", max_length=16, pattern=r"^\+?[0-9]{0,15}$")
    reference: str = Field(min_length=1, max_length=60)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    lines: list[Line] = Field(min_length=1, max_length=30)
    pricing_note: str = Field(
        default="Verify the effective unit price after any tax, discount or scheme.", max_length=500
    )


class Review(StrictModel):
    version: int
    invoice: Invoice
    delivery_complete: bool
    pricing_confirmed: bool


class Version(StrictModel):
    version: int


class Sent(Version):
    confirmed: bool


class Promise(Version):
    note: str = Field(min_length=1, max_length=500)
    follow_up: str


class Resolution(Version):
    kind: Literal["credit", "refund"]
    supplier: str = Field(min_length=1, max_length=100)
    invoice_reference: str = Field(min_length=1, max_length=60)
    evidence_reference: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=0, le=100000000, strict=True)
    attachment_id: str
    applied_confirmed: bool


class RuleError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def local_today():
    from .auth import principal

    p = principal.get()
    return datetime.now(ZoneInfo(p.timezone if p else "Asia/Kolkata")).date()


def normalized(s):
    return " ".join(s.casefold().split())


def calculate(lines, complete, pricing):
    issues, total, details = [], 0, []
    if not complete:
        issues.append("Confirm that the delivery is complete.")
    if not pricing:
        issues.append("Verify effective prices, including taxes, discounts and schemes.")
    for i, line in enumerate(lines):
        if isinstance(line, BaseModel):
            line = line.model_dump()
        line = dict(line)
        line["billed"] = Decimal(str(line["billed"]))
        if line["received"] is not None:
            line["received"] = Decimal(str(line["received"]))
        reason = None
        if line["received"] is None:
            reason = "Enter the quantity received."
        elif line["received"] > line["billed"]:
            reason = "Over-deliveries need a separate review; this prototype handles shortages."
        elif (
            line["unit"] == "unknown"
            or line["received_unit"] != line["unit"]
            or not line["unit_confirmed"]
        ):
            reason = (
                "Confirm matching billed and received units. No carton conversions are inferred."
            )
        if reason:
            issues.append(f"{line['name']}: {reason}")
        amount = (
            int(
                ((line["billed"] - line["received"]) * line["price_paise"]).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            if not reason
            else 0
        )
        details.append(
            {
                "index": i,
                "amount_paise": amount,
                "issue": reason,
                "shortage_quantity": str(line["billed"] - line["received"])
                if line["received"] is not None
                else None,
            }
        )
        total += amount
    return {
        "amount_paise": total,
        "issues": issues,
        "lines": details,
        "eligible": not issues and total > 0,
    }


def audit(case, action, detail, snapshot=None):
    event = {"at": now(), "action": action, "detail": detail}
    if snapshot is not None:
        event["snapshot"] = deepcopy(snapshot)
    case["history"].append(event)


def new_case(invoice, case_id, synthetic=False, attachment_id=None):
    return {
        "id": case_id,
        "invoice": invoice,
        "synthetic": synthetic,
        "attachment_id": attachment_id,
        "version": 1,
        "created_at": now(),
        "status": "review",
        "delivery_complete": False,
        "pricing_confirmed": False,
        "approved_version": None,
        "approved_amount_paise": None,
        "follow_up": None,
        "promise": None,
        "resolutions": [],
        "history": [
            {
                "at": now(),
                "action": "Invoice added",
                "detail": "Synthetic example"
                if synthetic
                else "Merchant invoice; extraction requires review",
            }
        ],
    }


def present(case):
    calc = calculate(case["invoice"]["lines"], case["delivery_complete"], case["pricing_confirmed"])
    recovered = sum(r["amount_paise"] for r in case["resolutions"])
    return {
        **case,
        "calculation": calc,
        "recovered_paise": recovered,
        "remaining_paise": max(
            0, (case["approved_amount_paise"] or calc["amount_paise"]) - recovered
        ),
    }


def rupees(paise):
    return format(Decimal(paise) / Decimal(100), ".2f")
