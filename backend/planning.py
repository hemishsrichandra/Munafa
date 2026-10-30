"""P2 readiness only. Missing proven foundations cannot be enabled by a flag or client claim.

No order, cashflow, lender application, cohort or external-execution model exists in
this repository. The explicit gates below describe that fact, rather than accepting
unsupported inputs as verified sources. No P1 implementation is smuggled in here.
"""

import os
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import select, func
from . import auth, store, models as m, inventory
from .commerce_models import Unit
from .domain import StrictModel

router = APIRouter(prefix="/api/planning")
Capability = Literal["procurement", "financial_planning", "benchmarking"]
INTENTS = {
    "procurement": {"purchase_order_draft"},
    "financial_planning": {"financial_summary", "lender_checklist"},
    "benchmarking": {"within_store_history", "peer_comparison"},
}
CONFIG = {
    "procurement": ("ENABLE_P2_PROCUREMENT", "Procurement assistant", "financial_commitment"),
    "financial_planning": (
        "ENABLE_P2_FINANCIAL_PLANNING",
        "Financial planning & document readiness",
        "sensitive_financial_data",
    ),
    "benchmarking": ("ENABLE_P2_BENCHMARKING", "Benchmarking & growth coach", "reidentification"),
}

# Implementation evidence, not merchant performance/quality scores. Turning on
# configuration cannot create an offer registry, regulated process or cohort policy.
BLOCKERS = {
    "procurement": [
        (
            "p1_quality_unproven",
            "Relevant P1 data quality and procurement evaluation have not been proven.",
        ),
        (
            "verified_offers_absent",
            "No documented, permissioned, current supplier price/availability registry exists. Historical invoice prices are not offers.",
        ),
        (
            "order_lifecycle_absent",
            "No purchase-order state machine, duplicate guard, cancellation or supplier confirmation contract exists.",
        ),
        (
            "external_execution_disabled",
            "Supplier communication, order placement, terms acceptance and fund commitments are disabled.",
        ),
    ],
    "financial_planning": [
        (
            "complete_cashflow_absent",
            "No authorised complete cashflow history with coverage/reconciliation evidence exists. Payment demo observations are not a cashflow ledger.",
        ),
        (
            "payables_receivables_absent",
            "No documented payable/receivable and upcoming-commitment ledgers exist. Accepted bills do not prove unpaid debt.",
        ),
        (
            "lender_process_absent",
            "No authorised lender process or lender-approved document checklist is configured.",
        ),
        (
            "verified_lending_consent_absent",
            "No purpose-bound lender consent/withdrawal registry exists. A checkbox or reference supplied here cannot establish consent.",
        ),
        (
            "underwriting_forbidden",
            "Eligibility scores, creditworthiness, approval/denial, loan terms and autonomous applications are not supported.",
        ),
    ],
    "benchmarking": [
        (
            "cohort_policy_absent",
            "No approved cohort sample-size, purpose, anonymisation, outlier and anti-reidentification controls exist. All peer statistics are suppressed.",
        ),
        (
            "p1_quality_unproven",
            "Relevant P1 source coverage and growth-comparison methodology have not been evaluated.",
        ),
        (
            "historical_comparison_unproven",
            "A growth comparison cannot be derived from stock movements or payment totals alone. Review your own recorded movement history instead.",
        ),
    ],
}


def flag(capability):
    name = CONFIG[capability][0]
    value = os.getenv(name, "0")
    return {"name": name, "requested": value == "1", "valid": value in ("0", "1")}


def gate(capability):
    setting = flag(capability)
    reasons = [{"code": code, "detail": detail} for code, detail in BLOCKERS[capability]]
    if not setting["valid"]:
        reasons.insert(
            0,
            {
                "code": "invalid_flag",
                "detail": "Feature configuration must be 0 or 1; access remains disabled.",
            },
        )
    return {
        "id": capability,
        "label": CONFIG[capability][1],
        "risk_classification": CONFIG[capability][2],
        "configuration": setting,
        "status": "blocked" if setting["requested"] else "disabled",
        "available": False,
        "proposal_generation_enabled": False,
        "external_execution_enabled": False,
        "prerequisites_proven": False,
        "blockers": reasons,
        "uncertainty": "Existing records do not establish the missing source quality, permissions or integration contracts.",
    }


