"""Only printed billed fields are accepted from models; authority fields are forbidden."""

from pydantic import BaseModel, ConfigDict, StrictStr, Field


class RawLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: StrictStr | None = None
    sku_candidate: StrictStr | None = None
    quantity: StrictStr | None = None
    unit: StrictStr | None = None
    unit_price: StrictStr | None = None
    tax: StrictStr | None = None
    tax_rate: StrictStr | None = None
    discount: StrictStr | None = None
    review_note: StrictStr | None = None


class RawInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier: StrictStr | None = None
    supplier_phone: StrictStr | None = None
    reference: StrictStr | None = None
    date: StrictStr | None = None
    subtotal: StrictStr | None = None
    tax: StrictStr | None = None
    discount: StrictStr | None = None
    rounding: StrictStr | None = None
    total: StrictStr | None = None
    lines: list[RawLine] = Field(min_length=1, max_length=30)
