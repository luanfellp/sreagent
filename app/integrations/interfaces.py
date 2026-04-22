from typing import Protocol

from app.integrations.models import (
    KubernetesWorkloadStatus,
    LokiErrorSummary,
    PrometheusSnapshot,
    SlackMessagePreview,
)


class PrometheusClient(Protocol):
    def query_service_health(
        self, service: str, environment: str
    ) -> PrometheusSnapshot: ...


class LokiClient(Protocol):
    def query_recent_errors(
        self, service: str, environment: str
    ) -> LokiErrorSummary: ...


class KubernetesClient(Protocol):
    def describe_workload(
        self, service: str, environment: str
    ) -> KubernetesWorkloadStatus: ...


class SlackClient(Protocol):
    def build_notification_preview(
        self, title: str, summary: str
    ) -> SlackMessagePreview: ...