def readiness(db):
    p = auth.current()
    now = datetime.now(timezone.utc)
    counts = {}
    queries = (
        ("catalog_records", m.products, None),
        ("supplier_records", m.suppliers, None),
        ("accepted_purchases", m.purchases, m.purchases.c.status == "accepted"),
        ("accepted_physical_receipts", m.receipts, None),
        ("inventory_events", m.inventory_events, None),
        (
            "live_settlement_observations",
            m.settlement_batches,
            m.settlement_batches.c.mode == "live",
        ),
        (
            "demo_settlement_observations",
            m.settlement_batches,
            m.settlement_batches.c.mode == "demo",
        ),
    )
    for name, table, condition in queries:
        query = select(func.count()).select_from(table).where(store.scope(table))
        if condition is not None:
            query = query.where(condition)
        counts[name] = db.execute(query).scalar_one()
    # Bounded samples, never all-store or cross-merchant aggregation. No phones,
    # documents, bank references, monetary totals or other merchants' IDs exposed.
    products = db.execute(
        select(m.products).where(store.scope(m.products)).order_by(m.products.c.id).limit(5)
    ).mappings()
    sources = []
    for product in products:
        last_event = db.execute(
            select(func.max(m.inventory_events.c.at)).where(
                store.scope(m.inventory_events), m.inventory_events.c.product_id == product["id"]
            )
        ).scalar_one()
        sources.append(
            {
                "type": "product",
                "id": product["id"],
                "label": product["name"],
                "unit": product["unit"],
                "product_version": product["version"],
                "stock_version": product["stock_version"],
                "route": "/stock/" + product["id"],
                "source_recorded_at": last_event or product["created_at"],
                "timestamp_basis": "last accepted inventory event"
                if last_event
                else "catalogue creation (no inventory event)",
            }
        )
    return {
        "schema_version": 1,
        "assessed_at": now,
        "mode": "demo" if p.demo else "merchant_records",
        "label": "Synthetic demo store" if p.demo else "Your recorded store",
        "record_counts": counts,
        "counts_are_quality_proof": False,
        "source_samples": sources,
        "source_sample_limit": 5,
        "source_samples_truncated": counts["catalog_records"] > len(sources),
        "capabilities": [gate(capability) for capability in CONFIG],
        "peer_comparison": {
            "suppressed": True,
            "cohort_size": None,
            "methodology": None,
            "date_range": None,
            "reason": "No approved cohort exists; no cross-store query is performed.",
        },
        "safe_alternative": "Review your own recorded SKU movement timeline. No peer or growth comparison is calculated.",
        "data_freshness": "Queried now; source timestamps describe recorded events, not current supplier price/availability or cashflow completeness.",
    }


class ProductContext(StrictModel):
    product_id: str = Field(min_length=1, max_length=64)
    expected_product_version: int = Field(ge=1, strict=True)
    expected_stock_version: int = Field(ge=0, strict=True)
    unit: Unit
    merchant_confirmed_need: bool = False


class OfferTimingClaim(StrictModel):
    # Declarations only. No price, availability, verification or consent field can
    # be promoted into server truth; even a fresh declaration remains blocked.
    observed_at: AwareDatetime
    valid_until: AwareDatetime


class LendingConsentClaim(StrictModel):
    purpose: Literal["lender_document_readiness"]
    process_reference: str = Field(min_length=1, max_length=100)
    granted: bool


class Assessment(StrictModel):
    capability: Capability
    intent: Literal[
        "purchase_order_draft",
        "financial_summary",
        "lender_checklist",
        "within_store_history",
        "peer_comparison",
    ]
    product: ProductContext | None = None
    supplier_id: str | None = Field(default=None, min_length=1, max_length=64)
    evidence_attachment_id: str | None = Field(default=None, min_length=1, max_length=64)
    offer_timing_claim: OfferTimingClaim | None = None
    lending_consent_claim: LendingConsentClaim | None = None
    claimed_cohort_size: int | None = Field(default=None, ge=0, le=1000000000, strict=True)

    @model_validator(mode="after")
    def compatible(self):
        if self.intent not in INTENTS[self.capability]:
            raise ValueError("Intent does not belong to this capability.")
        if self.capability != "procurement" and any(
            (self.supplier_id, self.evidence_attachment_id, self.offer_timing_claim)
        ):
            raise ValueError("Supplier evidence is only relevant to procurement readiness.")
        if self.lending_consent_claim and self.intent != "lender_checklist":
            raise ValueError("Lender consent must have the specific document-readiness purpose.")
        if self.claimed_cohort_size is not None and self.intent != "peer_comparison":
            raise ValueError(
                "A declared cohort size is only relevant to peer-comparison readiness."
            )
        if self.capability == "financial_planning" and self.product:
            raise ValueError("A SKU record is not evidence of lending readiness or cashflow.")
        return self


