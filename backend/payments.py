"""Typed immutable provider observations and deterministic, component-based reconciliation."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Literal, Protocol, Annotated
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime
from sqlalchemy import select, insert
from fastapi import APIRouter, HTTPException
from . import models as m, store, auth
from .domain import RuleError

Money = Annotated[int, Field(strict=True, ge=0, le=9000000000000000)]
Identifier = Annotated[str, Field(min_length=1, max_length=120)]
Mode = Literal["demo", "live"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentEvent(Strict):
    source_id: Identifier
    transaction_id: Identifier
    event_id: Identifier
    kind: Literal["payment", "refund", "reversal"]
    status: Literal["pending", "succeeded", "failed"]
    amount_paise: Money
    occurred_at: AwareDatetime


class SettlementLine(Strict):
    source_id: Identifier
    transaction_id: Identifier
    gross_paise: Money | None = None
    commission_paise: Money | None = None
    gst_paise: Money | None = None
    refund_paise: Money | None = None
    reversal_paise: Money | None = None
    adjustment_paise: (
        Annotated[int, Field(strict=True, ge=-9000000000000000, le=9000000000000000)] | None
    ) = None


class SettlementBatch(Strict):
    source_id: Identifier
    status: Literal["pending", "settled", "failed"]
    settled_paise: Money | None = None
    payout_reference: Identifier | None = None
    settlement_at: AwareDatetime | None = None
    payout_at: AwareDatetime | None = None
    cutoff_at: AwareDatetime | None = None
    observed_at: AwareDatetime
    lines: Annotated[list[SettlementLine], Field(min_length=1, max_length=1000)]


class Provider(Protocol):
    def snapshot(self) -> tuple[list[PaymentEvent], list[SettlementBatch]]: ...
    def verify_webhook(self, body: bytes, headers: dict) -> bool: ...


class DisabledLive:
    def snapshot(self):
        raise RuleError(
            "Live Paytm access is disabled: authorised credentials, supported environment and contract tests are required."
        )

    def verify_webhook(self, body, headers):
        return False  # No guessed signature algorithm or public ingestion endpoint.


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ingest(db, *, mode, provider, events, batches, provenance):
    """Internal adapter boundary, not an unauthenticated webhook. Transaction owned by request."""
    p = auth.current("admin")
    if mode != "demo" or not p.demo or provider != "fixture":
        raise RuleError("Only isolated synthetic demo ingestion is enabled.")
    now = datetime.now(timezone.utc)
    for event in events:
        event = PaymentEvent.model_validate(event)
        payload = event.model_dump(mode="json")
        fingerprint = digest(payload)
        q = select(m.payment_events).where(
            store.scope(m.payment_events),
            m.payment_events.c.mode == mode,
            m.payment_events.c.provider == provider,
            m.payment_events.c.source_id == event.source_id,
        )
        old = db.execute(q).mappings().first()
        if old:
            if old["source_digest"] != fingerprint:
                raise RuleError(
                    "Provider source ID already has different content; review required."
                )
            continue
        db.execute(
            insert(m.payment_events).values(
                id=store.uid(),
                store_id=p.store_id,
                mode=mode,
                provider=provider,
                **event.model_dump(),
                ingested_at=now,
                source_digest=fingerprint,
                provenance=provenance,
            )
        )
    for batch in batches:
        batch = SettlementBatch.model_validate(batch)
        fingerprint = digest(batch.model_dump(mode="json"))
        old = (
            db.execute(
                select(m.settlement_batches).where(
                    store.scope(m.settlement_batches),
                    m.settlement_batches.c.mode == mode,
                    m.settlement_batches.c.provider == provider,
                    m.settlement_batches.c.source_id == batch.source_id,
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["source_digest"] != fingerprint:
                raise RuleError(
                    "Settlement source ID already has different content; review required."
                )
            continue
        bid = store.uid()
        db.execute(
            insert(m.settlement_batches).values(
                id=bid,
                store_id=p.store_id,
                mode=mode,
                provider=provider,
                **batch.model_dump(exclude={"lines"}),
                ingested_at=now,
                source_digest=fingerprint,
                provenance=provenance,
            )
        )
        for line in batch.lines:
            db.execute(
                insert(m.settlement_lines).values(
                    id=store.uid(),
                    store_id=p.store_id,
                    batch_id=bid,
                    mode=mode,
                    **line.model_dump(),
                )
            )
        store.audit_record(
            db,
            bid,
            "Synthetic settlement observations imported",
            entity_type="settlement",
            source_ids=[bid],
        )


def current_events(rows):
    # A status update is an observation, not a second payment. Keep latest event-time;
    # conflicting equal-time observations are unresolved rather than guessed.
    grouped = {}
    for r in rows:
        grouped.setdefault((r["transaction_id"], r["kind"], r["event_id"]), []).append(r)
    result, conflicts = {}, set()
    for key, versions in grouped.items():
        latest_time = max(r["occurred_at"] for r in versions)
        latest = [r for r in versions if r["occurred_at"] == latest_time]
        if len({(r["status"], r["amount_paise"]) for r in latest}) > 1:
            conflicts.add(key)
        result[key] = sorted(latest, key=lambda r: r["source_id"])[-1]
    summaries = {}
    for (tx, kind, event_id), row in result.items():
        key = (tx, kind)
        if key not in summaries:
            summaries[key] = {**row, "amount_paise": 0, "ids": [], "status": "failed"}
        summary = summaries[key]
        summary["ids"].append(row["id"])
        summary["occurred_at"] = max(summary["occurred_at"], row["occurred_at"])
        if row["status"] == "succeeded":
            summary["amount_paise"] += row["amount_paise"]
            summary["status"] = "succeeded"
        elif row["status"] == "pending" and summary["status"] != "succeeded":
            summary["status"] = "pending"
    return summaries, {(tx, kind) for tx, kind, event_id in conflicts}


def reconcile(batch, lines, events, now=None):
    now = now or datetime.now(timezone.utc)
    current, conflicts = current_events(events)
    fields = ("gross", "commission", "gst", "refund", "reversal", "adjustment")
    totals = {f: 0 for f in fields}
    reasons, missing, source_ids = [], [], [batch["id"]]

    def reason(code, detail):
        if not any(r["code"] == code for r in reasons):
            reasons.append(
                {
                    "code": code,
                    "detail": detail,
                    "classification": "verified_field"
                    if code in ("fees", "refunds", "reversals")
                    else "review_candidate",
                }
            )

    for line in lines:
        source_ids.append(line["id"])
        for f in fields:
            value = line[f + "_paise"]
            if value is None:
                missing.append(f"{line['source_id']}:{f}_paise")
            else:
                totals[f] += value
        tx = line["transaction_id"]
        payment = current.get((tx, "payment"))
        if not payment or payment["status"] != "succeeded":
            reason(
                "uncorrelated_payment", "No confirmed matching collection observation is recorded."
            )
        elif payment["amount_paise"] != line["gross_paise"]:
            reason(
                "collection_mismatch",
                "Recorded collection differs from the settlement gross field.",
            )
        for kind in ("payment", "refund", "reversal"):
            event = current.get((tx, kind))
            if event:
                source_ids.extend(event["ids"])
            if (tx, kind) in conflicts:
                reason(
                    "conflicting_observations",
                    "Equal-time provider observations conflict; review source records.",
                )
            if kind != "payment" and line[kind + "_paise"] is not None:
                recorded = event["amount_paise"] if event and event["status"] == "succeeded" else 0
                if recorded != line[kind + "_paise"]:
                    reason(
                        "uncorrelated_" + kind,
                        f"{kind.title()} component lacks a matching successful observation.",
                    )
        if payment and batch.get("cutoff_at") and payment["occurred_at"] > batch["cutoff_at"]:
            reason("cutoff", "Collection observation falls after the recorded payout cutoff.")
    if missing or batch["settled_paise"] is None:
        reason(
            "missing_fields",
            "Reconciliation is incomplete: unknown amounts are never assumed to be zero.",
        )
    if totals["commission"] or totals["gst"]:
        reason("fees", "Recorded commission and GST are deductions; no fee rate is inferred.")
    if totals["refund"]:
        reason("refunds", "The statement records a refund deduction.")
    if totals["reversal"]:
        reason("reversals", "The statement records a reversal deduction.")
    if totals["adjustment"]:
        reason(
            "adjustment",
            "A signed statement adjustment is recorded; its cause needs source review.",
        )
    expected = (
        None
        if missing
        else totals["gross"]
        - totals["commission"]
        - totals["gst"]
        - totals["refund"]
        - totals["reversal"]
        + totals["adjustment"]
    )
    difference = (
        None
        if expected is None or batch["settled_paise"] is None
        else batch["settled_paise"] - expected
    )
    if batch["status"] != "settled" or not batch.get("payout_at") or batch.get("payout_at") > now:
        reason(
            "timing_pending", "Payout completion is not established by the recorded status/date."
        )
    if batch["status"] == "settled" and (
        not batch.get("settlement_at") or not batch.get("payout_reference")
    ):
        reason(
            "missing_payout_evidence",
            "Completed status lacks a settlement date or payout reference; bank receipt is unverified.",
        )
    stale = now - batch["observed_at"] > timedelta(hours=24)
    if stale:
        reason("stale", "Source observation is older than 24 hours; this is not live status.")
    if difference not in (None, 0):
        reason(
            "unexplained_difference",
            "Recorded payout differs from known components. Review linked evidence; no missing-money conclusion is made.",
        )
    review_codes = [r for r in reasons if r["classification"] == "review_candidate"]
    return {
        "batch_id": batch["id"],
        "source_id": batch["source_id"],
        "mode": batch["mode"],
        "provider": batch["provider"],
        "status": batch["status"],
        "components_paise": totals,
        "missing_fields": missing,
        "expected_net_paise": expected,
        "recorded_settled_paise": batch["settled_paise"],
        "difference_paise": difference,
        "needs_review": bool(review_codes),
        "reasons": reasons,
        "source_entity_ids": sorted(set(source_ids)),
        "observed_at": batch["observed_at"],
        "stale": stale,
        "payout_reference": batch.get("payout_reference"),
        "settlement_at": batch.get("settlement_at"),
        "payout_at": batch.get("payout_at"),
        "bank_receipt_verified": False,
    }


def overview(db, mode):
    if mode == "demo" and not auth.current().demo:
        raise HTTPException(403, "Demo data requires an isolated demo store.")
    batches = list(
        db.execute(
            select(m.settlement_batches)
            .where(store.scope(m.settlement_batches), m.settlement_batches.c.mode == mode)
            .order_by(m.settlement_batches.c.observed_at.desc())
        ).mappings()
    )
    events = list(
        db.execute(
            select(m.payment_events).where(
                store.scope(m.payment_events), m.payment_events.c.mode == mode
            )
        ).mappings()
    )
    results = []
    for batch in batches:
        lines = list(
            db.execute(
                select(m.settlement_lines).where(
                    store.scope(m.settlement_lines),
                    m.settlement_lines.c.batch_id == batch["id"],
                    m.settlement_lines.c.mode == mode,
                )
            ).mappings()
        )
        results.append(
            reconcile(batch, lines, [e for e in events if e["provider"] == batch["provider"]])
        )
    return {
        "mode": mode,
        "label": "SYNTHETIC DEMO DATA" if mode == "demo" and batches else "No connected Paytm data",
        "live_enabled": False,
        "updated_at": datetime.now(timezone.utc),
        "last_source_at": max((r["observed_at"] for r in batches), default=None),
        "settlements": results,
    }


class DemoAdapter:
    def snapshot(self):
        # Local fixture, never fetched from Paytm. Dates relative to this explicit load.
        from pathlib import Path

        raw = json.loads(
            Path(__file__).with_name("fixtures").joinpath("settlements.json").read_text()
        )
        day = datetime.now(timezone.utc).replace(
            hour=4, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        events = []
        for row in raw["events"]:
            offset = row.pop("minute_offset", 0)
            events.append(PaymentEvent(**row, occurred_at=day + timedelta(minutes=offset)))
        batches = [
            SettlementBatch(
                **{
                    **r,
                    "observed_at": day + timedelta(hours=6),
                    "settlement_at": day + timedelta(hours=5),
                    "payout_at": day + timedelta(hours=5),
                    "cutoff_at": day + timedelta(hours=1),
                }
            )
            for r in raw["batches"]
        ]
        return events, batches

    def verify_webhook(self, body, headers):
        return False


router = APIRouter(prefix="/api")


@router.get("/payments")
def read_payments(mode: Mode = "live"):
    with store.connect() as db:
        return overview(db, mode)


@router.post("/payments/demo", status_code=201)
def load_demo():
    auth.current("admin")
    with store.connect("admin") as db:
        events, batches = DemoAdapter().snapshot()
        # Stable source IDs: reloading returns existing data, without rewriting history.
        exists = db.execute(
            select(m.settlement_batches.c.id).where(
                store.scope(m.settlement_batches), m.settlement_batches.c.mode == "demo"
            )
        ).first()
        if not exists:
            ingest(
                db,
                mode="demo",
                provider="fixture",
                events=events,
                batches=batches,
                provenance={"fixture": "settlements-v1", "synthetic": True, "schema_version": 1},
            )
        return overview(db, "demo")


@router.get("/payments/{batch_id}")
def payment_detail(batch_id: str, mode: Mode = "live"):
    with store.connect() as db:
        result = overview(db, mode)
        found = next((r for r in result["settlements"] if r["batch_id"] == batch_id), None)
        if not found:
            raise KeyError(batch_id)
        return found


@router.post("/payments/live/connect")
def live_gate():
    auth.current("admin")
    raise HTTPException(503, "Live Paytm integration is disabled. See docs/PAYTM-INTEGRATION.md.")
