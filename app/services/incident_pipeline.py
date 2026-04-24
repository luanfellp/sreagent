import logging

from app.ai.base import BaseLLMProvider, sanitize_analysis_result
from app.ai.mock_provider import MockLLMProvider
from app.core.logging_utils import log_event
from app.domain.incident_models import IncidentContext
from app.domain.llm_models import (
    LLMContextAlert,
    LLMContextCorrelation,
    LLMContextEvidence,
    LLMContextHypothesis,
    LLMContextSignals,
    LLMIncidentContext,
)
from app.domain.models import AlertInput, CorrelationOutcome, EnrichedAlert
from app.integrations.interfaces import KubernetesClient, LokiClient, PrometheusClient
from app.integrations.mocks import mock_kubernetes, mock_loki, mock_prometheus
from app.services.correlation import correlate_alert
from app.services.diagnosis import diagnose_incident
from app.services.enrichment import enrich_alert
from app.services.redaction import redact_text, redact_value

logger = logging.getLogger(__name__)


def _create_llm_context(
    enriched_alert: EnrichedAlert, correlation_outcome: CorrelationOutcome
) -> LLMIncidentContext:
    return LLMIncidentContext(
        alert=LLMContextAlert(
            source=enriched_alert.alert.source,
            severity=enriched_alert.alert.severity,
            message=redact_text(enriched_alert.alert.message),
            service=enriched_alert.alert.service,
            environment=enriched_alert.alert.environment,
            labels={
                key: str(redact_value(value, key))
                for key, value in enriched_alert.alert.labels.items()
            },
        ),
        signals=LLMContextSignals.model_validate(enriched_alert.signals.model_dump()),
        correlation=LLMContextCorrelation.model_validate(
            correlation_outcome.correlation.model_dump()
        ),
        evidence=[
            LLMContextEvidence(
                id=item.id,
                source=item.source,
                kind=item.kind,
                summary=redact_text(item.summary),
                attributes=redact_value(item.attributes),
            )
            for item in enriched_alert.evidence
        ],
        deterministic_hypotheses=[
            LLMContextHypothesis(
                statement=redact_text(item.statement),
                confidence=item.confidence,
                evidence_ids=item.evidence_ids,
            )
            for item in correlation_outcome.hypotheses
        ],
    )


def analyze_alert(
    alert: AlertInput,
    llm_provider: BaseLLMProvider,
    prometheus_client: PrometheusClient = mock_prometheus,
    loki_client: LokiClient = mock_loki,
    kubernetes_client: KubernetesClient = mock_kubernetes,
) -> IncidentContext:
    enriched = enrich_alert(alert, prometheus_client, loki_client, kubernetes_client)
    correlated = correlate_alert(enriched)
    diagnosis = diagnose_incident(enriched, correlated)

    log_event(
        logger,
        logging.INFO,
        "incident.correlation.completed",
        source=alert.source,
        service=enriched.alert.service,
        environment=enriched.alert.environment,
        correlation_rule=correlated.correlation.rule,
        llm_provider=llm_provider.provider_name,
    )

    llm_context = _create_llm_context(enriched, correlated)
    allowed_evidence_ids = {item.id for item in enriched.evidence}

    try:
        llm_analysis = sanitize_analysis_result(
            llm_provider.analyze_incident(llm_context),
            allowed_evidence_ids=allowed_evidence_ids,
        )
        log_event(
            logger,
            logging.INFO,
            "incident.llm.completed",
            service=enriched.alert.service,
            environment=enriched.alert.environment,
            llm_provider=llm_provider.provider_name,
        )
    except Exception:
        log_event(
            logger,
            logging.WARNING,
            "incident.llm.fallback",
            service=enriched.alert.service,
            environment=enriched.alert.environment,
            failed_provider=llm_provider.provider_name,
            fallback_provider="mock",
        )
        fallback_provider = MockLLMProvider(
            note=f"Provider '{llm_provider.provider_name}' failed; fallback mock analysis used."
        )
        llm_analysis = sanitize_analysis_result(
            fallback_provider.analyze_incident(llm_context),
            allowed_evidence_ids=allowed_evidence_ids,
        )

    return IncidentContext(
        alert=enriched.alert,
        signals=enriched.signals,
        correlation=correlated.correlation,
        evidence=enriched.evidence,
        hypotheses=correlated.hypotheses,
        diagnosis=diagnosis,
        llm_analysis=llm_analysis,
    )