def assess(db, body):
    p = auth.current("admin" if body.capability == "financial_planning" else "write")
    now = datetime.now(timezone.utc)
    result = gate(body.capability)
    sources, checks = [], []

    def check(code, detail):
        checks.append({"code": code, "detail": detail})

    if body.product:
        ctx = body.product
        product = inventory.product(db, ctx.product_id)
        sources.append(
            {
                "type": "product",
                "id": product["id"],
                "version": product["version"],
                "stock_version": product["stock_version"],
            }
        )
        if (
            ctx.expected_product_version != product["version"]
            or ctx.expected_stock_version != product["stock_version"]
        ):
            check(
                "stale_source_version",
                "The recorded SKU or stock version changed. Reopen its workflow; this check never approves a write.",
            )
        if ctx.unit != product["unit"]:
            check(
                "unit_mismatch",
                "The requested unit differs from the recorded SKU. No implicit conversion is allowed.",
            )
        if not ctx.merchant_confirmed_need and body.capability == "procurement":
            check(
                "need_unconfirmed", "A catalogue or threshold alone does not confirm an order need."
            )
    elif body.capability == "procurement":
        check(
            "product_source_missing",
            "Choose a recorded SKU and confirm its units, versions and actual need in the source workflow.",
        )
    for table, value, kind in (
        (m.suppliers, body.supplier_id, "supplier"),
        (m.attachments, body.evidence_attachment_id, "attachment"),
    ):
        if value:
            row = db.execute(
                select(table.c.id).where(store.scope(table), table.c.id == value)
            ).first()
            if not row:
                raise KeyError(value)  # Same response for nonexistent and cross-store IDs.
            sources.append({"type": kind, "id": value})
    if body.capability == "procurement":
        if not body.supplier_id:
            check("supplier_source_missing", "No store-owned supplier source was selected.")
        if not body.evidence_attachment_id:
            check(
                "supplier_evidence_missing",
                "No source attachment was selected. An attachment alone would not verify an offer or its permission.",
            )
        claim = body.offer_timing_claim
        if claim:
            if claim.observed_at > now or claim.valid_until <= claim.observed_at:
                check(
                    "invalid_offer_dates",
                    "Declared offer timing is implausible; no price is trusted.",
                )
            elif claim.valid_until <= now:
                check(
                    "stale_offer_claim",
                    "The declared offer has expired. A historical price cannot become a current order input.",
                )
            else:
                check(
                    "unverified_offer_claim",
                    "A current-looking timestamp is only a declaration; no verified price, availability, tax/shipping basis or source permission exists.",
                )
    if body.intent == "lender_checklist":
        check(
            "consent_unverified"
            if body.lending_consent_claim and body.lending_consent_claim.granted
            else "consent_missing",
            "No lender-authorised, purpose-bound consent can be verified. This check does not register consent or submit data.",
        )
    if body.intent == "peer_comparison":
        check(
            "cohort_suppressed",
            "All peer results are suppressed. A client-declared cohort size, however large, cannot establish anonymisation, legal basis or sample quality.",
        )
    aid = store.uid()
    # Successful readiness inspection only, never a successful proposal/order.
    # Existing middleware persists the receipt atomically and replays exact retry
    # requests. Audit contains source IDs and enums only, no consent reference/PII.
    store.audit_record(
        db,
        aid,
        "P2 readiness checked; capability blocked",
        source_ids=[s["id"] for s in sources] or [aid],
        entity_type="planning_check",
        snapshot={
            "capability": body.capability,
            "intent": body.intent,
            "status": result["status"],
            "risk": result["risk_classification"],
            "codes": [r["code"] for r in checks],
        },
    )
    return {
        "schema_version": 1,
        "assessment_id": aid,
        "assessed_at": now,
        "mode": "demo" if p.demo else "merchant_records",
        "assessment_only": True,
        "capability": result,
        "intent": body.intent,
        "source_records": sources,
        "checks": checks,
        "proposal_created": False,
        "external_action_performed": False,
        "financial_decision": None,
        "peer_statistics": None,
        "consent_verified": False,
        "notice": "This is a readiness snapshot, not approval. No order, financial plan, lender checklist/application or cohort comparison was generated. A replay retains its original timestamp.",
    }


@router.get("/readiness")
def get_readiness():
    with store.connect() as db:
        return readiness(db)


@router.post("/assess")
def check_readiness(body: Assessment):
    with store.connect("write") as db:
        return assess(db, body)


@router.post("/{capability}/execute")
def execution_disabled(capability: Capability):
    # No executor is configured; neither owner, feature flag nor a claimed
    # approval can bypass that. Future execution must use central approvals,
    # fresh permissions/versions and verified integration contracts.
    auth.current("approve")
    raise HTTPException(
        409,
        "P2 execution is unavailable: prerequisites, exact reviewed approval and verified integration contracts are missing. Nothing was sent, ordered or submitted.",
    )
