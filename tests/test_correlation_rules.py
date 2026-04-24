from app.domain.models import AlertInput
from app.services.correlation import correlate_alert
from app.services.enrichment import enrich_alert


def test_recent_deploy_generates_kubernetes_backed_hypothesis() -> None:
    enriched = enrich_alert(
        AlertInput(
            source="grafana",
            severity="high",
            message="Checkout latency increased after deploy.",
            labels={
                "service": "checkout",
                "environment": "prod",
                "deploy_minutes_ago": "10",
            },
        )
    )

    correlation = correlate_alert(enriched)

    assert enriched.signals.recent_deploy is True
    assert correlation.correlation.rule == "recent-deploy-regression"
    assert correlation.correlation.primary_hypothesis.startswith(
        "Um deploy recente"
    )
    assert correlation.hypotheses[0].confidence == "medium"
    assert correlation.hypotheses[0].evidence_ids == [
        "kubernetes-workload-status",
        "prometheus-service-health",
    ]
    kubernetes_evidence = next(
        item for item in enriched.evidence if item.id == "kubernetes-workload-status"
    )
    assert "Recent deploy detected 10 minutes ago" in kubernetes_evidence.summary


def test_dominant_error_generates_loki_backed_hypothesis() -> None:
    enriched = enrich_alert(
        AlertInput(
            source="grafana",
            severity="critical",
            message="Requests are timing out.",
            labels={
                "service": "checkout",
                "environment": "prod",
                "dominant_error": "timeout",
            },
        )
    )

    correlation = correlate_alert(enriched)

    assert enriched.signals.dominant_error == "timeout"
    assert correlation.correlation.rule == "timeout-pattern"
    hypothesis = correlation.hypotheses[0]
    assert hypothesis.confidence == "high"
    assert hypothesis.evidence_ids == [
        "loki-error-summary",
        "prometheus-service-health",
    ]
    loki_evidence = next(
        item for item in enriched.evidence if item.id == "loki-error-summary"
    )
    assert "Erro dominante observado: timeout" in loki_evidence.summary


def test_crashloop_generates_high_confidence_hypothesis() -> None:
    enriched = enrich_alert(
        AlertInput(
            source="grafana",
            severity="critical",
            message="Pods are restarting and failing health checks.",
            labels={
                "service": "checkout",
                "environment": "prod",
                "restart_count": "5",
                "pod_status": "CrashLoopBackOff",
            },
        )
    )

    correlation = correlate_alert(enriched)

    assert enriched.signals.restart_detected is True
    assert enriched.signals.crashloop_detected is True
    assert correlation.correlation.rule == "crashloop-detected"
    assert correlation.correlation.supporting_evidence_ids == [
        "kubernetes-workload-status"
    ]
    hypothesis = correlation.hypotheses[0]
    assert hypothesis.confidence == "high"
    assert hypothesis.evidence_ids == ["kubernetes-workload-status"]
    kubernetes_evidence = next(
        item for item in enriched.evidence if item.id == "kubernetes-workload-status"
    )
    assert "CrashLoopBackOff" in kubernetes_evidence.summary
