import csv
import hashlib
import io
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from . import store, ai
from .domain import (
    Invoice,
    Review,
    Version,
    Sent,
    Promise,
    Resolution,
    StrictModel,
    RuleError,
    calculate,
    audit,
    new_case,
    present,
    normalized,
    now,
    local_today,
)
from .samples import sample_invoice, demo_seed


@asynccontextmanager
async def lifespan(app):
    store.init()
    if os.getenv("MUNAFA_SEED", "1") == "1":
        demo_seed()
    yield


app = FastAPI(title="Munafa Merchant Credit API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RuleError)
async def rules(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(KeyError)
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Case or attachment not found."})


@app.middleware("http")
async def local_guard(request: Request, call_next):
    # This unauthenticated prototype must be served only on loopback. Prevent browser cross-origin writes.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        allowed = {
            f"http://{h}:{p}" for h in ("localhost", "127.0.0.1") for p in (8000, 5173, 4173)
        }
        if request.url.hostname in ("localhost", "127.0.0.1"):
            allowed.add(str(request.base_url).rstrip("/"))
        if origin not in allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin writes are disabled for this local prototype."},
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


def db_cases(db):
    return [json.loads(r["data"]) for r in db.execute("SELECT data FROM cases")]


def identifier():
    return "MNF-" + uuid.uuid4().hex[:8].upper()


def insert_invoice(invoice, synthetic=False, attachment=None):
    try:
        date.fromisoformat(invoice["date"])
    except ValueError:
        raise RuleError("Enter a valid invoice date.")
    c = new_case(invoice, identifier(), synthetic)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        # A duplicated supplier invoice must be reviewed in the existing case.
        for row in db.execute("SELECT data FROM cases"):
            old = json.loads(row["data"])
            if normalized(old["invoice"]["supplier"]) == normalized(
                invoice["supplier"]
            ) and normalized(old["invoice"]["reference"]) == normalized(invoice["reference"]):
                raise RuleError(f"Invoice already exists in {old['id']}. Open the existing case.")
        store.save(db, c)
        if attachment:
            aid = uuid.uuid4().hex
            db.execute(
                "INSERT INTO attachments VALUES (?,?,?,?,?)",
                (aid, c["id"], attachment[0], attachment[1], attachment[2]),
            )
            c["attachment_id"] = aid
            store.save(db, c)
    return present(c)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "sarvam_configured": ai.configured(),
        "vision_model": os.getenv("SARVAM_VISION_MODEL", "gemma4"),
        "chat_model": os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b"),
        "mode": "local prototype",
    }


@app.get("/api/cases")
def cases():
    return [present(c) for c in store.all_cases()]


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    with store.connect() as db:
        return present(store.get(db, case_id))


@app.post("/api/invoices/sample", status_code=201)
def sample():
    return insert_invoice(sample_invoice(), True)


@app.post("/api/invoices/manual", status_code=201)
def manual(invoice: Invoice):
    try:
        date.fromisoformat(invoice.date)
    except ValueError:
        raise RuleError("Enter a valid invoice date.")
    return insert_invoice(invoice.model_dump())


class TextExtract(StrictModel):
    text: str = Field(min_length=20, max_length=18000)


@app.post("/api/invoices/extract-text", status_code=201)
def extract_text(body: TextExtract):
    invoice = ai.extract(text=body.text)
    return insert_invoice(invoice)


