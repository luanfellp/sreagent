from fastapi.testclient import TestClient

from app.main import create_app


def _alert_payload(service: str = "checkout") -> dict[str, object]:
    return {
        "source": "grafana",
        "severity": "critical",
        "message": "Checkout latency is above threshold.",
        "labels": {"service": service, "environment": "prod"},
    }


def test_recent_incidents_records_alert_responses() -> None:
    with TestClient(create_app()) as client:
        alert_response = client.post("/alerts", json=_alert_payload("checkout"))
        history_response = client.get("/incidents/recent")

    assert alert_response.status_code == 200
    assert history_response.status_code == 200

    payload = history_response.json()
    assert payload["mode"] == "read-only"
    assert payload["count"] == 1
    assert payload["incidents"][0]["service"] == "checkout"
    assert payload["incidents"][0]["status"] == "analyzed"
    assert payload["incidents"][0]["result"]["alert"]["service"] == "checkout"


def test_recent_incidents_supports_status_filter() -> None:
    with TestClient(create_app()) as client:
        client.post("/alerts", json=_alert_payload("checkout"))
        response = client.get("/incidents/recent", params={"status": "resolved"})

    assert response.status_code == 200
    assert response.json()["incidents"] == []


def test_get_incident_by_id() -> None:
    with TestClient(create_app()) as client:
        client.post("/alerts", json=_alert_payload("checkout"))
        recent = client.get("/incidents/recent").json()
        incident_id = recent["incidents"][0]["id"]
        response = client.get(f"/incidents/{incident_id}")

    assert response.status_code == 200
    assert response.json()["id"] == incident_id


def test_dashboard_serves_operational_html() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert "SREAgent" in response.text
    assert "/incidents/recent" in response.text
