"""Test inputs use the authenticated store's business date, not the runner's timezone."""

from datetime import datetime
from zoneinfo import ZoneInfo


def merchant_today(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200, response.text
    return datetime.now(ZoneInfo(response.json()["store"]["timezone"])).date()
