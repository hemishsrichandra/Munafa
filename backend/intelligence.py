"""Store-scoped readiness; observed events are not complete sales coverage."""

from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import select, func
from . import auth, inventory, models as m, store

router = APIRouter(prefix="/api/intelligence")


@router.get("/readiness")
def readiness():
    p = auth.current()
    with store.connect() as db:
        products = list(
            db.execute(
                select(m.products)
                .where(store.scope(m.products))
                .order_by(m.products.c.id)
                .limit(101)
            ).mappings()
        )
        result = []
        for product in products[:100]:
            counts = dict(
                db.execute(
                    select(m.inventory_events.c.kind, func.count())
                    .where(
                        store.scope(m.inventory_events),
                        m.inventory_events.c.product_id == product["id"],
                    )
                    .group_by(m.inventory_events.c.kind)
                ).all()
            )
            first, last, observed_periods = db.execute(
                select(
                    func.min(m.inventory_sources.c.occurred_on),
                    func.max(m.inventory_sources.c.occurred_on),
                    func.count(func.distinct(m.inventory_sources.c.occurred_on)),
                ).where(
                    store.scope(m.inventory_sources),
                    m.inventory_sources.c.product_id == product["id"],
                    m.inventory_sources.c.source_type == "sale",
                )
            ).one()
            result.append(
                {
                    "product_id": product["id"],
                    "name": product["name"],
                    "unit": product["unit"],
                    "stock_version": product["stock_version"],
                    "route": "/stock/" + product["id"],
                    "event_counts": counts,
                    "observed_sales_period": {
                        "first": first,
                        "last": last,
                        "distinct_days": observed_periods,
                    },
                    "complete_sales_coverage": False,
                    "missing_intervals": None,
                    "stockout_periods": None,
                    "unit_policy": "Only recorded SKU units and explicit merchant conversions; no inferred conversion.",
                    "source_confidence": "Accepted ledger events; completeness of sales/depletion reporting is unverified.",
                    "forecast_enabled": False,
                    "status": "DATA NOT READY",
                    "reasons": (
                        [] if counts.get("sale") else ["No accepted SKU-level sale events."]
                    )
                    + [
                        "No verified observation calendar distinguishes zero sales from unrecorded intervals.",
                        "No reviewed per-SKU evaluation plan, lead-time assumptions or time-held-out baseline comparison.",
                    ],
                    "simple_rule": {
                        "kind": "merchant_reorder_threshold",
                        "threshold": inventory.quantity(product["reorder_threshold"])
                        if product["reorder_threshold"] is not None
                        else None,
                        "is_forecast": False,
                    },
                }
            )
    return {
        "mode": "demo" if p.demo else "live",
        "queried_at": datetime.now(timezone.utc),
        "products": result,
        "truncated": len(products) > 100,
        "coverage": "First 100 catalogue records only"
        if len(products) > 100
        else "All current store catalogue records",
        "evaluation_policy": {
            "version": "readiness-v1",
            "minimum_history": None,
            "reason": "No reviewed evaluation plan configured. No universal day threshold can enable forecasts.",
        },
        "benchmark": {
            "status": "BLOCKED — LEGAL/CONSENT",
            "suppressed": True,
            "cohort_size": None,
            "reason": "No consented comparable cohort, privacy policy or re-identification review.",
        },
        "pilot": {"status": "PILOT NOT RUN", "measured_outcomes": None},
    }
