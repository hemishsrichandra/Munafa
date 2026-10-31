import csv
import hashlib
import io
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from . import store, ai, auth, actions
from .sync import router as sync_router
from .commerce_api import router as commerce_router
from .payments import router as payments_router
from .brief import router as brief_router
from .ai_api import router as ai_router
from .planning import router as planning_router
from .integrations import router as integrations_router
from .preparation import router as preparation_router
from .intelligence import router as intelligence_router
from .records import router as records_router
from .supplier_performance import router as supplier_performance_router
from .db import engine
from .security import guard, origins
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
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
    rupees,
)
from .samples import sample_invoice


@asynccontextmanager
async def lifespan(app):
    auth.development_login()
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    expected = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    with engine().connect() as db:
        if db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != expected:
            raise RuntimeError("Database migrations must be applied before startup.")
    yield


app = FastAPI(title="Paytm Business Partner · Munafa API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token",
        "Idempotency-Key",
        "Authorization",
        "X-Client-Platform",
    ],
)
app.middleware("http")(guard)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Pydantic's default error includes submitted `input`, which may be a secret,
    # customer contact or document. Keep only field locations and safe messages.
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
            ]
        },
    )


@app.exception_handler(ValidationError)
async def invalid_proposal(request, exc):
    # Nested proposal schema validation occurs inside service adapters too.
    return JSONResponse(
        status_code=422,
        content={
            "detail": "The proposal has invalid fields. Review the source and enter corrected values manually."
        },
    )


@app.exception_handler(RuleError)
async def rules(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(KeyError)
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Case or attachment not found."})


def identifier():
    return "MNF-" + uuid.uuid4().hex.upper()


def insert_invoice(invoice, synthetic=False, attachment=None, reuse_sample=False):
    try:
        date.fromisoformat(invoice["date"])
    except ValueError:
        raise RuleError("Enter a valid invoice date.")
    c = new_case(invoice, identifier(), auth.current().demo)
    with store.connect() as db:
        # Serialise the fixed sample without weakening generic invoice duplication guards.
        if reuse_sample:
            key = int.from_bytes(
                hashlib.sha256((auth.current().store_id + ":sample:A-104").encode()).digest()[:8],
                "big",
                signed=True,
            )
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        # A duplicated supplier invoice must be reviewed in the existing case.
        for old in store.all_cases(db):
            if normalized(old["invoice"]["supplier"]) == normalized(
                invoice["supplier"]
            ) and normalized(old["invoice"]["reference"]) == normalized(invoice["reference"]):
                if reuse_sample and auth.current().demo and old["synthetic"]:
                    return {**present(old), "sample_reused": True}
                raise RuleError(f"Invoice already exists in {old['id']}. Open the existing case.")
        store.save(db, c)
        if attachment:
            aid = store.add_attachment(db, c["id"], attachment[0], attachment[1], attachment[2])
            c["attachment_id"] = aid
            store.save(db, c)
    return present(c)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "sarvam_configured": ai.configured(),
        "speech_preview": os.getenv("ENABLE_SPEECH_PREVIEW") == "1",
        "vision_model": os.getenv("SARVAM_VISION_MODEL", "gemma4"),
        "chat_model": os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b"),
        "mode": "merchant workspace",
        "development_login": auth.development_login(),
        "public_signup": auth.public_signup_enabled(),
        "public_demo": auth.public_demo_enabled(),
    }


@app.get("/api/cases")
def cases():
    from .purchasing import case_link

    with store.connect() as db:
        result = []
        for c in store.all_cases(db):
            value = present(c)
            link = case_link(db, c["id"])
            if link:
                value["commerce_link"] = link
            result.append(value)
        return result


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    with store.connect() as db:
        c = present(store.get(db, case_id))
        from .purchasing import case_link

        link = case_link(db, case_id)
        if link:
            c["commerce_link"] = link
        return c


@app.post("/api/invoices/sample", status_code=201)
def sample():
    if not auth.current("write").demo:
        raise HTTPException(403, "Synthetic invoices require an isolated demo store.")
    return insert_invoice(sample_invoice(), True, reuse_sample=True)


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
    validate_file(data, mime, proof)
    return data, mime


