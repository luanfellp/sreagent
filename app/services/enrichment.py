from app.domain.models import (
    AlertInput,
    EnrichedAlert,
    EnrichmentSignals,
    EvidenceItem,
    NormalizedAlert,
)
from app.integrations.interfaces import KubernetesClient, LokiClient, PrometheusClient
from app.integrations.mocks import mock_kubernetes, mock_loki, mock_prometheus
from app.integrations.models import (
    KubernetesWorkloadStatus,
    LokiErrorSummary,
    PrometheusSnapshot,
)


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_int(value: str | None) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0


def _detect_recent_deploy(
    labels: dict[str, str], workload_status: KubernetesWorkloadStatus
) -> bool:
    if _is_truthy(labels.get("recent_deploy")):
        return True
    deploy_minutes_ago = _parse_int(labels.get("deploy_minutes_ago"))
    if 0 < deploy_minutes_ago <= 30:
        return True
    return workload_status.recent_deploy and (
        workload_status.deploy_minutes_ago is None
        or 0 < workload_status.deploy_minutes_ago <= 30
    )


def _detect_dominant_error(
    alert: AlertInput, error_summary: LokiErrorSummary
) -> str | None:
    if alert.labels.get("dominant_error"):
        return alert.labels["dominant_error"].strip().lower()
    if error_summary.dominant_error:
        return error_summary.dominant_error.strip().lower()

    message = alert.message.lower()
    if "timeout" in message:
        return "timeout"
    if "crashloop" in message:
        return "crashloopbackoff"
    if "oom" in message:
        return "oomkilled"
    if "5xx" in message or "500" in message:
        return "http-5xx"
    return None


def _detect_restart_signals(
    labels: dict[str, str], workload_status: KubernetesWorkloadStatus
) -> tuple[bool, bool]:
    restart_count = max(
        _parse_int(labels.get("restart_count")), workload_status.restart_count
    )
    pod_status = (
        ((labels.get("pod_status") or workload_status.pod_status) or "").strip().lower()
    )
    crashloop_detected = (
        "crashloop" in pod_status
        or _is_truthy(labels.get("crashloop"))
        or workload_status.crashloop_detected
    )
    restart_detected = (
        crashloop_detected or restart_count > 0 or "restart" in pod_status
    )
    return restart_detected, crashloop_detected


def _build_prometheus_evidence(snapshot: PrometheusSnapshot) -> EvidenceItem:
    return EvidenceItem(
        id="prometheus-service-health",
        source="prometheus",
        kind="service-health",
        summary=snapshot.summary,
        attributes={
            "metric_name": snapshot.metric_name,
            "status": snapshot.status,
            "latency_p95_ms": snapshot.latency_p95_ms,
            "error_rate_per_minute": snapshot.error_rate_per_minute,
        },
        raw=snapshot.model_dump(exclude_none=True),
    )


def _build_loki_evidence(
    error_summary: LokiErrorSummary, dominant_error: str | None
) -> EvidenceItem:
    summary = error_summary.summary
    if error_summary.examples and "Exemplo recente:" not in summary:
        summary = f"{summary} Trecho recente: {error_summary.examples[0]}"
    if dominant_error:
        summary = f"{summary} Erro dominante observado: {dominant_error}."

    attributes = error_summary.model_dump(exclude_none=True)
    attributes["dominant_error"] = dominant_error
    return EvidenceItem(
        id="loki-error-summary",
        source="loki",
        kind="application-log-summary",
        summary=summary,
        attributes=attributes,
        raw=error_summary.model_dump(exclude_none=True),
    )


def _build_kubernetes_evidence(
    workload_status: KubernetesWorkloadStatus,
    recent_deploy: bool,
    restart_detected: bool,
    crashloop_detected: bool,
    deploy_minutes_ago: int,
    restart_count: int,
) -> EvidenceItem:
    summary = workload_status.summary
    if recent_deploy:
        if deploy_minutes_ago > 0:
            summary = (
                f"{summary} Recent deploy detected {deploy_minutes_ago} minutes ago."
            )
        else:
            summary = f"{summary} Recent deploy detected."
    if crashloop_detected:
        summary = f"{summary} Pod status indicates CrashLoopBackOff."
    elif restart_detected:
        summary = f"{summary} Restart count observed: {restart_count}."

    attributes = workload_status.model_dump(exclude_none=True)
    attributes.update(
        {
            "recent_deploy": recent_deploy,
            "deploy_minutes_ago": deploy_minutes_ago
            or workload_status.deploy_minutes_ago,
            "restart_detected": restart_detected,
            "restart_count": restart_count,
            "crashloop_detected": crashloop_detected,
        }
    )
    return EvidenceItem(
        id="kubernetes-workload-status",
        source="kubernetes",
        kind="workload-status",
        summary=summary,
        attributes=attributes,
        raw=workload_status.model_dump(exclude_none=True),
    )


def enrich_alert(
    alert: AlertInput,
    prometheus_client: PrometheusClient = mock_prometheus,
    loki_client: LokiClient = mock_loki,
    kubernetes_client: KubernetesClient = mock_kubernetes,
) -> EnrichedAlert:
    service = alert.labels.get("service") or alert.source
    environment = alert.labels.get("environment", "unknown")
    normalized_alert = NormalizedAlert(
        source=alert.source,
        severity=alert.severity,
        message=alert.message,
        service=service,
        environment=environment,
        labels=alert.labels,
    )
    prometheus_snapshot = prometheus_client.query_service_health(service, environment)
    loki_error_summary = loki_client.query_recent_errors(service, environment)
    kubernetes_workload_status = kubernetes_client.describe_workload(
        service, environment
    )

    recent_deploy = _detect_recent_deploy(alert.labels, kubernetes_workload_status)
    dominant_error = _detect_dominant_error(alert, loki_error_summary)
    restart_detected, crashloop_detected = _detect_restart_signals(
        alert.labels, kubernetes_workload_status
    )
    high_error_rate = prometheus_snapshot.status in {"degraded", "critical"}
    latency_elevated = (prometheus_snapshot.latency_p95_ms or 0) >= 700
    relevant_logs_found = (loki_error_summary.error_count or 0) > 0
    deploy_minutes_ago = max(
        _parse_int(alert.labels.get("deploy_minutes_ago")),
        kubernetes_workload_status.deploy_minutes_ago or 0,
    )
    restart_count = max(
        _parse_int(alert.labels.get("restart_count")),
        kubernetes_workload_status.restart_count,
    )

    evidence = [
        _build_prometheus_evidence(prometheus_snapshot),
        _build_loki_evidence(loki_error_summary, dominant_error),
        _build_kubernetes_evidence(
            kubernetes_workload_status,
            recent_deploy,
            restart_detected,
            crashloop_detected,
            deploy_minutes_ago,
            restart_count,
        ),
    ]
    signals = EnrichmentSignals(
        recent_deploy=recent_deploy,
        dominant_error=dominant_error,
        restart_detected=restart_detected,
        crashloop_detected=crashloop_detected,
        high_error_rate=high_error_rate,
        latency_elevated=latency_elevated,
        relevant_logs_found=relevant_logs_found,
    )
    return EnrichedAlert(alert=normalized_alert, evidence=evidence, signals=signals)
