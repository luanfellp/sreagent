from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_postmortem_draft_returns_structured_response() -> None:
    response = client.post(
        "/postmortems/draft",
        json={
            "alert": {
                "source": "grafana",
                "severity": "critical",
                "message": "Checkout latency is above threshold.",
                "labels": {"service": "checkout", "environment": "prod"},
            },
            "timeline": [
                {
                    "timestamp": "2026-04-22T10:15:00Z",
                    "phase": "detected",
                    "summary": "Pager notified the on-call engineer.",
                    "source": "pagerduty",
                }
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["mode"] == "read-only"
    assert payload["status"] == "draft"
    assert payload["alert"]["service"] == "checkout"
    assert payload["diagnosis"]["probable_component"] == "checkout"
    assert payload["incident_summary"].startswith("🧠 Análise inicial:")
    assert payload["timeline"][0]["phase"] == "detected"
    assert payload["root_cause_status"] == "hypothesis-only"
    assert "prometheus-service-health" in payload["evidence_references"]
    assert payload["action_items"]


def test_postmortem_draft_redacts_sensitive_timeline_data() -> None:
    response = client.post(
        "/postmortems/draft",
        json={
            "alert": {
                "source": "grafana",
                "severity": "high",
                "message": "Alert references engineer user@example.com from 10.0.0.7",
                "labels": {"service": "checkout", "environment": "prod"},
            },
            "timeline": [
                {
                    "timestamp": "2026-04-22T10:15:00Z",
                    "phase": "note",
                    "summary": "Contact user@example.com and inspect 10.0.0.7",
                    "source": "manual",
                }
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert "[REDACTED_EMAIL]" in payload["timeline"][0]["summary"]
    assert "[REDACTED_IP]" in payload["timeline"][0]["summary"]
