"""Offline, minimised pilot analysis. Never calls a provider or reads application DB.

Input is a private JSON document matching Dataset. No free text, contacts, document
contents or raw merchant IDs accepted. This validates structure, not legal consent.
Revoked/expired participants are excluded from every result. Outputs must remain
private; small-cohort reports are not public anonymised benchmarking.
"""

import argparse
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Participant(Strict):
    participant_id: str = Field(pattern=r"^pilot_[a-f0-9]{12}$")
    consent_version: Literal["pilot-v1"]
    consented_at: AwareDatetime
    expires_at: AwareDatetime
    revoked_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        if not self.consented_at < self.expires_at <= self.consented_at + timedelta(days=30):
            raise ValueError("Pilot permission must expire within 30 days.")
        if self.revoked_at and self.revoked_at < self.consented_at:
            raise ValueError("Withdrawal cannot precede consent.")
        return self


class Observation(Strict):
    operation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    participant_id: str = Field(pattern=r"^pilot_[a-f0-9]{12}$")
    task: Literal["invoice", "receiving", "reconciliation", "supplier_followup"]
    method: Literal["manual_baseline", "touch", "voice", "assisted"]
    at: AwareDatetime
    completed: bool
    abandoned: bool
    active_ms: int = Field(ge=0, le=86400000, strict=True)
    correction_ms: int = Field(ge=0, le=86400000, strict=True)
    fields_reviewed: int = Field(ge=0, le=10000, strict=True)
    fields_corrected: int = Field(ge=0, le=10000, strict=True)
    negative: Literal[
        "none", "false_alert", "sync_conflict", "data_loss", "wrong_extraction", "support_needed"
    ]

    @model_validator(mode="after")
    def consistent(self):
        if self.completed and self.abandoned:
            raise ValueError("Completed and abandoned are exclusive.")
        if self.fields_corrected > self.fields_reviewed:
            raise ValueError("Corrections cannot exceed reviewed fields.")
        return self


class Dataset(Strict):
    schema_version: Literal[1]
    mode: Literal["demo", "pilot"]
    protocol_version: Literal["pilot-v1"]
    observed_until: AwareDatetime
    participants: list[Participant] = Field(max_length=1000)
    observations: list[Observation] = Field(max_length=100000)


def analyse(value):
    data = Dataset.model_validate(value)
    participants = {p.participant_id: p for p in data.participants}
    if len(participants) != len(data.participants):
        raise ValueError("Duplicate participant.")
    seen, eligible = {}, []
    for row in data.observations:
        payload = row.model_dump(mode="json")
        if row.operation_id in seen:
            if seen[row.operation_id] != payload:
                raise ValueError("Operation ID replay contains changed data.")
            continue
        seen[row.operation_id] = payload
        participant = participants.get(row.participant_id)
        if participant is None:
            raise ValueError("Observation without participant permission record.")
        if row.at > data.observed_until:
            raise ValueError("Future observation beyond report cutoff.")
        if participant.revoked_at or participant.expires_at <= data.observed_until:
            continue
        if not participant.consented_at <= row.at < participant.expires_at:
            raise ValueError("Observation outside permission period.")
        eligible.append(row)
    groups = {}
    for row in eligible:
        groups.setdefault((row.task, row.method), []).append(row)
    metrics = []
    for (task, method), rows in sorted(groups.items()):
        completed = [r for r in rows if r.completed]
        reviewed = sum(r.fields_reviewed for r in rows)
        metrics.append(
            {
                "task": task,
                "method": method,
                "observations": len(rows),
                "completed": len(completed),
                "abandoned": sum(r.abandoned for r in rows),
                "mean_correction_adjusted_completed_ms": str(
                    sum(Decimal(r.active_ms + r.correction_ms) for r in completed) / len(completed)
                )
                if completed
                else None,
                "field_correction_rate": str(
                    Decimal(sum(r.fields_corrected for r in rows)) / reviewed
                )
                if reviewed
                else None,
                "negative_outcomes": {
                    key: sum(r.negative == key for r in rows)
                    for key in (
                        "false_alert",
                        "sync_conflict",
                        "data_loss",
                        "wrong_extraction",
                        "support_needed",
                    )
                },
            }
        )
    # Elapsed complete seven-day windows, relative to explicit consent, not arbitrary
    # calendar-week cutoffs. Task completion required; screen views are not useful use.
    return_eligible, returned = 0, 0
    for participant in participants.values():
        if participant.revoked_at or participant.expires_at <= data.observed_until:
            continue
        if data.observed_until - participant.consented_at < timedelta(days=14):
            continue
        weeks = {
            int((r.at - participant.consented_at).total_seconds() // 604800)
            for r in eligible
            if r.participant_id == participant.participant_id and r.completed
        }
        if 0 in weeks:
            return_eligible += 1
            returned += int(1 in weeks)
    return {
        "schema_version": 1,
        "mode": data.mode,
        "status": "NOT YET AVAILABLE" if not eligible else "DESCRIPTIVE OBSERVATIONS ONLY",
        "report_cutoff": data.observed_until.isoformat(),
        "metrics": metrics,
        "deduplicated_observations": len(eligible),
        "repeat_use": {
            "week_1_active_with_two_complete_weeks": return_eligible,
            "week_2_returned": returned,
            "rate": str(Decimal(returned) / return_eligible) if return_eligible else None,
        },
        "impact_claim": None,
        "causal_lift": None,
        "limitations": [
            "No causal or representative-population inference; no verified recovery metric from task observations.",
            "Consent evidence requires human review; structural validation does not establish lawful permission.",
            "Local reports are private, not privacy-reviewed cohort releases.",
            "Task active_ms excludes correction_ms; both measured independently, no invented missing timings.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = analyse(json.loads(args.input.read_text()))
    except (ValueError, OSError):
        parser.exit(
            2,
            "Invalid or unreadable private dataset. Check the protocol/schema locally; input values are not logged.\n",
        )
    # Avoid accidentally replacing an existing research report.
    with args.output.open("x", encoding="utf-8") as output:
        args.output.chmod(0o600)
        json.dump(result, output, indent=2)
        output.write("\n")
    print("Private descriptive report written; no provider called, no impact claim generated.")


if __name__ == "__main__":
    main()
