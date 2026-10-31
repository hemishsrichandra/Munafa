"""Read-only documented supplier outcomes; no inferred supplier reliability score."""

from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter
from sqlalchemy import select
from . import models as m, store
from .domain import normalized, present

router = APIRouter(prefix="/api/supplier-performance")


def elapsed(start, end):
    return round(
        max(0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
        / 3600,
        2,
    )


@router.get("")
def report():
    with store.connect() as db:
        damage = {}
        query = (
            select(
                m.purchases.c.case_id,
                m.receipt_lines.c.damaged_quantity,
                m.receipt_lines.c.unit,
                m.receipt_lines.c.receipt_id,
            )
            .select_from(
                m.receipt_lines.join(
                    m.receipts,
                    (m.receipt_lines.c.receipt_id == m.receipts.c.id)
                    & (m.receipt_lines.c.store_id == m.receipts.c.store_id),
                ).join(
                    m.purchases,
                    (m.receipts.c.purchase_id == m.purchases.c.id)
                    & (m.receipts.c.store_id == m.purchases.c.store_id),
                )
            )
            .where(store.scope(m.receipt_lines), store.scope(m.receipts), store.scope(m.purchases))
        )
        for r in db.execute(query).mappings():
            if r["case_id"] and r["damaged_quantity"] > 0:
                damage.setdefault(r["case_id"], []).append(
                    {
                        "quantity": str(r["damaged_quantity"]),
                        "unit": r["unit"],
                        "receipt_id": r["receipt_id"],
                    }
                )
        groups = {}
        for raw in store.all_cases(db):
            c = present(raw)
            key = normalized(c["invoice"]["supplier"])
            group = groups.setdefault(key, {"supplier": c["invoice"]["supplier"], "cases": []})
            approved = c["approved_version"] is not None
            shortages = []
            if approved:
                for line in c["invoice"]["lines"]:
                    if (
                        line["received"] is not None
                        and line["unit_confirmed"]
                        and line["unit"] == line["received_unit"]
                    ):
                        missing = Decimal(str(line["billed"])) - Decimal(str(line["received"]))
                        if missing > 0:
                            shortages.append(
                                {
                                    "product": line["name"],
                                    "quantity": str(missing),
                                    "unit": line["unit"],
                                }
                            )
            resolutions = sorted(c["resolutions"], key=lambda r: r["at"])
            group["cases"].append(
                {
                    "case_id": c["id"],
                    "reference": c["invoice"]["reference"],
                    "approved": approved,
                    "status": c["status"],
                    "shortages": shortages,
                    "damage": damage.get(c["id"], []),
                    "remaining_paise": c["remaining_paise"] if approved else None,
                    "recovered_paise": c["recovered_paise"],
                    "first_recovery_hours": elapsed(c["created_at"], resolutions[0]["at"])
                    if resolutions
                    else None,
                    "full_recovery_hours": elapsed(c["created_at"], resolutions[-1]["at"])
                    if resolutions and c["status"] == "resolved"
                    else None,
                }
            )
        return {
            "suppliers": list(groups.values()),
            "coverage": "Tracked recovery cases only. Approved missing/unusable quantities may include damage; do not add them to receipt damage. Units are kept separate. Recovery time starts at case creation. No delivery punctuality or reliability score is inferred.",
        }
