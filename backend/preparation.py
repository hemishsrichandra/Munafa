"""Source-linked local preparation. No eligibility, tax determination or submission."""

from datetime import date, datetime, timezone
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from pydantic import Field, model_validator
from sqlalchemy import select, text
from . import auth, actions, store, models as m
from .domain import StrictModel, RuleError

router = APIRouter(prefix="/api/preparation")


class Period(StrictModel):
    start: date
    end: date

    @model_validator(mode="after")
    def valid(self):
        if not 0 <= (self.end - self.start).days <= 366:
            raise ValueError("Choose an ordered period of at most 367 days.")
        return self


class PackRequest(Period):
    source_ids: list[str] = Field(default_factory=list, max_length=100)


def build(db, body: Period, source_ids=None):
    p = auth.current()
    # Accepted immutable snapshots, never draft OCR or inferred unpaid balances.
    rows = db.execute(
        select(
            m.purchases.c.id,
            m.purchases.c.version,
            m.purchase_acceptances.c.snapshot,
            m.purchase_acceptances.c.total_paise,
        )
        .join(
            m.purchase_acceptances,
            (m.purchases.c.id == m.purchase_acceptances.c.purchase_id)
            & (m.purchases.c.store_id == m.purchase_acceptances.c.store_id),
        )
        .where(store.scope(m.purchases), m.purchases.c.status == "accepted")
        .where(
            m.purchase_acceptances.c.snapshot["invoice"]["date"].as_string()
            >= body.start.isoformat(),
            m.purchase_acceptances.c.snapshot["invoice"]["date"].as_string()
            <= body.end.isoformat(),
        )
        .where(m.purchases.c.id.in_(source_ids) if source_ids is not None else True)
        .order_by(m.purchases.c.id)
        .limit(101)
    ).mappings()
    records = []
    requested = set(source_ids) if source_ids is not None else None
    for row in rows:
        snapshot = row["snapshot"]
        # Snapshot structure is owned by existing purchase acceptance, not a provider.
        draft = snapshot["invoice"]
        recorded_date = date.fromisoformat(draft["date"])
        if not body.start <= recorded_date <= body.end:
            continue
        if requested is not None and row["id"] not in requested:
            continue
        docs = list(
            db.execute(
                select(m.purchase_documents.c.id, m.purchase_documents.c.sha256)
                .where(
                    store.scope(m.purchase_documents),
                    m.purchase_documents.c.purchase_id == row["id"],
                )
                .order_by(m.purchase_documents.c.id)
            ).mappings()
        )
        records.append(
            {
                "purchase_id": row["id"],
                "purchase_version": row["version"],
                "source_route": "/purchases/" + row["id"],
                "date": draft["date"],
                "reference": draft["reference"],
                "supplier": draft["supplier"],
                "total_paise": row["total_paise"],
                "tax_paise_recorded": draft.get("tax_paise"),
                "documents": [dict(d) for d in docs],
                "review_status": "merchant_accepted_not_CA_reviewed",
                "exceptions": [
                    "GSTIN, HSN, place of supply and tax classification are not captured by this model."
                ]
                + ([] if docs else ["No original document attached; manual source only."]),
            }
        )
        if len(records) > 100:
            raise RuleError(
                "More than 100 purchases in period. Narrow the period; no records were silently omitted."
            )
    if requested is not None and requested != {r["purchase_id"] for r in records}:
        raise RuleError("A selected source is unavailable in this store/period.")
    return {
        "schema_version": 1,
        "purpose": "local_bookkeeping_preparation",
        "mode": "demo" if p.demo else "live",
        "period": body.model_dump(mode="json", include={"start", "end"}),
        "status": "needs_external_review",
        "recipient": "merchant_local_download_only",
        "records": records,
        "total_recorded_paise": sum(r["total_paise"] for r in records),
        "coverage": "Accepted purchases in selected period only; not a complete sales, GST, cashflow, debt or lending record.",
        "lender_checklist": "BLOCKED — no authorised lender/product checklist; no eligibility or offer calculated.",
        "filing": "BLOCKED — no CA review, authorised filing contract or official acknowledgement.",
        "originals": "Documents stay in the existing scoped purchase store; this pack contains IDs/hashes, not document bytes.",
    }


@router.post("/preview")
def preview(body: Period):
    with store.connect() as db:
        return build(db, body)


def proposal_payload(db, payload):
    period = Period.model_validate(payload["period"])
    return build(db, period, payload["source_ids"])


@router.post("/proposals", status_code=201)
def propose(body: PackRequest, request: Request):
    auth.current("export")
    with store.connect("write") as db:
        if not body.source_ids:
            raise RuleError("Review and select at least one accepted purchase first.")
        return actions.propose(
            db,
            "export_preparation",
            "preparation",
            {
                "period": body.model_dump(mode="json", include={"start", "end"}),
                "source_ids": body.source_ids,
            },
            0,
            request.headers["idempotency-key"],
        )


def revalidate(db, action):
    payload = action["payload"]
    fresh = build(
        db, Period.model_validate(payload["period"]), [r["purchase_id"] for r in payload["records"]]
    )
    if actions.payload_digest(fresh) != action["payload_digest"]:
        raise RuleError("Preparation sources changed. Review and approve a new pack.")


@router.get("/export")
def export(action_id: str):
    p = auth.current("export")
    with store.connect("export") as db:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        a = actions.get(db, action_id)
        if (
            a["action_type"] != "export_preparation"
            or a["status"] != "executed"
            or a["created_by"] != p.user_id
            or a["approved_by"] != p.user_id
            or a["expires_at"] <= datetime.now(timezone.utc)
        ):
            raise HTTPException(403, "Approve your exact preparation pack before download.")
        revalidate(db, a)
        store.audit_record(db, a["id"], "Preparation pack downloaded", entity_type="export")
        output = {
            **a["payload"],
            "approval": {
                "action_id": a["id"],
                "payload_digest": a["payload_digest"],
                "approved_at": a["approved_at"].isoformat(),
                "meaning": "Merchant approved local export; not CA review or partner submission.",
            },
        }
    return Response(
        json.dumps(output, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="unreviewed-preparation.json"'},
    )
