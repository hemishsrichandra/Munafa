"""Narrow proposal-only AI interfaces. No tool writes, tokens or business authority."""

import os
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import Protocol, Literal
import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert
from . import ai, auth, models as m, store
from .domain import RuleError

Language = Literal["en-IN", "hi-IN", "kn-IN"]


class DocumentProvider(Protocol):
    def extract(
        self, *, text: str | None, data: bytes | None, mime: str | None
    ) -> tuple[dict, dict]: ...


class SpeechProvider(Protocol):
    def transcribe(self, audio: bytes, mime: str, language: Language) -> dict: ...


class TranslationProvider(Protocol):
    def translate(self, text: str, target: Language) -> dict: ...


class ReasoningProvider(Protocol):
    def explain(self, facts: dict) -> dict: ...


class ProposalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    provider: str | None
    model: str | None
    review_required: Literal[True] = True
    coordinates: list[dict] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    language_validation: Literal["not_field_validated"] = "not_field_validated"


def telemetry(db, purpose, digest, status, started, model, usage=None, provider="sarvam"):
    p = auth.current()
    rid = store.uid()
    clean = {
        k: v
        for k, v in (usage or {}).items()
        if k in ("prompt_tokens", "completion_tokens", "total_tokens", "audio_seconds")
        and type(v) is int
        and v >= 0
    }
    db.execute(
        insert(m.ai_runs).values(
            id=rid,
            store_id=p.store_id,
            actor_id=p.user_id,
            purpose=purpose,
            input_digest=digest,
            provider=provider,
            model=model,
            status=status,
            latency_ms=max(0, int((time.monotonic() - started) * 1000)),
            usage=clean,
            cost_paise=None,
            at=datetime.now(timezone.utc),
        )
    )
    return rid


def input_digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def numeric_tokens(text):
    return re.findall(r"\d+(?:[.,]\d+)*", text)


class SarvamTranslation:
    def translate(self, text, target):
        if target == "en-IN":
            return {
                "source": text,
                "draft": text,
                "provider": "rules",
                "review_required": True,
                "numeric_match": True,
                "language": target,
            }
        translated = ai.translate(text, target)
        match = numeric_tokens(text) == numeric_tokens(translated)
        return {
            "source": text,
            "draft": translated,
            "provider": "sarvam",
            "model": "mayura:v1",
            "review_required": True,
            "numeric_match": match,
            "warning": None
            if match
            else "Numeric/reference mismatch. Do not share this translation; use the original or correct it manually.",
            "language": target,
            "language_validation": "not_field_validated",
        }


class SarvamSpeech:
    def transcribe(self, audio, mime, language):
        key = os.getenv("SARVAM_API_KEY")
        if not key:
            raise RuleError("Speech is not configured. Type your note instead.")
        model = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
        try:
            result = httpx.post(
                ai.BASE + "/speech-to-text",
                headers={"api-subscription-key": key},
                files={
                    "file": (
                        {
                            "audio/webm": "note.webm",
                            "audio/ogg": "note.ogg",
                            "audio/wav": "note.wav",
                            "audio/mp4": "note.m4a",
                        }[mime],
                        audio,
                        mime,
                    )
                },
                data={"model": model, "language_code": language, "mode": "transcribe"},
                timeout=httpx.Timeout(20, connect=5),
            )
            result.raise_for_status()
            value = result.json()
            transcript = value.get("transcript")
            if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 4000:
                raise ValueError("Invalid transcript")
            return {
                "transcript": transcript,
                "language": value.get("language_code", language),
                "provider": "sarvam",
                "model": model,
                "review_required": True,
                "language_validation": "not_field_validated",
                "warning": "Recognition may be wrong, especially in noise. Review this text; no business fields were changed.",
            }
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError, AttributeError):
            raise RuleError(
                "Speech was unavailable or unclear. No audio was saved. Type your note instead."
            ) from None


class SarvamDocument:
    def extract(self, *, text=None, data=None, mime=None):
        from .purchase_extraction import extract

        return extract(text=text, data=data, mime=mime)


class BoundedReasoning:
    def explain(self, facts):
        # Deterministic source explanations are the default until model evaluation wins.
        allowed = {"explanation", "source_entity_ids"}
        if set(facts) - allowed:
            raise RuleError("Unsupported explanation fields.")
        return {
            "explanation": facts.get("explanation", "No approved explanation is available."),
            "source_entity_ids": facts.get("source_entity_ids", []),
            "provider": "rules",
            "model": None,
        }


def guarded_extraction(call, *, text=None, data=None, mime=None):
    """Persistent invalid-output budget, including failed requests; no raw source telemetry.

    An independent transaction is intentional: an HTTP validation rollback must not
    erase the invalid-output counter. No inventory/financial write occurs here.
    """
    from sqlalchemy import select, func, text as sql_text
    from .db import engine
    from .commerce_models import PurchaseDraft

    p = auth.principal.get()
    if p is None:
        return call(text=text, data=data, mime=mime)
    from .security import rate_limit

    rate_limit(("ai", p.user_id), 10)
    digest = input_digest(data if data is not None else text or "")
    started = time.monotonic()
    with engine().begin() as db:
        lock = int.from_bytes(
            hashlib.sha256((p.store_id + "extract" + digest).encode()).digest()[:8],
            "big",
            signed=True,
        )
        db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
        count = db.execute(
            select(func.count())
            .select_from(m.ai_runs)
            .where(
                store.scope(m.ai_runs),
                m.ai_runs.c.purpose == "extraction",
                m.ai_runs.c.input_digest == digest,
                m.ai_runs.c.status == "invalid",
            )
        ).scalar()
        if count >= 2:
            return PurchaseDraft().model_dump(mode="json"), {
                "provider": None,
                "model": None,
                "review_required": True,
                "extraction_schema_version": 1,
                "manual_required": True,
                "invalid_attempts": count,
                "warning": "Two invalid structured outputs for this source. Automated extraction stopped; complete the manual draft.",
            }
        draft, meta = call(text=text, data=data, mime=mime)
        meta.setdefault("extraction_schema_version", 1)
        meta.setdefault("review_required", True)
        meta.setdefault("coordinates", None)
        meta.setdefault("confidence", None)
        status = meta.pop("failure_kind", None) or (
            "valid" if not meta.get("warning") else "unavailable"
        )
        rid = telemetry(
            db,
            "extraction",
            digest,
            status,
            started,
            meta.get("model") or "unconfigured",
            usage=meta.get("provider_reported_usage"),
            provider=meta.get("provider") or "none",
        )
        meta.update(
            run_id=rid,
            source_sha256=digest,
            manual_required=status != "valid",
            invalid_attempts=count + (status == "invalid"),
            fields={
                key: {
                    "review_state": "merchant_review_required"
                    if value not in (None, "")
                    else "missing",
                    "confidence": None,
                    "source_coordinates": None,
                }
                for key, value in draft.items()
                if key not in ("lines", "supplier_phone")
            },
        )
        return draft, meta
