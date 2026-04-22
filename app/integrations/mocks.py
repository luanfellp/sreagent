from app.integrations.models import (
    KubernetesWorkloadStatus,
    LokiErrorSummary,
    PrometheusSnapshot,
    SlackMessagePreview,
)


class MockPrometheusClient:
    def query_service_health(
        self, service: str, environment: str
    ) -> PrometheusSnapshot:
        return PrometheusSnapshot(
            service=service,
            environment=environment,
            metric_name="http_request_latency_p95_ms",
            status="degraded",
            summary=(
                f"Mock Prometheus evidence for {service} in {environment}: "
                "latency is elevated compared to the baseline."
            ),
            latency_p95_ms=850,
            error_rate_per_minute=12,
        )


class MockLokiClient:
    def query_recent_errors(self, service: str, environment: str) -> LokiErrorSummary:
        return LokiErrorSummary(
            service=service,
            environment=environment,
            summary=(
                f"Mock Loki evidence for {service} in {environment}: "
                "recent logs contain repeated error entries around the alert window."
            ),
            error_count=37,
            examples=["timeout while calling downstream dependency"],
        )


class MockKubernetesClient:
    def describe_workload(
        self, service: str, environment: str
    ) -> KubernetesWorkloadStatus:
        return KubernetesWorkloadStatus(
            service=service,
            environment=environment,
            summary=(
                f"Mock Kubernetes evidence for {service} in {environment}: "
                "deployment is running and no rollout is currently in progress."
            ),
            rollout_in_progress=False,
            restart_count=0,
            crashloop_detected=False,
        )


class MockSlackClient:
    def build_notification_preview(
        self, title: str, summary: str
    ) -> SlackMessagePreview:
        return SlackMessagePreview(
            channel="slack", message=f"[READ-ONLY] {title} | {summary}"
        )


mock_prometheus = MockPrometheusClient()
mock_loki = MockLokiClient()
mock_kubernetes = MockKubernetesClient()
mock_slack = MockSlackClient()
