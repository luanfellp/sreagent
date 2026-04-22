from app.domain.models import CorrelationOutcome, EnrichedAlert, IncidentDiagnosis


def _find_evidence_ids(alert: EnrichedAlert, source: str) -> list[str]:
    return [item.id for item in alert.evidence if item.source == source]


def diagnose_incident(
    alert: EnrichedAlert, correlation: CorrelationOutcome
) -> IncidentDiagnosis:
    probable_component = alert.alert.service
    probable_failure_type = "service-degradation"
    probable_scope = "single-service"
    supporting_evidence_ids = [item.id for item in alert.evidence]

    if alert.signals.crashloop_detected:
        probable_component = f"{alert.alert.service} workload"
        probable_failure_type = "crashloop"
        probable_scope = "single-workload"
        supporting_evidence_ids = _find_evidence_ids(alert, "kubernetes")
    elif alert.signals.restart_detected:
        probable_component = f"{alert.alert.service} workload"
        probable_failure_type = "restart-instability"
        probable_scope = "single-workload"
        supporting_evidence_ids = _find_evidence_ids(alert, "kubernetes")
    elif alert.signals.dominant_error:
        probable_failure_type = alert.signals.dominant_error
        supporting_evidence_ids = _find_evidence_ids(alert, "loki")
    elif alert.signals.recent_deploy:
        probable_failure_type = "recent-deploy-regression"
        supporting_evidence_ids = _find_evidence_ids(alert, "kubernetes")

    return IncidentDiagnosis(
        probable_component=probable_component,
        probable_failure_type=probable_failure_type,
        probable_scope=probable_scope,
        confidence=correlation.correlation.confidence,
        supporting_evidence_ids=supporting_evidence_ids,
    )
