"""Exact proposal approval, with server-side execution of narrowly supported actions."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, insert, update
from . import models as m, store
from .auth import current
from .domain import RuleError


def payload_digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def propose(db, action_type, entity_id, payload, expected_version, key):
    p = current("write")
    if action_type not in (
        "approve_case",
        "export_ledger",
        "accept_purchase",
        "accept_receiving",
        "inventory_movement",
    ):
        raise RuleError("Unsupported action type.")
    if action_type == "approve_case":
        c = store.get(db, entity_id)
        if c["version"] != expected_version:
            raise RuleError("Proposal source is stale.")
        payload = {
            "invoice": c["invoice"],
            "delivery_complete": c["delivery_complete"],
            "pricing_confirmed": c["pricing_confirmed"],
        }
    elif action_type == "export_ledger":
        payload = export_payload(db)
    else:
        from .commerce_api import action_payload

        payload = action_payload(db, action_type, entity_id, expected_version, payload)
    aid = store.uid()
    db.execute(
        insert(m.actions).values(
            id=aid,
            store_id=p.store_id,
            action_type=action_type,
            entity_id=entity_id,
            payload=payload,
            payload_digest=payload_digest(payload),
            risk_level="financial" if action_type == "approve_case" else "private",
            source_ids=[entity_id] if entity_id else [],
            status="proposed",
            version=1,
            expected_version=expected_version,
            idempotency_key=key,
            created_by=p.user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
    )
    store.audit_record(db, aid, "Action proposed", new=1, entity_type="assistant_action")
    return get(db, aid)


def get(db, aid, lock=False):
    q = select(m.actions).where(store.scope(m.actions), m.actions.c.id == aid)
    row = db.execute(q.with_for_update() if lock else q).mappings().first()
    if not row:
        raise KeyError(aid)
    return dict(row)


def approve(db, aid, version, digest):
    p = current("approve")
    a = get(db, aid, True)
    if (
        a["version"] != version
        or a["status"] != "proposed"
        or a["payload_digest"] != digest
        or payload_digest(a["payload"]) != digest
    ):
        raise RuleError("Approval must match the exact current proposal and payload digest.")
    if a["expires_at"] <= datetime.now(timezone.utc):
        raise RuleError("Proposal expired. Create a new proposal.")
    db.execute(
        update(m.actions)
        .where(store.scope(m.actions), m.actions.c.id == aid)
        .values(
            status="approved",
            approved_by=p.user_id,
            approved_at=datetime.now(timezone.utc),
            approved_digest=digest,
            version=version + 1,
        )
    )
    store.audit_record(
        db, aid, "Action approved", version, version + 1, entity_type="assistant_action"
    )
    return get(db, aid)


def revise(db, aid, version, payload):
    current("write")
    a = get(db, aid, True)
    if a["version"] != version or a["status"] == "executed":
        raise RuleError("The action is stale or already executed.")
    # Revisions are proposals only; execution also verifies current authoritative source.
    db.execute(
        update(m.actions)
        .where(store.scope(m.actions), m.actions.c.id == aid)
        .values(
            payload=payload,
            payload_digest=payload_digest(payload),
            status="proposed",
            approved_by=None,
            approved_at=None,
            approved_digest=None,
            version=version + 1,
        )
    )
    store.audit_record(
        db,
        aid,
        "Action revised; approval invalidated",
        version,
        version + 1,
        entity_type="assistant_action",
    )
    return get(db, aid)


def consume(db, aid, version):
    a = get(db, aid, True)
    current("export" if a["action_type"] == "export_ledger" else "approve")
    if (
        a["version"] != version
        or a["status"] != "approved"
        or a["expires_at"] <= datetime.now(timezone.utc)
        or a["approved_digest"] != payload_digest(a["payload"])
    ):
        raise RuleError("The approved proposal is stale, expired or changed.")
    return a


def executed(db, a):
    db.execute(
        update(m.actions)
        .where(store.scope(m.actions), m.actions.c.id == a["id"])
        .values(status="executed", version=a["version"] + 1)
    )
    store.audit_record(
        db,
        a["id"],
        "Action executed",
        a["version"],
        a["version"] + 1,
        entity_type="assistant_action",
    )


def export_payload(db):
    return {
        "scope": "current_store_ledger",
        "versions": sorted([[c["id"], c["version"]] for c in store.all_cases(db)]),
    }
