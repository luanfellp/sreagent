from app.ai.base import sanitize_analysis_result
from app.ai.mock_provider import MockLLMProvider
from app.domain.llm_models import (
    LLMContextAlert,
    LLMContextCorrelation,
    LLMContextEvidence,
    LLMContextHypothesis,
    LLMContextSignals,
    LLMIncidentContext,
)


def _incident_context() -> LLMIncidentContext:
    return LLMIncidentContext(
        alert=LLMContextAlert(
            source="grafana",
            severity="critical",
            message="Checkout latency is above threshold.",
            service="checkout",
            environment="prod",
            labels={"service": "checkout", "environment": "prod"},
        ),
        signals=LLMContextSignals(),
        correlation=LLMContextCorrelation(
            dedup_key="checkout:prod:critical",
            rule="critical-service-alert",
            confidence="medium",
        ),
        evidence=[
            LLMContextEvidence(
                id="prometheus-service-health",
                source="prometheus",
                kind="service-health",
                summary="Latency is elevated compared to baseline.",
                attributes={"latency_p95_ms": 850},
            ),
            LLMContextEvidence(
                id="loki-error-summary",
                source="loki",
                kind="application-log-summary",
                summary="Logs da aplicação mostram timeouts próximos ao alerta.",
                attributes={"error_count": 12},
            ),
        ],
        deterministic_hypotheses=[
            LLMContextHypothesis(
                statement="The incident is likely centered on service checkout in environment prod.",
                confidence="medium",
                evidence_ids=["prometheus-service-health"],
            )
        ],
    )


def test_mock_provider_returns_valid_analysis_structure() -> None:
    provider = MockLLMProvider()

    result = provider.analyze_incident(_incident_context())

    assert result.summary
    assert result.summary.startswith("🧠 Análise inicial:")
    assert "logs reais da aplicação no Loki" in result.summary
    assert result.hypotheses_refined
    assert 0.0 <= result.hypotheses_refined[0].confidence <= 1.0
    assert result.hypotheses_refined[0].evidence_ids == ["prometheus-service-health"]
    assert result.next_steps
    assert result.confidence_notes


def test_sanitize_analysis_result_removes_unknown_evidence_ids() -> None:
    provider = MockLLMProvider()
    result = provider.analyze_incident(_incident_context())
    result.hypotheses_refined[0].evidence_ids = ["unknown-evidence-id"]

    sanitized = sanitize_analysis_result(result, {"prometheus-service-health"})

    assert sanitized.hypotheses_refined == []
    assert any("discarded" in note for note in sanitized.confidence_notes)
