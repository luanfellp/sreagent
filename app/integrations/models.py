from typing import Literal

from pydantic import BaseModel, Field


class PrometheusSnapshot(BaseModel):
    service: str
    environment: str
    metric_name: str
    status: Literal["ok", "degraded", "critical"]
    summary: str
    latency_p95_ms: int | None = None
    error_rate_per_minute: int | None = None


class LokiErrorSummary(BaseModel):
    service: str
    environment: str
    summary: str
    dominant_error: str | None = None
    error_count: int | None = None
    examples: list[str] = Field(default_factory=list)


class KubernetesWorkloadStatus(BaseModel):
    service: str
    environment: str
    summary: str
    recent_deploy: bool = False
    deploy_minutes_ago: int | None = None
    rollout_in_progress: bool = False
    restart_count: int = 0
    crashloop_detected: bool = False
    pod_status: str | None = None


class NotificationMessagePreview(BaseModel):
    channel: Literal["telegram"]
    message: str
