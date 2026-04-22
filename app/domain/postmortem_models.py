from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import AlertInput, IncidentDiagnosis, NormalizedAlert


TimelinePhase = Literal[
    "detected",
    "observed",
    "investigating",
    "mitigated",
    "resolved",
    "note",
]


class PostmortemTimelineEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(..., min_length=1)
    phase: TimelinePhase
    summary: str = Field(..., min_length=1)
    source: str = Field(default="manual", min_length=1)

    @field_validator("timestamp", "summary", "source")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class PostmortemDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert: AlertInput
    timeline: list[PostmortemTimelineEventInput] = Field(default_factory=list)
    incident_title: str | None = None


class PostmortemTimelineEvent(BaseModel):
    timestamp: str
    phase: TimelinePhase
    summary: str
    source: str


class PostmortemDraft(BaseModel):
    mode: Literal["read-only"]
    status: Literal["draft"]
    title: str
    alert: NormalizedAlert
    diagnosis: IncidentDiagnosis
    incident_summary: str
    impact_summary: str
    detection_summary: str
    timeline: list[PostmortemTimelineEvent] = Field(default_factory=list)
    confirmed_facts: list[str] = Field(default_factory=list)
    probable_contributing_factors: list[str] = Field(default_factory=list)
    root_cause_status: Literal["hypothesis-only"]
    unknowns: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    llm_summary: str
