import copy
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from backend.tests.test_commerce import purchase, receive, receiving
from backend.tests.test_trust import other_client
from scripts.analyse_pilot import analyse
from scripts.evaluate_forecast import evaluate


def test_readiness_never_infers_sales_from_invoice_or_receipt(client):
    p, product = purchase(client)
    receive(client, p, receiving(p, "2"))
    r = client.get("/api/intelligence/readiness")
    assert r.status_code == 200, r.text
    data = r.json()
    sku = data["products"][0]
    assert sku["product_id"] == product["id"] and sku["event_counts"] == {"receipt": 1}
    assert not sku["forecast_enabled"] and not sku["complete_sales_coverage"]
    assert sku["missing_intervals"] is None and sku["stockout_periods"] is None
    assert sku["observed_sales_period"]["distinct_days"] == 0
    assert data["benchmark"]["suppressed"] and data["pilot"]["measured_outcomes"] is None
    other, _ = other_client()
    assert other.get("/api/intelligence/readiness").json()["products"] == []


def dataset():
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    return {
        "schema_version": 1,
        "mode": "demo",
        "protocol_version": "pilot-v1",
        "observed_until": now.isoformat(),
        "participants": [
            {
                "participant_id": "pilot_abcdef123456",
                "consent_version": "pilot-v1",
                "consented_at": (now - timedelta(days=15)).isoformat(),
                "expires_at": (now + timedelta(days=5)).isoformat(),
            }
        ],
        "observations": [],
    }


def observation(days=1, operation="a" * 32):
    return {
        "operation_id": operation,
        "participant_id": "pilot_abcdef123456",
        "task": "invoice",
        "method": "touch",
        "at": (datetime(2026, 10, 15, tzinfo=timezone.utc) + timedelta(days=days)).isoformat(),
        "completed": True,
        "abandoned": False,
        "active_ms": 1000,
        "correction_ms": 200,
        "fields_reviewed": 10,
        "fields_corrected": 2,
        "negative": "wrong_extraction",
    }


def test_pilot_unknown_is_not_zero_and_duplicates_do_not_inflate():
    data = dataset()
    assert analyse(data)["status"] == "NOT YET AVAILABLE"
    assert analyse(data)["repeat_use"]["rate"] is None
    data["observations"] = [observation(), observation(), observation(8, "b" * 32)]
    result = analyse(data)
    assert result["deduplicated_observations"] == 2
    assert result["metrics"][0]["mean_correction_adjusted_completed_ms"] == "1200"
    assert result["metrics"][0]["field_correction_rate"] == "0.2"
    assert result["repeat_use"]["rate"] == "1" and result["impact_claim"] is None
    data["observations"][1] = {**observation(), "correction_ms": 500}
    with pytest.raises(ValueError, match="replay"):
        analyse(data)


@pytest.mark.parametrize("change", ["revoked", "expired"])
def test_withdrawal_excludes_all_measurements(change):
    data = dataset()
    data["observations"] = [observation()]
    if change == "revoked":
        data["participants"][0]["revoked_at"] = data["observed_until"]
    else:
        data["participants"][0]["expires_at"] = data["observed_until"]
    assert analyse(data)["metrics"] == []


@pytest.mark.parametrize(
    "patch",
    [{"phone": "private"}, {"active_ms": -1}, {"fields_corrected": 11}, {"abandoned": True}],
)
def test_pilot_rejects_pii_and_invalid_observations(patch):
    data = dataset()
    data["observations"] = [{**observation(), **patch}]
    with pytest.raises(ValidationError):
        analyse(data)


def series():
    return {
        "schema_version": 1,
        "mode": "demo",
        "protocol_id": "SYNTHETIC-TEST",
        "unit": "kg",
        "minimum_training_periods": 2,
        "holdout_start": "2026-10-03",
        "periods": [
            {
                "date": "2026-10-01",
                "quantity": "1.5",
                "coverage_confirmed": True,
                "stockout": False,
            },
            {
                "date": "2026-10-02",
                "quantity": "2.5",
                "coverage_confirmed": True,
                "stockout": False,
            },
            {"date": "2026-10-03", "quantity": "2", "coverage_confirmed": True, "stockout": False},
        ],
    }


def test_time_split_no_future_leakage_and_baseline_comparison():
    data = series()
    result = evaluate(data)
    assert result["holdout_MAE_quantity"] == {"last_observed": "0.5", "training_mean": "0.0"}
    changed = copy.deepcopy(data)
    changed["periods"][-1]["quantity"] = "900"
    assert evaluate(changed)["predictions_per_day"] == result["predictions_per_day"]
    assert not result["production_enabled"] and result["confidence_interval"] is None


@pytest.mark.parametrize("kind", ["missing", "stockout", "unconfirmed", "cold_start"])
def test_suppress_invalid_forecast_data(kind):
    data = series()
    if kind == "missing":
        data["periods"][1]["date"] = "2026-10-04"
    elif kind == "stockout":
        data["periods"][0]["stockout"] = True
    elif kind == "unconfirmed":
        data["periods"][0]["coverage_confirmed"] = False
    else:
        data["minimum_training_periods"] = 3
    with pytest.raises(ValueError):
        evaluate(data)