async def read_file(file: UploadFile, proof=False):
    data = await file.read(8 * 1024 * 1024 + 1)
    if not data or len(data) > 8 * 1024 * 1024:
        raise RuleError("Choose a non-empty file smaller than 8 MB.")
    mime = file.content_type
    valid = (
        (mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
        or (mime == "image/webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )
    if proof and mime == "application/pdf" and data.startswith(b"%PDF-"):
        valid = True
    if not valid:
        raise RuleError("Use a PNG, JPEG or WebP image" + (" or PDF proof." if proof else "."))
    return data, mime


@app.post("/api/invoices/extract", status_code=201)
async def extract_image(file: UploadFile = File(...)):
    data, mime = await read_file(file)
    # Run blocking provider I/O outside the event loop.
    from starlette.concurrency import run_in_threadpool

    invoice = await run_in_threadpool(ai.extract, image=data, mime=mime)
    return insert_invoice(invoice, attachment=(file.filename or "invoice", mime, data))


@app.patch("/api/cases/{case_id}/review")
def review(case_id: str, body: Review):
    with store.mutate(case_id, body.version) as (db, c):
        if c["resolutions"]:
            raise RuleError(
                "A case with recorded recovery cannot be edited. Keep the original evidence and review any additional issue separately."
            )
        try:
            date.fromisoformat(body.invoice.date)
        except ValueError:
            raise RuleError("Enter a valid invoice date.")
        for old in db_cases(db):
            if (
                old["id"] != case_id
                and normalized(old["invoice"]["supplier"]) == normalized(body.invoice.supplier)
                and normalized(old["invoice"]["reference"]) == normalized(body.invoice.reference)
            ):
                raise RuleError("This supplier invoice already has another case.")
        c["invoice"] = body.invoice.model_dump()
        c.update(
            delivery_complete=body.delivery_complete,
            pricing_confirmed=body.pricing_confirmed,
            status="review",
            approved_version=None,
            approved_amount_paise=None,
            follow_up=None,
            promise=None,
        )
        audit(
            c,
            "Counts reviewed",
            "Evidence changed. Previous approval and follow-up are invalidated; sharing history is retained.",
        )
    return present(c)


@app.post("/api/cases/{case_id}/approve")
def approve(case_id: str, body: Version):
    with store.mutate(case_id, body.version) as (_, c):
        if c["status"] != "review":
            raise RuleError("Only a case in review can be approved.")
        calc = calculate(c["invoice"]["lines"], c["delivery_complete"], c["pricing_confirmed"])
        if not calc["eligible"]:
            raise RuleError(" ".join(calc["issues"]) or "There is no delivery shortage to claim.")
        c.update(
            status="ready",
            approved_version=c["version"] + 1,
            approved_amount_paise=calc["amount_paise"],
        )
        audit(
            c,
            "Evidence approved",
            f"INR {calc['amount_paise'] / 100:.2f} reviewed by the merchant.",
            snapshot={
                "version": c["approved_version"],
                "invoice": c["invoice"],
                "amount_paise": calc["amount_paise"],
                "delivery_complete": True,
                "pricing_confirmed": True,
            },
        )
    return present(c)


@app.post("/api/cases/{case_id}/sent")
def sent(case_id: str, body: Sent):
    with store.mutate(case_id, body.version) as (_, c):
        if c["status"] != "ready" or c["approved_version"] is None or not body.confirmed:
            raise RuleError("Approve the current evidence and explicitly confirm that you sent it.")
        c["status"] = "sent"
        audit(
            c,
            "Sharing confirmed",
            "Merchant confirmed sending the approved evidence. Delivery/read status is not verified.",
        )
    return present(c)


@app.post("/api/cases/{case_id}/promise")
def promise(case_id: str, body: Promise):
    try:
        due = date.fromisoformat(body.follow_up)
    except ValueError:
        raise RuleError("Choose a valid follow-up date.")
    if due < local_today():
        raise RuleError("A new follow-up date must be today or later.")
    with store.mutate(case_id, body.version) as (_, c):
        if c["status"] not in ("sent", "promised", "partial"):
            raise RuleError("Confirm sharing before recording a supplier promise.")
        c.update(
            status="partial" if c["resolutions"] else "promised",
            follow_up=body.follow_up,
            promise=body.note,
        )
        audit(c, "Supplier promise recorded", body.note + " Follow up: " + body.follow_up)
    return present(c)


@app.post("/api/cases/{case_id}/proof", status_code=201)
async def proof(case_id: str, file: UploadFile = File(...)):
    data, mime = await read_file(file, True)
    aid = uuid.uuid4().hex
    with store.connect() as db:
        store.get(db, case_id)
        db.execute(
            "INSERT INTO attachments VALUES (?,?,?,?,?)",
            (aid, case_id, file.filename or "proof", mime, data),
        )
    return {"attachment_id": aid, "name": file.filename}


class SampleProof(StrictModel):
    amount_paise: int | None = Field(default=None, gt=0, le=100000000, strict=True)
    kind: Literal["credit", "refund"] = "credit"
    evidence_reference: str | None = Field(default=None, min_length=1, max_length=100)


@app.post("/api/cases/{case_id}/sample-proof", status_code=201)
def sample_proof(case_id: str, body: SampleProof = SampleProof()):
    with store.connect() as db:
        c = store.get(db, case_id)
        if not c["synthetic"]:
            raise RuleError("Synthetic proof is available only for synthetic invoices.")
        if c["status"] not in ("sent", "promised", "partial"):
            raise RuleError("Confirm sharing before checking a credit.")
        ref = body.evidence_reference or (
            "DEMO-"
            + ("CN-" if body.kind == "credit" else "RF-")
            + c["invoice"]["reference"]
            + ("-" + str(len(c["resolutions"]) + 1) if c["resolutions"] else "")
        )
        amount = body.amount_paise or present(c)["remaining_paise"]
        if amount > present(c)["remaining_paise"]:
            raise RuleError("Synthetic proof amount must not exceed the remaining claim.")
        aid = uuid.uuid4().hex
        text = f"SYNTHETIC NEXT BILL / CREDIT EVIDENCE\nSupplier: {c['invoice']['supplier']}\nOriginal invoice: {c['invoice']['reference']}\nEvidence reference: {ref}\n{'Credit applied' if body.kind == 'credit' else 'Refund received'}: INR {amount / 100:.2f}\nFor hackathon demonstration only."
        db.execute(
            "INSERT INTO attachments VALUES (?,?,?,?,?)",
            (aid, case_id, ref + ".txt", "text/plain", text.encode()),
        )
        result = {
            "attachment_id": aid,
            "supplier": c["invoice"]["supplier"],
            "invoice_reference": c["invoice"]["reference"],
            "evidence_reference": ref,
            "amount_paise": amount,
            "kind": body.kind,
            "synthetic": True,
        }
        db.execute("INSERT INTO synthetic_proofs VALUES (?,?)", (aid, json.dumps(result)))
    return result


@app.post("/api/cases/{case_id}/resolve")
def resolve(case_id: str, body: Resolution):
    with store.mutate(case_id, body.version) as (db, c):
        if c["status"] not in ("sent", "promised", "partial") or c["approved_version"] is None:
            raise RuleError("Only a shared, approved case can receive a verified credit or refund.")
        if not body.applied_confirmed:
            raise RuleError("Confirm the credit was actually applied or the refund was received.")
        if normalized(body.supplier) != normalized(c["invoice"]["supplier"]) or normalized(
            body.invoice_reference
        ) != normalized(c["invoice"]["reference"]):
            raise RuleError("Supplier and original invoice reference must match this case.")
        if body.amount_paise > present(c)["remaining_paise"]:
            raise RuleError(
                "The resolution exceeds the remaining claim. Partial credits may be recorded, over-credit cannot."
            )
        attachment = db.execute(
            "SELECT * FROM attachments WHERE id=? AND case_id=?", (body.attachment_id, case_id)
        ).fetchone()
        if not attachment:
            raise RuleError(
                "Attach credit or refund proof belonging to this case before closing it."
            )
        if not c["synthetic"] and attachment["mime"] == "text/plain":
            raise RuleError("Synthetic evidence cannot close a merchant invoice.")
        digest = hashlib.sha256(bytes(attachment["data"])).hexdigest()
        if db.execute(
            "SELECT 1 FROM resolution_proofs WHERE supplier=? AND digest=?",
            (normalized(body.supplier), digest),
        ).fetchone():
            raise RuleError(
                "This evidence file has already been counted. Attach distinct proof of the additional credit or refund."
            )
        fixture = db.execute(
            "SELECT data FROM synthetic_proofs WHERE attachment_id=?", (body.attachment_id,)
        ).fetchone()
        if fixture:
            fields = json.loads(fixture["data"])
            if any(
                body.model_dump()[key] != fields[key]
                for key in (
                    "kind",
                    "supplier",
                    "invoice_reference",
                    "evidence_reference",
                    "amount_paise",
                )
            ):
                raise RuleError(
                    "The entered resolution does not match the synthetic evidence. Load proof for the exact amount and type being recorded."
                )
        try:
            db.execute(
                "INSERT INTO resolution_keys VALUES (?,?)",
                (normalized(body.supplier), normalized(body.evidence_reference)),
            )
        except sqlite3.IntegrityError:
            raise RuleError(
                "This supplier evidence reference has already been counted. Use a distinct credit or refund record."
            ) from None
        try:
            db.execute(
                "INSERT INTO resolution_proofs VALUES (?,?)", (normalized(body.supplier), digest)
            )
        except sqlite3.IntegrityError:
            raise RuleError(
                "This evidence file has already been counted. Attach distinct proof of the additional credit or refund."
            ) from None
        c["resolutions"].append(
            {**body.model_dump(exclude={"version"}), "id": uuid.uuid4().hex, "at": now()}
        )
        remaining = present(c)["remaining_paise"]
        c["status"] = "resolved" if remaining == 0 else "partial"
        if not remaining:
            c["follow_up"] = None
        audit(
            c,
            "Credit verified" if body.kind == "credit" else "Refund verified",
            f"INR {body.amount_paise / 100:.2f} recorded against {body.evidence_reference}; INR {remaining / 100:.2f} remaining.",
        )
    return present(c)


def message(c):
    p = present(c)
    lines = [
        f"Hello, please review the delivery shortage on invoice {c['invoice']['reference']} ({c['invoice']['date']})."
    ]
    for line in c["invoice"]["lines"]:
        short = line["billed"] - line["received"]
        if short:
            lines.append(
                f"{line['name']}: {line['billed']} billed, {line['received']} received ({line['unit']}). {short} x INR {line['price_paise'] / 100:.2f} = INR {short * line['price_paise'] / 100:.2f}."
            )
    lines.append(
        f"Total reviewed shortage: INR {c['approved_amount_paise'] / 100:.2f}. Please issue a credit note referencing this invoice and confirm when applied, or refund the amount. Thank you."
    )
    if c["resolutions"]:
        lines.append(
            f"Already verified: INR {p['recovered_paise'] / 100:.2f}. Remaining: INR {p['remaining_paise'] / 100:.2f}."
        )
    if c["synthetic"]:
        lines.insert(0, "[SYNTHETIC DEMO — NOT A REAL CLAIM]")
    return "\n".join(lines)


class Draft(StrictModel):
    language: Literal["en-IN", "hi-IN", "kn-IN"] = "en-IN"


@app.post("/api/cases/{case_id}/message")
def draft(case_id: str, body: Draft):
    with store.connect() as db:
        c = store.get(db, case_id)
    if c["approved_version"] is None:
        raise RuleError("Approve the evidence before preparing the supplier message.")
    original = message(c)
    translated = ai.translate(original, body.language)
    return {
        "text": translated,
        "original": original,
        "provider": "sarvam" if body.language != "en-IN" else "rules",
        "version": c["version"],
        "language": body.language,
    }


@app.get("/api/cases/{case_id}/approvals/{version}")
def approval_snapshot(case_id: str, version: int):
    with store.connect() as db:
        c = store.get(db, case_id)
    for event in c["history"]:
        if event.get("snapshot", {}).get("version") == version:
            return event["snapshot"]
    raise KeyError(version)


@app.get("/api/attachments/{attachment_id}")
def attachment(attachment_id: str):
    with store.connect() as db:
        row = db.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
        if not row:
            raise KeyError(attachment_id)
        return Response(
            bytes(row["data"]),
            media_type=row["mime"],
            headers={"Content-Disposition": 'inline; filename="evidence"'},
        )


@app.get("/api/export")
def export():
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(
        [
            "Case",
            "Supplier",
            "Invoice",
            "Status",
            "Reviewed INR",
            "Verified INR",
            "Remaining INR",
            "Follow up",
            "Synthetic",
        ]
    )
    for c in store.all_cases():
        p = present(c)

        # Protect spreadsheet consumers from formula injection in merchant-controlled strings.
        def safe(s):
            return (
                "'" + s if isinstance(s, str) and s[:1] in ("=", "+", "-", "@", "\t", "\r") else s
            )

        w.writerow(
            [
                safe(c["id"]),
                safe(c["invoice"]["supplier"]),
                safe(c["invoice"]["reference"]),
                c["status"],
                f"{(c['approved_amount_paise'] or 0) / 100:.2f}",
                f"{p['recovered_paise'] / 100:.2f}",
                f"{p['remaining_paise'] / 100:.2f}",
                c["follow_up"],
                c["synthetic"],
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="munafa-ledger.csv"'},
    )


# A built frontend can be served by the same loopback process.
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Endpoint not found")
        if path == "favicon.svg":
            return FileResponse(DIST / "favicon.svg")
        return FileResponse(DIST / "index.html")
