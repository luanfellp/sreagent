
import pytest
import requests

pytestmark = pytest.mark.e2e

ALERTMANAGER_SAMPLE = {
    "receiver": "sreagent-webhook",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "High5xxRate", "severity": "critical", "service": "metrics-generator"},
            "annotations": {"summary": "5xx rate > 8%", "description": "Simulated test alert"},
            "startsAt": "2026-01-01T00:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
        }
    ],
}


def test_alertmanager_webhook_to_agent():
    """Integration test: POST Alertmanager payload to SREAgent and expect a 200 OK and valid JSON."""
    url = "http://localhost:8002/alerts/alertmanager"
    r = requests.post(url, json=ALERTMANAGER_SAMPLE, timeout=10)
    assert r.status_code == 200, f"unexpected status: {r.status_code} {r.text}"
    data = r.json()
    # basic schema checks
    assert "status" in data
    assert "results" in data
    assert data["results"][0]["alert"]["severity"] in (
        "critical",
        "high",
        "medium",
        "low",
        "info",
    )
