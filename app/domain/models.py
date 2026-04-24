from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.llm_models import LLMAnalysisResult

Severity = Literal["critical", "high", "medium", "low", "info"]


class AlertInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., min_length=1)
    severity: Severity
    message: str = Field(..., min_length=1)
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("source", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        aliases = {
            "warning": "medium",
            "warn": "medium",
            "error": "high",
        }
        return aliases.get(normalized, normalized)


class NormalizedAlert(BaseModel):
    source: str
    severity: str
    message: str
    service: str
    environment: str
    labels: dict[str, str] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    id: str
    source: str
    kind: str
    summary: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class EnrichmentSignals(BaseModel):
    recent_deploy: bool = False
    dominant_error: str | None = None
    restart_detected: bool = False
    crashloop_detected: bool = False
    high_error_rate: bool = False
    latency_elevated: bool = False
    relevant_logs_found: bool = True


class EnrichedAlert(BaseModel):
    alert: NormalizedAlert
    evidence: list[EvidenceItem]
    signals: EnrichmentSignals


class CorrelationDetails(BaseModel):
    dedup_key: str
    rule: str
    confidence: str
    primary_hypothesis: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    secondary_signals: list[str] = Field(default_factory=list)
    information_gaps: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    kind: str = "generic"
    statement: str
    confidence: Literal["low", "medium", "high"]
    score: int = Field(default=0, ge=0)
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_signals: list[str] = Field(default_factory=list)


class CorrelationOutcome(BaseModel):
    correlation: CorrelationDetails
    hypotheses: list[Hypothesis]


class IncidentDiagnosis(BaseModel):
    probable_component: str
    probable_failure_type: str
    probable_scope: Literal["single-workload", "single-service", "unknown"]
    confidence: Literal["low", "medium", "high"]
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class NotificationPreview(BaseModel):
    channel: Literal["telegram"]
    message: str


class AlertResponse(BaseModel):
    mode: Literal["read-only"]
    status: str
    title: str
    alert: NormalizedAlert
    signals: EnrichmentSignals
    correlation: CorrelationDetails
    evidence: list[EvidenceItem]
    hypotheses: list[Hypothesis]
    diagnosis: IncidentDiagnosis
    llm_analysis: LLMAnalysisResult
    actions: list[str]
    non_executed_actions: list[str] = Field(default_factory=list)
    notifications: list[NotificationPreview]


class AlertmanagerWebhookResponse(BaseModel):
    mode: Literal["read-only"]
    status: str
    group_count: int
    firing_groups: int
    resolved_groups: int
    ignored_groups: int
    results: list[AlertResponse] = Field(default_factory=list)
