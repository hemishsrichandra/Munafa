"""Purchase and stock inputs. Money is paise; quantities are exact six-place strings."""

from datetime import date
from typing import Literal
from pydantic import Field
from .domain import StrictModel, Quantity

Unit = Literal["pack", "piece", "carton", "kg"]
Money = int


class PurchaseLine(StrictModel):
    description: str = Field(default="", max_length=120)
    sku_candidate: str | None = Field(default=None, max_length=120)
    product_id: str | None = Field(default=None, max_length=64)
    billed_quantity: Quantity | None = Field(default=None, gt=0, le=100000)
    unit: Unit | None = None
    unit_price_paise: int | None = Field(default=None, gt=0, le=100000000, strict=True)
    effective_price_paise: int | None = Field(default=None, gt=0, le=100000000, strict=True)
    tax_paise: int | None = Field(default=None, ge=0, le=10000000000, strict=True)
    tax_rate: Quantity | None = Field(default=None, ge=0, le=100)
    discount_paise: int | None = Field(default=None, ge=0, le=10000000000, strict=True)
    confidence: float | None = Field(default=None, ge=0, le=1)
    review_note: str = Field(default="", max_length=300)


class PurchaseDraft(StrictModel):
    supplier: str = Field(default="", max_length=100)
    supplier_phone: str = Field(default="", max_length=16, pattern=r"^\+?[0-9]{0,15}$")
    reference: str = Field(default="", max_length=60)
    date: str = Field(default="", max_length=10)
    lines: list[PurchaseLine] = Field(
        default_factory=lambda: [PurchaseLine()], min_length=1, max_length=30
    )
    subtotal_paise: int | None = Field(default=None, ge=0, le=300000000000000, strict=True)
    tax_paise: int | None = Field(default=None, ge=0, le=300000000000000, strict=True)
    discount_paise: int | None = Field(default=None, ge=0, le=300000000000000, strict=True)
    rounding_paise: int = Field(default=0, ge=-10000, le=10000, strict=True)
    total_paise: int | None = Field(default=None, ge=0, le=300000000000000, strict=True)
    pricing_note: str = Field(default="", max_length=500)


class ProductInput(StrictModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    unit: Unit
    barcode: str | None = Field(default=None, min_length=1, max_length=80)
    reorder_threshold: Quantity | None = Field(default=None, ge=0, le=100000000)
    expiry_tracking: bool = False


class ConversionInput(StrictModel):
    from_unit: Unit
    to_unit: Unit
    factor: Quantity = Field(gt=0, le=100000)
    provenance: str = Field(min_length=3, max_length=300)


class ReceivingLine(StrictModel):
    purchase_line_id: str = Field(min_length=1, max_length=64)
    quantity: Quantity | None = Field(default=None, ge=0, le=100000)
    damaged_quantity: Quantity = Field(default=0, ge=0, le=100000)
    unit: Unit
    unit_confirmed: bool = False
    note: str = Field(default="", max_length=500)
    batch_reference: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None


class ReceivingDraft(StrictModel):
    purchase_version: int = Field(ge=1, strict=True)
    lines: list[ReceivingLine] = Field(min_length=1, max_length=30)
    delivery_complete: bool = False
    pricing_confirmed: bool = False
    note: str = Field(default="", max_length=500)
    received_on: date | None = None


class MovementInput(StrictModel):
    product_id: str = Field(min_length=1, max_length=64)
    expected_stock_version: int = Field(ge=0, strict=True)
    kind: Literal[
        "count", "sale", "return_in", "return_out", "damage", "reversal", "shortage_correction"
    ]
    quantity: Quantity = Field(ge=0, le=100000000)
    unit: Unit
    reference: str = Field(min_length=1, max_length=100)
    occurred_on: date
    reason: str = Field(min_length=3, max_length=500)
    lot_id: str | None = Field(default=None, max_length=64)
    batch_reference: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None
    reversal_of: str | None = Field(default=None, max_length=64)
    case_id: str | None = Field(default=None, max_length=64)
