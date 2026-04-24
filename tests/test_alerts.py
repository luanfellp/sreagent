from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app


client = TestClient(app)


def _alert_payload() -> dict[str, object]:
    return {
        "source": "grafana",
        "severity": "critical",
        "message": "Checkout latency is above threshold.",
        "labels": {"service": "checkout", "environment": "prod"},
    }


def test_create_alert_returns_structured_response() -> None:
    response = client.post("/alerts", json=_alert_payload())

    assert response.status_code == 200

    payload = response.json()

    assert payload["mode"] == "read-only"
    assert payload["status"] == "analyzed"
    assert payload["alert"]["service"] == "checkout"
    assert payload["alert"]["environment"] == "prod"
    assert payload["signals"] == {
        "recent_deploy": False,
        "dominant_error": None,
        "restart_detected": False,
        "crashloop_detected": False,
    }
    assert payload["correlation"]["dedup_key"] == "checkout:prod:critical"
    assert payload["correlation"]["rule"] == "critical-service-alert"
    assert payload["correlation"]["confidence"] == "medium"
    assert payload["diagnosis"] == {
        "probable_component": "checkout",
        "probable_failure_type": "service-degradation",
        "probable_scope": "single-service",
        "confidence": "medium",
        "supporting_evidence_ids": [
            "prometheus-service-health",
            "loki-error-summary",
            "kubernetes-workload-status",
        ],
    }
    evidence_by_source = {item["source"]: item for item in payload["evidence"]}
    assert sorted(evidence_by_source) == ["kubernetes", "loki", "prometheus"]
    assert evidence_by_source["prometheus"]["kind"] == "service-health"
    assert (
        evidence_by_source["prometheus"]["attributes"]["metric_name"]
        == "http_request_latency_p95_ms"
    )
    assert evidence_by_source["loki"]["kind"] == "application-log-summary"
    assert evidence_by_source["kubernetes"]["kind"] == "workload-status"
    assert payload["hypotheses"][0]["confidence"] == "medium"
    assert payload["hypotheses"][0]["evidence_ids"] == [
        "prometheus-service-health",
        "loki-error-summary",
        "kubernetes-workload-status",
    ]
    assert payload["llm_analysis"]["summary"]
    assert "logs reais da aplicação no Loki" in payload["llm_analysis"]["summary"]
    assert payload["llm_analysis"]["hypotheses_refined"]
    assert payload["llm_analysis"]["confidence_notes"]
    assert any(
        "Provedor LLM mock" in note
        for note in payload["llm_analysis"]["confidence_notes"]
    )
    assert payload["notifications"][0]["channel"] == "slack"
    assert payload["notifications"][0]["message"].startswith("🛡️ [SOMENTE LEITURA]")
    assert "🧠 Resumo:" in payload["notifications"][0]["message"]
    assert "🪵 Logs da aplicação:" in payload["notifications"][0]["message"]
    assert "➡️ Próximos passos:" in payload["notifications"][0]["message"]
    assert "📈 Confiança:" in payload["notifications"][0]["message"]


def test_create_alert_detects_recent_deploy_error_and_crashloop() -> None:
    response = client.post(
        "/alerts",
        json={
            "source": "grafana",
            "severity": "critical",
            "message": "Checkout timeout spike with crashloop symptoms.",
            "labels": {
                "service": "checkout",
                "environment": "prod",
                "deploy_minutes_ago": "12",
                "restart_count": "4",
                "pod_status": "CrashLoopBackOff",
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["signals"] == {
        "recent_deploy": True,
        "dominant_error": "timeout",
        "restart_detected": True,
        "crashloop_detected": True,
    }
    assert payload["diagnosis"] == {
        "probable_component": "checkout workload",
        "probable_failure_type": "crashloop",
        "probable_scope": "single-workload",
        "confidence": "high",
        "supporting_evidence_ids": ["kubernetes-workload-status"],
    }
    assert payload["correlation"]["rule"] == "crashloop-detected"
    assert payload["correlation"]["confidence"] == "high"
    assert [item["confidence"] for item in payload["hypotheses"]] == [
        "high",
        "high",
        "high",
    ]
    assert [item["evidence_ids"] for item in payload["hypotheses"]] == [
        ["kubernetes-workload-status"],
        ["loki-error-summary"],
        ["kubernetes-workload-status"],
    ]
    assert [
        item["evidence_ids"] for item in payload["llm_analysis"]["hypotheses_refined"]
    ] == [
        ["kubernetes-workload-status"],
        ["loki-error-summary"],
        ["kubernetes-workload-status"],
    ]
    assert any(
        "Recent deploy detected 12 minutes ago" in item["summary"]
        for item in payload["evidence"]
    )
    assert any(
        "Erro dominante observado: timeout" in item["summary"]
        for item in payload["evidence"]
    )
    assert any("CrashLoopBackOff" in item["summary"] for item in payload["evidence"])


def test_create_alert_requires_api_token_when_configured() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(api_token="test-token")

    try:
        unauthorized_response = client.post("/alerts", json=_alert_payload())
        authorized_response = client.post(
            "/alerts",
            json=_alert_payload(),
            headers={"X-API-Token": "test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert unauthorized_response.status_code == 401
    assert unauthorized_response.json() == {"detail": "Invalid or missing API token."}
    assert authorized_response.status_code == 200


def test_create_alert_uses_mock_llm_when_disabled() -> None:
    response = client.post("/alerts", json=_alert_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_analysis"]["summary"].startswith(
        "🧠 Análise inicial:"
    )
    assert (
        "⚙️ LLM desabilitada por configuração." in payload["llm_analysis"]["confidence_notes"]
    )


def test_alertmanager_warning_is_normalized_to_medium() -> None:
    response = client.post(
        "/alerts/alertmanager",
        json={
            "receiver": "sreagent-webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "TelegramSendFailure",
                        "severity": "warning",
                        "service": "sreagent",
                    },
                    "annotations": {
                        "summary": "Telegram delivery failures detected",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["alert"]["severity"] == "medium"
    assert payload["alert"]["source"] == "alertmanager"
