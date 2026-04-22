from abc import ABC, abstractmethod

from app.domain.llm_models import (
    LLMAnalysisResult,
    LLMIncidentContext,
    LLMRefinedHypothesis,
)


class BaseLLMProvider(ABC):
    provider_name: str

    @abstractmethod
    def analyze_incident(self, context: LLMIncidentContext) -> LLMAnalysisResult:
        raise NotImplementedError


def sanitize_analysis_result(
    result: LLMAnalysisResult, allowed_evidence_ids: set[str]
) -> LLMAnalysisResult:
    sanitized_hypotheses: list[LLMRefinedHypothesis] = []
    dropped_hypotheses = 0

    for hypothesis in result.hypotheses_refined:
        evidence_ids = [
            evidence_id
            for evidence_id in hypothesis.evidence_ids
            if evidence_id in allowed_evidence_ids
        ]
        if hypothesis.evidence_ids and not evidence_ids:
            dropped_hypotheses += 1
            continue

        sanitized_hypotheses.append(
            hypothesis.model_copy(update={"evidence_ids": evidence_ids})
        )

    confidence_notes = list(result.confidence_notes)
    if dropped_hypotheses:
        confidence_notes.append(
            "One or more LLM hypotheses were discarded because they referenced unknown evidence ids."
        )

    return result.model_copy(
        update={
            "hypotheses_refined": sanitized_hypotheses,
            "confidence_notes": confidence_notes,
        }
    )
