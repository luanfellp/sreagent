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
                "logs da aplicação contêm erros repetidos e úteis para a análise inicial."
            ),
            error_count=37,
            examples=[
                "error 504 1342ms - timeout while calling downstream dependency"
            ],
        )


class MockKubernetesClient:
    def describe_workload(
        self, service: str, environment: str
    ) -> KubernetesWorkloadStatus:
        return KubernetesWorkloadStatus(
            service=service,
            environment=environment,
            summary=(
                f"Nenhum provider de Kubernetes configurado para {service} em {environment}; "
                "apenas metadados do alerta estão disponíveis para estado do workload."
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
            channel="slack", message=f"🛡️ [SOMENTE LEITURA] {title}\n\n{summary}"
        )


mock_prometheus = MockPrometheusClient()
mock_loki = MockLokiClient()
mock_kubernetes = MockKubernetesClient()
mock_slack = MockSlackClient()
