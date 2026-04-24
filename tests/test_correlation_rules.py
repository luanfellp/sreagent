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
    assert correlation.correlation.rule == "recent-deploy-detected"
    assert correlation.hypotheses[0].confidence == "medium"
    assert correlation.hypotheses[0].evidence_ids == ["kubernetes-workload-status"]
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
    hypothesis = next(
        item
        for item in correlation.hypotheses
        if "dominant error pattern" in item.statement.lower()
    )
    assert hypothesis.confidence == "high"
    assert hypothesis.evidence_ids == ["loki-error-summary"]
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
    hypothesis = next(
        item
        for item in correlation.hypotheses
        if "crash looping" in item.statement.lower()
    )
    assert hypothesis.confidence == "high"
    assert hypothesis.evidence_ids == ["kubernetes-workload-status"]
    kubernetes_evidence = next(
        item for item in enriched.evidence if item.id == "kubernetes-workload-status"
    )
    assert "CrashLoopBackOff" in kubernetes_evidence.summary
