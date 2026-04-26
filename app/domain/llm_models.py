from typing import Any

from pydantic import BaseModel, Field


class LLMContextAlert(BaseModel):
    source: str
    severity: str
    message: str
    service: str
    environment: str
    labels: dict[str, str] = Field(default_factory=dict)


class LLMContextSignals(BaseModel):
    recent_deploy: bool = False
    dominant_error: str | None = None
    restart_detected: bool = False
    crashloop_detected: bool = False
    high_error_rate: bool = False
    latency_elevated: bool = False
    relevant_logs_found: bool = False


class LLMContextCorrelation(BaseModel):
    dedup_key: str
    rule: str
    confidence: str


class LLMContextEvidence(BaseModel):
    id: str
    source: str
    kind: str
    summary: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class LLMContextHypothesis(BaseModel):
    statement: str
    confidence: str
    evidence_ids: list[str] = Field(default_factory=list)


class LLMIncidentContext(BaseModel):
    alert: LLMContextAlert
    signals: LLMContextSignals
    correlation: LLMContextCorrelation
    evidence: list[LLMContextEvidence] = Field(default_factory=list)
    deterministic_hypotheses: list[LLMContextHypothesis] = Field(default_factory=list)


class LLMRefinedHypothesis(BaseModel):
    title: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str


class LLMAnalysisResult(BaseModel):
    summary: str
    hypotheses_refined: list[LLMRefinedHypothesis] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
