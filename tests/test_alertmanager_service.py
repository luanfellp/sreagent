from app.services.alertmanager import build_grouped_alert_inputs


def test_build_grouped_alert_inputs_groups_by_service_environment_severity_and_status() -> None:
    groups = build_grouped_alert_inputs(
        {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "High5xxRate",
                        "severity": "critical",
                        "service": "checkout",
                        "environment": "prod",
                        "instance": "pod-a",
                    },
                    "annotations": {"summary": "Erro alto checkout"},
                },
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "High5xxRate",
                        "severity": "critical",
                        "service": "checkout",
                        "environment": "prod",
                        "instance": "pod-b",
                    },
                    "annotations": {"summary": "Erro alto checkout"},
                },
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "HighLatency",
                        "severity": "high",
                        "service": "payments",
                        "environment": "prod",
                    },
                    "annotations": {"summary": "Latência normalizada"},
                },
            ],
        }
    )

    assert len(groups) == 2
    assert groups[0].alert.labels["service"] == "checkout"
    assert groups[0].alert.labels["alert_count"] == "2"
    assert groups[0].status == "firing"
    assert groups[1].alert.labels["service"] == "payments"
    assert groups[1].status == "resolved"