def validate_file(data, mime, proof=False):
    if not data or len(data) > 8 * 1024 * 1024:
        raise RuleError("Choose a non-empty file smaller than 8 MB.")
    valid = (
        (mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
        or (mime == "image/webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )
    if proof and mime == "application/pdf" and data.startswith(b"%PDF-"):
        valid = True
    if valid and mime == "application/pdf":
        # Reject obvious active content. This is not antivirus/content disarm and
        # does not establish safety for arbitrary PDF syntax or encoded objects.
        import re

        if re.search(
            rb"/(?:JavaScript|JS|Launch|EmbeddedFile|OpenAction|RichMedia|XFA)\b", data, re.I
        ):
            raise RuleError(
                "Active or embedded PDF content is unsupported. Use a static image or a safe document."
            )
    if not valid:
        raise RuleError("Use a PNG, JPEG or WebP image" + (" or PDF proof." if proof else "."))


@app.post("/api/invoices/extract", status_code=201)
async def extract_image(file: UploadFile = File(...)):
    data, mime = await read_file(file)
    # Run blocking provider I/O outside the event loop.
    from starlette.concurrency import run_in_threadpool

    invoice = await run_in_threadpool(ai.extract, image=data, mime=mime)
    return insert_invoice(invoice, attachment=(file.filename or "invoice", mime, data))


@app.patch("/api/cases/{case_id}/review")
def review(case_id: str, body: Review):
    from .purchasing import require_legacy_edit_allowed

    with store.connect() as db:
        require_legacy_edit_allowed(db, case_id)
    with store.mutate(case_id, body.version) as (db, c):
        if c["resolutions"]:
            raise RuleError(
                "A case with recorded recovery cannot be edited. Keep the original evidence and review any additional issue separately."
            )
        try:
            date.fromisoformat(body.invoice.date)
        except ValueError:
            raise RuleError("Enter a valid invoice date.")
        for old in store.all_cases(db):
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
    with store.mutate(case_id, body.version, "approve") as (db, c):
        proposal = actions.propose(db, "approve_case", case_id, {}, body.version, store.uid())
        proposal = actions.approve(
            db, proposal["id"], proposal["version"], proposal["payload_digest"]
        )
        actions.consume(db, proposal["id"], proposal["version"])
        actions.executed(db, proposal)
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
            f"INR {rupees(calc['amount_paise'])} reviewed by the merchant.",
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
    with store.connect("write") as db:
        aid = store.add_attachment(db, case_id, file.filename or "proof", mime, data)
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
        evidence = f"SYNTHETIC EVIDENCE\nSupplier: {c['invoice']['supplier']}\nInvoice: {c['invoice']['reference']}\nReference: {ref}\n{body.kind}: INR {rupees(amount)}"
        aid = store.add_attachment(db, case_id, ref + ".txt", "text/plain", evidence.encode())
        result = {
            "attachment_id": aid,
            "supplier": c["invoice"]["supplier"],
            "invoice_reference": c["invoice"]["reference"],
            "evidence_reference": ref,
            "amount_paise": amount,
            "kind": body.kind,
            "synthetic": True,
        }
        from sqlalchemy import update
        from .models import attachments

        db.execute(
            update(attachments)
            .where(store.scope(attachments), attachments.c.id == aid)
            .values(synthetic_fields=result)
        )
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
        attachment = store.attachment(db, body.attachment_id, case_id)
        if not attachment:
            raise RuleError(
                "Attach credit or refund proof belonging to this case before closing it."
            )
        if not c["synthetic"] and attachment["mime"] == "text/plain":
            raise RuleError("Synthetic evidence cannot close a merchant invoice.")
        if store.proof_used(db, body.supplier, digest=attachment["digest"]):
            raise RuleError("This evidence file has already been counted.")
        if store.proof_used(db, body.supplier, reference=body.evidence_reference):
            raise RuleError("This supplier evidence reference has already been counted.")
        fields = attachment["synthetic_fields"]
        if fields and any(
            body.model_dump()[key] != fields[key]
            for key in (
                "kind",
                "supplier",
                "invoice_reference",
                "evidence_reference",
                "amount_paise",
            )
        ):
            raise RuleError("The entered resolution does not match the synthetic evidence.")
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
            f"INR {rupees(body.amount_paise)} recorded against {body.evidence_reference}; INR {rupees(remaining)} remaining.",
        )
    return present(c)


def message(c):
    p = present(c)
    lines = [
        f"Hello, please review the delivery shortage on invoice {c['invoice']['reference']} ({c['invoice']['date']})."
    ]
    for index, line in enumerate(c["invoice"]["lines"]):
        from decimal import Decimal

        short = Decimal(str(line["billed"])) - Decimal(str(line["received"]))
        if short:
            lines.append(
                f"{line['name']}: {line['billed']} billed, {line['received']} received ({line['unit']}). {short} x INR {rupees(line['price_paise'])} = INR {rupees(p['calculation']['lines'][index]['amount_paise'])}."
            )
    lines.append(
        f"Total reviewed shortage: INR {rupees(c['approved_amount_paise'])}. Please issue a credit note referencing this invoice and confirm when applied, or refund the amount. Thank you."
    )
    if c["resolutions"]:
        lines.append(
            f"Already verified: INR {rupees(p['recovered_paise'])}. Remaining: INR {rupees(p['remaining_paise'])}."
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
    from .providers import numeric_tokens

    match = numeric_tokens(original) == numeric_tokens(translated)
    return {
        "text": translated,
        "numeric_match": match,
        "review_required": True,
        "warning": None
        if match
        else "Numeric/reference mismatch: use the original or correct manually.",
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
        row = store.attachment(db, attachment_id)
        if not row:
            raise KeyError(attachment_id)
        return Response(
            bytes(row["data"]),
            media_type=row["mime"],
            headers={"Content-Disposition": 'attachment; filename="evidence"'},
        )


@app.get("/api/export")
def export(action_id: str):
    with store.connect("export") as db:
        # Validation and CSV rendering must share a consistent ledger snapshot,
        # even when another request creates/edits a case after approval checking.
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        approved = actions.get(db, action_id)
        if (
            approved["action_type"] != "export_ledger"
            or approved["status"] != "executed"
            or approved["created_by"] != auth.current().user_id
        ):
            raise HTTPException(403, "Approve this ledger export first.")
        if approved["expires_at"] <= __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ):
            raise HTTPException(403, "Export approval expired.")
        if approved["payload"] != actions.export_payload(db):
            raise RuleError("Ledger changed after approval. Approve a fresh export.")
        store.audit_record(db, action_id, "Ledger downloaded", entity_type="export")
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
                "'" + s
                if isinstance(s, str)
                and (s[:1] in ("\t", "\r", "\n") or s.lstrip()[:1] in ("=", "+", "-", "@"))
                else s
            )

        w.writerow(
            [
                safe(c["id"]),
                safe(c["invoice"]["supplier"]),
                safe(c["invoice"]["reference"]),
                c["status"],
                rupees(c["approved_amount_paise"] or 0),
                f"{rupees(p['recovered_paise'])}",
                f"{rupees(p['remaining_paise'])}",
                c["follow_up"],
                c["synthetic"],
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="munafa-ledger.csv"'},
    )


# These routes precede the frontend catch-all in registration order below.
class LoginBody(StrictModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class DemoBody(StrictModel):
    code: str = Field(min_length=16, max_length=200)


def login_response(result, request):
    p, token, csrf = result
    secure = os.getenv("APP_ENV", "production") == "production"
    response = JSONResponse(
        {
            **(
                {"session_token": token}
                if request.headers.get("x-client-platform") == "android"
                else {}
            ),
            "user_id": p.user_id,
            "csrf": csrf,
            "store": {
                "id": p.store_id,
                "name": p.store_name,
                "demo": p.demo,
                "timezone": p.timezone,
            },
            "role": p.role,
            "permissions": sorted(auth.PERMISSIONS[p.role]),
        }
    )
    response.set_cookie(
        "pbp_session",
        token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=43200,
        path="/api",
    )
    response.set_cookie(
        "pbp_csrf", csrf, httponly=False, secure=secure, samesite="strict", max_age=43200, path="/"
    )
    return response


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request):
    return login_response(auth.login(body.username, body.password), request)


class SignupBody(StrictModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    store_name: str = Field(min_length=1, max_length=120)


@app.post("/api/auth/signup", status_code=201)
def signup(body: SignupBody, request: Request):
    response = login_response(auth.signup(body.username, body.password, body.store_name), request)
    response.status_code = 201
    return response


class PublicDemoBody(StrictModel):
    pass


@app.post("/api/auth/demo", status_code=201)
def public_demo(body: PublicDemoBody, request: Request):
    response = login_response(auth.public_demo(), request)
    response.status_code = 201
    return response


@app.post("/api/auth/dev-login")
def dev_login(body: DemoBody, request: Request):
    return login_response(auth.demo_login(body.code), request)


@app.get("/api/auth/me")
def me(request: Request):
    p = auth.current()
    return {
        "user_id": p.user_id,
        "csrf": request.cookies.get("pbp_csrf", ""),
        "role": p.role,
        "permissions": sorted(auth.PERMISSIONS[p.role]),
        "store": {"id": p.store_id, "name": p.store_name, "demo": p.demo, "timezone": p.timezone},
    }


@app.post("/api/auth/logout")
def logout(request: Request):
    header = request.headers.get("authorization", "")
    auth.revoke(
        header[7:] if header.startswith("Bearer ") else request.cookies.get("pbp_session", "")
    )
    response = JSONResponse({"ok": True})
    response.delete_cookie("pbp_session", path="/api")
    response.delete_cookie("pbp_csrf", path="/")
    return response


class ProposalBody(StrictModel):
    action_type: Literal["approve_case", "export_ledger"]
    entity_id: str = ""
    expected_version: int = 0


class ActionApproval(StrictModel):
    version: int
    payload_digest: str


class ActionRevision(StrictModel):
    version: int
    payload: dict


@app.post("/api/actions", status_code=201)
def propose_action(body: ProposalBody, request: Request):
    with store.connect("write") as db:
        return actions.propose(
            db,
            body.action_type,
            body.entity_id,
            {},
            body.expected_version,
            request.headers["idempotency-key"],
        )


@app.get("/api/actions/{action_id}")
def get_action(action_id: str):
    with store.connect() as db:
        return actions.get(db, action_id)


@app.patch("/api/actions/{action_id}")
def revise_action(action_id: str, body: ActionRevision):
    with store.connect("write") as db:
        return actions.revise(db, action_id, body.version, body.payload)


@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: str, body: ActionApproval):
    with store.connect("approve") as db:
        return actions.approve(db, action_id, body.version, body.payload_digest)


@app.post("/api/actions/{action_id}/execute")
def execute_action(action_id: str, body: Version, request: Request):
    with store.connect("approve") as db:
        a = actions.consume(db, action_id, body.version)
        if a["action_type"] == "approve_case":
            c = store.get(db, a["entity_id"], True)
            payload = {
                "invoice": c["invoice"],
                "delivery_complete": c["delivery_complete"],
                "pricing_confirmed": c["pricing_confirmed"],
            }
            if (
                c["version"] != a["expected_version"]
                or actions.payload_digest(payload) != a["payload_digest"]
            ):
                raise RuleError("Approved source changed. Create a new proposal.")
            result = approve(c["id"], Version(version=c["version"]))
        elif a["action_type"] in ("accept_purchase", "accept_receiving", "inventory_movement"):
            from .commerce_api import execute

            return execute(db, a, request.headers["idempotency-key"])
        elif a["action_type"] == "export_preparation":
            from .preparation import revalidate

            auth.current("export")
            if (
                a["created_by"] != auth.current().user_id
                or a["approved_by"] != auth.current().user_id
            ):
                raise HTTPException(403, "Review your own preparation export.")
            revalidate(db, a)
            result = {"download_url": f"/api/preparation/export?action_id={a['id']}"}
        else:
            auth.current("export")
            if a["payload"] != actions.export_payload(db):
                raise RuleError("Invalid ledger export scope.")
            result = {"download_url": f"/api/export?action_id={a['id']}"}
        actions.executed(db, a)
    return result


# A built frontend can be served by the same loopback process.

app.include_router(sync_router)
app.include_router(commerce_router)
app.include_router(payments_router)
app.include_router(brief_router)
app.include_router(ai_router)
app.include_router(planning_router)
app.include_router(integrations_router)
app.include_router(preparation_router)
app.include_router(intelligence_router)
app.include_router(records_router)
app.include_router(supplier_performance_router)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (DIST / "assets").is_dir() and (DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Endpoint not found")
        if path in ("favicon.svg", "sw.js", "manifest.webmanifest") or path in (
            "icons/icon-192.png",
            "icons/icon-512.png",
            "icons/maskable-512.png",
        ):
            return FileResponse(
                DIST / path, headers={"Cache-Control": "no-cache"} if path == "sw.js" else None
            )
        return FileResponse(DIST / "index.html")
