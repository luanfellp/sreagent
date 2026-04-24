from app.domain.models import CorrelationOutcome, EnrichedAlert, IncidentDiagnosis


def _find_evidence_ids(alert: EnrichedAlert, source: str) -> list[str]:
    return [item.id for item in alert.evidence if item.source == source]


def diagnose_incident(
    alert: EnrichedAlert, correlation: CorrelationOutcome
) -> IncidentDiagnosis:
    primary_kind = correlation.hypotheses[0].kind if correlation.hypotheses else "service-degradation"
    probable_component = alert.alert.service
    probable_failure_type = "service-degradation"
    probable_scope = "single-service"
    supporting_evidence_ids = correlation.correlation.supporting_evidence_ids or [
        item.id for item in alert.evidence
    ]

    if primary_kind == "crashloop-detected":
        probable_component = f"{alert.alert.service} workload"
        probable_failure_type = "crashloop"
        probable_scope = "single-workload"
        supporting_evidence_ids = _find_evidence_ids(alert, "kubernetes")
    elif primary_kind == "restart-detected":
        probable_component = f"{alert.alert.service} workload"
        probable_failure_type = "restart-instability"
        probable_scope = "single-workload"
        supporting_evidence_ids = _find_evidence_ids(alert, "kubernetes")
    elif primary_kind == "recent-deploy-regression":
        probable_failure_type = "recent-deploy-regression"
        supporting_evidence_ids = correlation.correlation.supporting_evidence_ids
    elif primary_kind == "timeout-pattern":
        probable_failure_type = "timeout"
        supporting_evidence_ids = _find_evidence_ids(alert, "loki")
    elif primary_kind == "http-5xx-spike":
        probable_failure_type = "http-5xx"
        supporting_evidence_ids = correlation.correlation.supporting_evidence_ids
    elif primary_kind == "dominant-error-detected" and alert.signals.dominant_error:
        probable_failure_type = alert.signals.dominant_error
        supporting_evidence_ids = _find_evidence_ids(alert, "loki")

    return IncidentDiagnosis(
        probable_component=probable_component,
        probable_failure_type=probable_failure_type,
        probable_scope=probable_scope,
        confidence=correlation.correlation.confidence,
        supporting_evidence_ids=supporting_evidence_ids,
    )
