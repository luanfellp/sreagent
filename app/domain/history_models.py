from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import AlertResponse


class IncidentHistoryRecord(BaseModel):
    id: str
    created_at: datetime
    status: str
    title: str
    severity: str
    service: str
    environment: str
    source: str
    dedup_key: str
    correlation_rule: str
    confidence: str
    primary_hypothesis: str
    evidence_ids: list[str] = Field(default_factory=list)
    notification_channels: list[str] = Field(default_factory=list)
    result: AlertResponse


class IncidentHistoryResponse(BaseModel):
    mode: str = "read-only"
    count: int
    incidents: list[IncidentHistoryRecord] = Field(default_factory=list)
