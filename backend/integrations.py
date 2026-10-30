"""Internal contracts, not wire formats or evidence of provider access.

No public webhook or send endpoint is exposed without an authorised contract.
Existing payment ingestion and reconciliation remain the single financial path.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

from fastapi import APIRouter
from pydantic import AwareDatetime, Field

from . import auth
from .domain import StrictModel, RuleError
from .payments import PaymentEvent, SettlementBatch

router = APIRouter(prefix="/api/integrations")


def rupees_to_paise(value: str) -> int:
    """Only explicit decimal strings; no rounding, exponent or float ambiguity."""
    import re

    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,14}(\.[0-9]{1,2})?", value):
        raise RuleError(
            "Amount must be a non-negative rupee decimal string with at most two decimals."
        )
    try:
        result = int(Decimal(value) * 100)
    except (InvalidOperation, ValueError):
        raise RuleError("Invalid amount.") from None
    if result > 9000000000000000:
        raise RuleError("Amount exceeds supported range.")
    return result


class CommercePage(StrictModel):
    schema_version: Literal[1]
    mode: Literal["demo", "sandbox", "live"]
    provider: str = Field(min_length=1, max_length=40)
    window_start: AwareDatetime
    window_end: AwareDatetime
    next_cursor: str | None = Field(default=None, max_length=500)
    coverage_complete: bool
    events: list[PaymentEvent] = Field(max_length=1000)
    settlements: list[SettlementBatch] = Field(max_length=1000)


class DeviceObservation(StrictModel):
    """Trusted adapter must map a provider device to a store before persistence."""

    schema_version: Literal[1]
    source_event_id: str = Field(min_length=1, max_length=120)
    device_reference: str = Field(min_length=1, max_length=120)
    mode: Literal["demo", "sandbox", "live"]
    reported_status: Literal["online", "offline", "fault", "unknown"]
    reported_at: AwareDatetime


def device_state(observation: DeviceObservation | None, now=None):
    if observation is None:
        return {"status": "unavailable", "alert": False, "reported_at": None}
    now = now or datetime.now(timezone.utc)
    stale = not timedelta(0) <= now - observation.reported_at <= timedelta(hours=24)
    return {
        "status": observation.reported_status,
        "reported_at": observation.reported_at,
        "stale": stale,
        "alert": not stale and observation.reported_status in ("offline", "fault"),
        "freshness_policy": "24h advisory only; provider SLA not configured",
    }


class CommerceAdapter(Protocol):
    def fetch_page(self, start: datetime, end: datetime, cursor: str | None) -> CommercePage: ...


class MessageDraft(StrictModel):
    schema_version: Literal[1]
    recipient: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    language: Literal["en", "hi", "kn"]
    purpose: Literal["supplier_recovery", "receivable_reminder"]
    text: str = Field(min_length=1, max_length=4000)
    consent_id: str = Field(min_length=1, max_length=64)


class DisabledConnector:
    """Fail closed even if a caller supplies arbitrary credentials or flags."""

    def execute(self, *args, **kwargs):
        raise RuleError("BLOCKED — ACCESS: authorised contract and verified connector required.")

    def verify_webhook(self, body: bytes, headers: dict) -> bool:
        return False


CAPABILITIES = (
    (
        "paytm",
        "Paytm payments and settlements",
        "BLOCKED — ACCESS",
        [
            "Authorised merchant/product mapping and server-side access",
            "Confirmed production contract, authentication and enabled API capabilities",
            "Provider webhook/replay and pagination specifications; successful authorised contract test",
        ],
    ),
    (
        "devices",
        "Soundbox / POS telemetry",
        "BLOCKED — SPECIFICATION",
        [
            "Authorised device inventory and telemetry contract with trusted store mapping",
            "Provider timestamps, status meanings and reporting SLA",
        ],
    ),
    (
        "whatsapp",
        "WhatsApp Business messages",
        "BLOCKED — ACCESS",
        [
            "Approved WABA, registered number, pinned API version and server credentials",
            "Approved templates, current channel policy and authenticated webhook contract",
            "Purpose-specific contact consent, revocation and exact-recipient/content approval",
        ],
    ),
    (
        "lender",
        "Lending partner",
        "BLOCKED — ACCESS",
        [
            "Named authorised lender, product/disclosures, versioned API and approved document checklist",
            "Partner data-processing, consent, retention and submission review",
        ],
    ),
    (
        "gst",
        "GST / IRP filing",
        "BLOCKED — LEGAL/CONSENT",
        [
            "Qualified CA review of preparation output",
            "Authorised taxpayer/IRP access, current schema and sandbox contract",
            "Exact-payload approval and official acknowledgement contract",
        ],
    ),
)


@router.get("/status")
def status():
    p = auth.current()
    return {
        "mode": "demo" if p.demo else "live",
        "checked_at": datetime.now(timezone.utc),
        "private_cache_policy": "No API response caching; connection required to refresh.",
        "capabilities": [
            {
                "id": key,
                "label": label,
                "status": state,
                "connected": False,
                "last_successful_sync": None,
                "coverage_window": None,
                "external_execution_enabled": False,
                "missing": missing,
            }
            for key, label, state, missing in CAPABILITIES
        ],
        "available_paths": [
            {"label": "Synthetic settlement fixtures", "status": "DEMO ONLY"},
            {"label": "WhatsApp deep link", "status": "Manual handoff; delivery unverified"},
        ],
    }
