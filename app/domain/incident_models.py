from pydantic import BaseModel

from app.domain.llm_models import LLMAnalysisResult
from app.domain.models import (
    CorrelationDetails,
    EnrichmentSignals,
    EvidenceItem,
    Hypothesis,
    IncidentDiagnosis,
    NormalizedAlert,
)


class IncidentContext(BaseModel):
    alert: NormalizedAlert
    signals: EnrichmentSignals
    correlation: CorrelationDetails
    evidence: list[EvidenceItem]
    hypotheses: list[Hypothesis]
    diagnosis: IncidentDiagnosis
    llm_analysis: LLMAnalysisResult
