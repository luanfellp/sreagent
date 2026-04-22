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
        summary = (
            f"Deterministic correlation points to rule {context.correlation.rule} "
            f"for service {context.alert.service} in {context.alert.environment}."
        )
        refined_hypotheses = [
            LLMRefinedHypothesis(
                title=hypothesis.statement,
                confidence=_string_confidence_to_score(hypothesis.confidence),
                evidence_ids=hypothesis.evidence_ids,
                rationale=(
                    "This refinement mirrors the deterministic correlation and does not add "
                    "new facts beyond the collected evidence."
                ),
            )
            for hypothesis in context.deterministic_hypotheses
        ]

        next_steps = [
            "Validate the correlated signals against dashboards and logs.",
            "Confirm the affected scope before proposing any remediation.",
        ]
        if context.signals.crashloop_detected:
            next_steps.insert(
                0, "Inspect restart reasons and pod events for the failing workload."
            )
        elif context.signals.recent_deploy:
            next_steps.insert(
                0, "Review the latest deployment timeline and rollout health."
            )

        confidence_notes = [
            "Mock LLM provider in use; output is a deterministic refinement layer.",
            "The LLM layer is advisory only and does not replace collected evidence or deterministic correlation.",
        ]
        if self._note:
            confidence_notes.append(self._note)

        return LLMAnalysisResult(
            summary=summary,
            hypotheses_refined=refined_hypotheses,
            next_steps=next_steps,
            confidence_notes=confidence_notes,
        )
