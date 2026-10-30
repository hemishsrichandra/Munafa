from .domain import Invoice
from . import store

SAMPLE = {
    "supplier": "Shree Ganesh Distributors",
    "supplier_phone": "",
    "reference": "A-104",
    "date": "2026-10-29",
    "pricing_note": "Synthetic invoice. Net unit prices; no additional tax, discount or scheme.",
    "lines": [
        {"name": "Parle-G biscuits", "billed": 12, "unit": "pack", "price_paise": 4000},
        {"name": "Tata Tea 250 g", "billed": 6, "unit": "pack", "price_paise": 12500},
        {
            "name": "Lifebuoy soap",
            "billed": 24,
            "unit": "unknown",
            "price_paise": 3500,
            "note": "Unit on bill is unclear. Confirm with the supplier.",
        },
    ],
}


def sample_invoice():
    return Invoice.model_validate(SAMPLE).model_dump()


def demo_seed():
    """Explicit per-store fixture creation. Never runs on startup or touches live stores."""
    from .auth import current
    from .domain import RuleError

    if not current("admin").demo:
        raise RuleError("Seeding is restricted to an isolated demo store.")
    if store.all_cases():
        return
    from .app import sample

    sample()
