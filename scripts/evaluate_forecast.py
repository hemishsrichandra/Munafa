"""Offline time-holdout comparison. Does not enable app forecasts or place orders."""

import argparse
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    quantity: str = Field(pattern=r"^(0|[1-9][0-9]{0,10})(\.[0-9]{1,6})?$")
    coverage_confirmed: Literal[True]
    stockout: bool


class Series(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    mode: Literal["demo", "permissioned_evaluation"]
    protocol_id: str = Field(min_length=1, max_length=64)
    unit: Literal["piece", "pack", "carton", "kg"]
    minimum_training_periods: int = Field(strict=True, ge=2, le=3650)
    holdout_start: date
    periods: list[Period] = Field(min_length=3, max_length=7300)

    @model_validator(mode="after")
    def ordered(self):
        for prior, current in zip(self.periods, self.periods[1:]):
            if current.date != prior.date + timedelta(days=1):
                raise ValueError(
                    "Require contiguous ordered confirmed daily periods; never fill unknown gaps with zero."
                )
        return self


def evaluate(value):
    series = Series.model_validate(value)
    train = [r for r in series.periods if r.date < series.holdout_start]
    test = [r for r in series.periods if r.date >= series.holdout_start]
    if len(train) < series.minimum_training_periods or not test:
        raise ValueError("Insufficient declared training history or no holdout.")
    if any(r.stockout for r in series.periods):
        raise ValueError(
            "Stockout-censored demand requires a separately reviewed method; suppress this evaluation."
        )
    # Frozen origin: holdout observations cannot alter either prediction.
    naive = Decimal(train[-1].quantity)
    mean = sum(Decimal(r.quantity) for r in train) / len(train)
    actual = [Decimal(r.quantity) for r in test]
    errors = {
        name: sum(abs(y - estimate) for y in actual) / len(actual)
        for name, estimate in (("last_observed", naive), ("training_mean", mean))
    }
    return {
        "schema_version": 1,
        "mode": series.mode,
        "protocol_id": series.protocol_id,
        "unit": series.unit,
        "training_periods": len(train),
        "holdout_periods": len(test),
        "holdout_start": series.holdout_start.isoformat(),
        "predictions_per_day": {"last_observed": str(naive), "training_mean": str(mean)},
        "holdout_MAE_quantity": {k: str(v) for k, v in errors.items()},
        "comparison": "training_mean_lower_error"
        if errors["training_mean"] < errors["last_observed"]
        else "retain_naive_baseline",
        "production_enabled": False,
        "confidence_interval": None,
        "limitations": [
            "Single frozen-origin split, not evidence of generalisation or causal stockout improvement.",
            "No calibrated uncertainty, supplier lead time or purchase-order calculation.",
            "Coverage and permissions require source/human review; structural checks do not establish them.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.input.read_text()))
    except (ValueError, OSError):
        parser.exit(
            2,
            "Invalid or unreadable private series. Check coverage, units and protocol locally; input values are not logged.\n",
        )
    with args.output.open("x") as out:
        args.output.chmod(0o600)
        json.dump(result, out, indent=2)
        out.write("\n")
    print("Offline holdout report written. No app capability enabled.")


if __name__ == "__main__":
    main()
