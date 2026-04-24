from app.ai.base import BaseLLMProvider
from app.domain.llm_models import (
    LLMAnalysisResult,
    LLMIncidentContext,
    LLMRefinedHypothesis,
)


def _string_confidence_to_score(value: str) -> float:
    return {"low": 0.35, "medium": 0.6, "high": 0.85}[value]


class MockLLMProvider(BaseLLMProvider):
    provider_name = "mock"

    def __init__(self, note: str | None = None):
        self._note = note

    def analyze_incident(self, context: LLMIncidentContext) -> LLMAnalysisResult:
        log_evidence_present = any(
            item.source == "loki" and item.kind == "application-log-summary"
            for item in context.evidence
        )
        evidence_basis = (
            "com apoio de Prometheus e logs reais da aplicação no Loki"
            if log_evidence_present
            else "com apoio dos sinais determinísticos disponíveis"
        )
        summary = (
            f"🧠 Análise inicial: a correlação determinística aponta para a regra "
            f"'{context.correlation.rule}' no serviço {context.alert.service} "
            f"em {context.alert.environment}, {evidence_basis}."
        )
        refined_hypotheses = [
            LLMRefinedHypothesis(
                title=hypothesis.statement,
                confidence=_string_confidence_to_score(hypothesis.confidence),
                evidence_ids=hypothesis.evidence_ids,
                rationale=(
                    "🔎 Esta hipótese apenas refina a correlação determinística e não "
                    "adiciona fatos além das evidências já coletadas."
                ),
            )
            for hypothesis in context.deterministic_hypotheses
        ]

        next_steps = [
            "📊 Validar os sinais correlacionados nos dashboards e logs.",
            "🧭 Confirmar o escopo afetado antes de propor qualquer remediação.",
        ]
        if context.signals.crashloop_detected:
            next_steps.insert(
                0, "🚨 Inspecionar motivos de restart e eventos dos pods do workload afetado."
            )
        elif context.signals.recent_deploy:
            next_steps.insert(
                0, "🚀 Revisar o último deploy e a saúde do rollout."
            )

        confidence_notes = [
            "🤖 Provedor LLM mock em uso; a saída é uma camada de refinamento determinística.",
            "🛡️ A camada de IA é apenas consultiva e não substitui as evidências coletadas nem a correlação determinística.",
        ]
        if self._note:
            confidence_notes.append(self._note)

        return LLMAnalysisResult(
            summary=summary,
            hypotheses_refined=refined_hypotheses,
            next_steps=next_steps,
            confidence_notes=confidence_notes,
        )
