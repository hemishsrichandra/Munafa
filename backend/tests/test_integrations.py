from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from backend.integrations import (
    rupees_to_paise,
    DeviceObservation,
    device_state,
    MessageDraft,
    DisabledConnector,
)
from backend.domain import RuleError


@pytest.mark.parametrize("value,expected", [("0", 0), ("1.01", 101), ("938.20", 93820)])
def test_exact_amount(value, expected):
    assert rupees_to_paise(value) == expected


@pytest.mark.parametrize("value", [1.1, "1e2", "-1", "NaN", "1.001", " 1", "1,000", True])
def test_reject_ambiguous_amount(value):
    with pytest.raises(RuleError):
        rupees_to_paise(value)


def test_missing_and_stale_device_not_fault():
    now = datetime.now(timezone.utc)
    assert device_state(None)["status"] == "unavailable"
    for age, alert in [(0, True), (48, False), (-1, False)]:
        observation = DeviceObservation(
            schema_version=1,
            source_event_id="SYNTHETIC-1",
            device_reference="SYNTHETIC-device",
            mode="demo",
            reported_status="offline",
            reported_at=now - timedelta(hours=age),
        )
        assert device_state(observation, now)["alert"] is alert


def test_disabled_connector_never_authenticates_or_sends():
    connector = DisabledConnector()
    assert not connector.verify_webhook(b"{}", {"authorization": "invented"})
    with pytest.raises(RuleError):
        connector.execute(consent=True, approved=True, mode="live")
    with pytest.raises(ValidationError):
        MessageDraft(
            schema_version=1,
            recipient="123",
            language="en",
            purpose="supplier_recovery",
            text="draft",
            consent_id="x",
        )


def test_status_honest_and_no_secret_reflection(client, monkeypatch):
    monkeypatch.setenv("PAYTM_SECRET", "must-never-be-returned")
    response = client.get("/api/integrations/status")
    assert response.status_code == 200
    assert "must-never-be-returned" not in response.text
    assert all(
        not c["connected"] and c["last_successful_sync"] is None
        for c in response.json()["capabilities"]
    )
