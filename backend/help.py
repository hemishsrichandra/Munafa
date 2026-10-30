"""Extractive approved-source retrieval with allow-listed principal-scoped read tools."""

import json
import re
from pathlib import Path
from datetime import date
from . import auth, store, inventory
from .domain import present, RuleError

SOURCES = Path(__file__).with_name("knowledge") / "product-v1.json"


def sources():
    return json.loads(SOURCES.read_text())["documents"]


def answer(db, body):
    auth.current("read")
    question = body.question.casefold()
    # No user-supplied URLs, tool names or instructions enter a model context.
    tokens = set(re.findall(r"[a-z]+", question))
    docs = sources()
    matches = [(len(tokens & set(d["keywords"])), d) for d in docs]
    matches = [d for score, d in sorted(matches, key=lambda x: (-x[0], x[1]["id"])) if score][:3]
    today = date.today().isoformat()
    stale = any(d["valid_until"] < today for d in matches)
    contradictions = len({d["text"] for d in matches if d.get("contradiction_group")}) > 1
    unsupported = (
        not matches
        or stale
        or contradictions
        or bool(tokens & {"guarantee", "guaranteed", "loan", "eta", "legal", "rate", "policy"})
    )
    retrieved = (
        []
        if unsupported
        else [
            {
                "document_id": d["id"],
                "version": d["version"],
                "title": d["title"],
                "section": d["section"],
                "kind": d["kind"],
                "text": d["text"],
                "citation": d.get("url") or "/api/assistant/sources/" + d["id"],
                "reviewed_at": d["reviewed_at"],
                "valid_until": d["valid_until"],
            }
            for d in matches
        ]
    )
    facts = []
    draft_action = None
    if body.tool in ("case_read", "draft_followup"):
        if not body.entity_id:
            raise RuleError("Choose a case source record.")
        c = present(store.get(db, body.entity_id))
        facts = [
            {
                "source_entity_ids": [c["id"]],
                "source_label": "Invoice " + c["invoice"]["reference"],
                "route": "/cases/" + c["id"],
                "status": c["status"],
                "remaining_paise": c["remaining_paise"],
                "promise_recorded": bool(c["promise"]),
                "recovered_paise": c["recovered_paise"],
                "synthetic": c["synthetic"],
            }
        ]
        if body.tool == "draft_followup":
            auth.current("messaging")
            if c["approved_version"] is None:
                raise RuleError("Review and approve the source evidence first.")
            draft_action = {
                "type": "supplier_followup_draft",
                "source_entity_ids": [c["id"]],
                "expected_version": c["version"],
                "text": "Please review the approved delivery evidence and confirm the next step. A promise remains unverified until applied.",
                "review_required": True,
                "route": "/cases/" + c["id"],
                "execution": "none — open the source workflow to review, share and confirm explicitly",
            }
    elif body.tool == "stock_read":
        if not body.entity_id:
            raise RuleError("Choose a SKU source record.")
        p = inventory.product_view(db, inventory.product(db, body.entity_id))
        facts = [
            {
                "source_entity_ids": [p["id"]],
                "source_label": p["name"],
                "route": "/stock/" + p["id"],
                "stock_quantity": p["stock_quantity"],
                "unit": p["unit"],
                "expected_version": p["stock_version"],
                "synthetic": p["synthetic"],
            }
        ]
    elif body.tool == "brief_read":
        from .brief import build

        facts = [
            {"source_entity_ids": r["source_entity_ids"], "route": r["route"], "fact": r["reason"]}
            for r in build(db)["items"]
        ]
    # Missing/contradictory policy is not repaired with model speculation.
    return {
        "provider": "deterministic_retrieval",
        "purpose": "merchant_help",
        "retrieved_sources": retrieved,
        "merchant_facts": facts,
        "general_explanation": "These are cited source excerpts and recorded store facts, not a policy decision. Review the linked workflow before acting."
        if not unsupported
        else "No current, consistent approved source answers this question. No policy, fee, refund outcome or settlement cause can be established here.",
        "unsupported": unsupported,
        "stale": stale,
        "contradictory": contradictions,
        "support_route": "Open Business with Paytm → Help & Support for account-specific Paytm questions; use the Munafa workflow guide for product steps.",
        "draft_action": draft_action,
        "mutation_performed": False,
    }
