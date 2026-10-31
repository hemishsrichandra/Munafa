"""Explicit, bounded AI draft endpoints; neither tools nor models execute business changes."""

import os
import time
from typing import Literal
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import Field
from . import auth, store, providers
from . import usage as provider_usage
from .domain import StrictModel, RuleError
from .security import rate_limit

router = APIRouter(prefix="/api/assistant")


@router.get("/capabilities")
def capabilities():
    principal = auth.current()
    allowed = (
        provider_usage.public_settings_enabled()
        if principal.public_demo
        else principal.provider_access
    )
    return {
        "cloud_configured": bool(os.getenv("SARVAM_API_KEY", "").strip()) and allowed,
        "public_demo_provider_access": principal.public_demo and allowed,
        "provider_access_allowed": allowed,
        "speech_preview": os.getenv("ENABLE_SPEECH_PREVIEW") == "1"
        and allowed
        and bool(os.getenv("SARVAM_API_KEY", "").strip()),
        "languages": ["en-IN", "hi-IN", "kn-IN"],
        "language_validation": "not_field_validated",
        "live_provider_tests_passed": False,
        "audio_retained": False,
        "default_path": "manual",
        "help_provider": "deterministic approved-source retrieval",
    }


class TranslationInput(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    target: providers.Language
    consent_to_provider: bool


@router.post("/translate")
def translate(body: TranslationInput):
    p = auth.current("messaging")
    if not body.consent_to_provider and body.target != "en-IN":
        raise HTTPException(422, "Confirm sharing this text with the speech/translation provider.")
    rate_limit(("ai", p.user_id), 10)
    start = time.monotonic()
    with store.connect() as db:
        try:
            result = providers.SarvamTranslation().translate(body.text, body.target)
        except RuleError:
            return {
                "source": body.text,
                "draft": None,
                "review_required": True,
                "warning": "Translation unavailable. Use the original text/manual entry.",
                "run_id": providers.telemetry(
                    db,
                    "translation",
                    providers.input_digest(body.text),
                    "provider_error",
                    start,
                    "mayura:v1",
                ),
            }
        result["run_id"] = providers.telemetry(
            db,
            "translation",
            providers.input_digest(body.text),
            "valid" if result["numeric_match"] else "invalid",
            start,
            "mayura:v1",
            provider=result["provider"],
        )
        return result


@router.post("/speech")
async def speech(
    file: UploadFile = File(...),
    language: providers.Language = Form("en-IN"),
    consent_to_provider: bool = Form(False),
):
    p = auth.current("write")
    if os.getenv("ENABLE_SPEECH_PREVIEW") != "1":
        raise HTTPException(
            503,
            "Speech is an unvalidated opt-in preview. Use text entry; see the language/device test matrix.",
        )
    if not consent_to_provider:
        raise HTTPException(
            422, "Explicit permission to send this audio for transcription is required."
        )
    rate_limit(("ai", p.user_id), 10)
    audio = await file.read(2 * 1024 * 1024 + 1)
    if not audio or len(audio) > 2 * 1024 * 1024:
        raise HTTPException(413, "Use a short recording under 2 MB.")
    mime = (file.content_type or "").split(";")[0]
    if mime not in ("audio/webm", "audio/ogg", "audio/wav", "audio/mp4"):
        raise HTTPException(415, "Use WebM, Ogg, WAV or MP4 audio; text entry is always available.")
    valid = (
        audio.startswith(b"\x1aE\xdf\xa3")
        if mime == "audio/webm"
        else audio.startswith(b"OggS")
        if mime == "audio/ogg"
        else audio.startswith(b"RIFF") and audio[8:12] == b"WAVE"
        if mime == "audio/wav"
        else audio[4:8] == b"ftyp"
    )
    if not valid:
        raise HTTPException(415, "Recording signature does not match its format. Use text entry.")
    from starlette.concurrency import run_in_threadpool

    started = time.monotonic()
    with store.connect() as db:
        try:
            result = await run_in_threadpool(
                providers.SarvamSpeech().transcribe, audio, mime, language
            )
        except RuleError:
            return {
                "transcript": None,
                "review_required": True,
                "warning": "Speech unavailable or unclear. Type your note instead.",
                "run_id": providers.telemetry(
                    db,
                    "speech",
                    providers.input_digest(audio),
                    "provider_error",
                    started,
                    "saaras:v3",
                ),
            }
        result["run_id"] = providers.telemetry(
            db, "speech", providers.input_digest(audio), "valid", started, result["model"]
        )
        return result


class HelpInput(StrictModel):
    question: str = Field(min_length=2, max_length=800)
    purpose: Literal["merchant_help"] = "merchant_help"
    tool: Literal["none", "case_read", "stock_read", "brief_read", "draft_followup"] = "none"
    entity_id: str | None = Field(default=None, max_length=64)


@router.post("/help")
def help_answer(body: HelpInput):
    from .help import answer

    with store.connect() as db:
        return answer(db, body)


@router.get("/sources/{source_id}")
def source_document(source_id: str):
    from .help import sources

    doc = next((d for d in sources() if d["id"] == source_id), None)
    if doc is None:
        raise KeyError(source_id)
    return doc


@router.get("/usage")
def usage():
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from . import models as m

    with store.connect() as db:
        rows = list(
            db.execute(
                select(m.ai_runs).where(
                    store.scope(m.ai_runs),
                    m.ai_runs.c.at >= datetime.now(timezone.utc) - timedelta(days=30),
                )
            ).mappings()
        )
        times = sorted(r["latency_ms"] for r in rows)
        return {
            "period_days": 30,
            "calls": len(rows),
            "valid_outputs": sum(r["status"] == "valid" for r in rows),
            "invalid_outputs": sum(r["status"] == "invalid" for r in rows),
            "unavailable_or_error": sum(
                r["status"] in ("unavailable", "provider_error") for r in rows
            ),
            "p50_latency_ms": times[(len(times) - 1) // 2] if times else None,
            "p95_latency_ms": times[max(0, __import__("math").ceil(len(times) * 0.95) - 1)]
            if times
            else None,
            "billed_cost_paise": sum(r["cost_paise"] for r in rows)
            if rows and all(r["cost_paise"] is not None for r in rows)
            else None,
            "cost_per_completed_task_paise": None,
            "note": "Valid output is not merchant acceptance. Billed cost and human task completion/time have not been measured. No raw inputs or responses are returned.",
        }
