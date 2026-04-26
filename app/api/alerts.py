from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai.base import BaseLLMProvider
from app.core.settings import Settings, get_settings
from app.dependencies import (
    get_incident_store,
    get_kubernetes_client,
    get_llm_provider,
    get_loki_client,
    get_notification_preview_builder,
    get_notification_service,
    get_prometheus_client,
    require_api_token,
)
from app.domain.incident_models import IncidentContext
from app.domain.llm_models import LLMAnalysisResult
from app.domain.models import (
    AlertInput,
    AlertmanagerWebhookResponse,
    AlertResponse,
    CorrelationDetails,
    EnrichmentSignals,
    IncidentDiagnosis,
    NormalizedAlert,
)
from app.integrations.interfaces import (
    KubernetesClient,
    LokiClient,
    NotificationPreviewBuilder,
    PrometheusClient,
)
from app.services.alertmanager import AlertmanagerGroupInput, build_grouped_alert_inputs
from app.services.incident_pipeline import analyze_alert
from app.services.incident_store import IncidentStore
from app.services.notification_service import NotificationService
from app.services.summarization import summarize_alert

READ_ONLY_NON_EXECUTED_ACTIONS = [
    "Nenhuma remediação automatizada foi executada pelo SREAgent; o sistema permanece somente leitura.",
]


def _analyze_alert(
    alert: AlertInput,
    llm_provider: BaseLLMProvider,
    prometheus_client: PrometheusClient,
    loki_client: LokiClient,
    kubernetes_client: KubernetesClient,
) -> IncidentContext:
    return analyze_alert(
        alert,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
    )


def _summarize_alert(
    incident: IncidentContext,
    notification_preview_builder: NotificationPreviewBuilder,
) -> AlertResponse:
    return summarize_alert(
        incident,
        notification_preview_builder,
        non_executed_actions=READ_ONLY_NON_EXECUTED_ACTIONS,
    )


def _build_resolved_response(
    group: AlertmanagerGroupInput,
    emit_resolved: bool,
) -> AlertResponse:
    service = group.alert.labels.get("service") or group.alert.source
    environment = group.alert.labels.get("environment", "unknown")
    status = "resolved" if emit_resolved else "ignored"
    title = (
        f"✅ Alerta resolvido em {service}"
        if emit_resolved
        else f"ℹ️ Alerta resolvido ignorado em {service}"
    )
    summary = (
        f"Alertmanager reportou a resolução de {group.alert_count} alerta(s) para "
        f"{service} em {environment}; nenhuma nova análise de incidente foi executada."
        if emit_resolved
        else f"Alertmanager reportou a resolução de {group.alert_count} alerta(s) para "
        f"{service} em {environment}; o grupo foi ignorado por configuração."
    )
    information_gap = (
        "O grupo chegou com status resolved; o SREAgent não cria incidente ativo para alertas encerrados."
    )
    actions = [
        "Validar se a recuperação permaneceu estável antes de encerrar a investigação."
    ]

    return AlertResponse(
        mode="read-only",
        status=status,
        title=title,
        alert=NormalizedAlert(
            source=group.alert.source,
            severity=group.alert.severity,
            message=group.alert.message,
            service=service,
            environment=environment,
            labels=group.alert.labels,
        ),
        signals=EnrichmentSignals(relevant_logs_found=False),
        correlation=CorrelationDetails(
            dedup_key=f"{service}:{environment}:{group.alert.severity}",
            rule="alertmanager-resolved",
            confidence="low",
            primary_hypothesis="O alerta já foi resolvido e não representa incidente ativo.",
            supporting_evidence_ids=[],
            secondary_signals=[],
            information_gaps=[information_gap],
        ),
        evidence=[],
        hypotheses=[],
        diagnosis=IncidentDiagnosis(
            probable_component=service,
            probable_failure_type="resolved",
            probable_scope="single-service",
            confidence="low",
            supporting_evidence_ids=[],
        ),
        llm_analysis=LLMAnalysisResult(
            summary=summary,
            hypotheses_refined=[],
            next_steps=actions,
            confidence_notes=[
                "A IA não foi acionada para grupos resolved.",
            ],
        ),
        actions=actions,
        non_executed_actions=READ_ONLY_NON_EXECUTED_ACTIONS,
        notifications=[],
    )


def _build_webhook_response(results: list[AlertResponse]) -> AlertmanagerWebhookResponse:
    firing_groups = sum(
        1 for result in results if result.status in {"analyzed", "observed"}
    )
    resolved_groups = sum(1 for result in results if result.status == "resolved")
    ignored_groups = sum(1 for result in results if result.status == "ignored")

    if firing_groups and (resolved_groups or ignored_groups):
        status = "mixed"
    elif firing_groups:
        status = "processed"
    elif resolved_groups:
        status = "resolved"
    else:
        status = "ignored"

    return AlertmanagerWebhookResponse(
        mode="read-only",
        status=status,
        group_count=len(results),
        firing_groups=firing_groups,
        resolved_groups=resolved_groups,
        ignored_groups=ignored_groups,
        results=results,
    )


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post(
    "", response_model=AlertResponse, dependencies=[Depends(require_api_token)]
)
def create_alert(
    background_tasks: BackgroundTasks,
    alert: AlertInput,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    notification_preview_builder: Annotated[
        NotificationPreviewBuilder, Depends(get_notification_preview_builder)
    ],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
    notification_service: Annotated[
        NotificationService, Depends(get_notification_service)
    ],
    incident_store: Annotated[IncidentStore, Depends(get_incident_store)],
) -> AlertResponse:
    incident = _analyze_alert(
        alert, llm_provider, prometheus_client, loki_client, kubernetes_client
    )
    result = _summarize_alert(incident, notification_preview_builder)
    notification_service.schedule_alert_delivery(
        background_tasks,
        source=alert.source,
        labels=alert.labels,
        result=result,
    )
    incident_store.add(result)

    return result


@router.post(
    "/alertmanager",
    response_model=AlertmanagerWebhookResponse,
    dependencies=[Depends(require_api_token)],
)
def create_alert_from_alertmanager(
    background_tasks: BackgroundTasks,
    payload: dict,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    notification_preview_builder: Annotated[
        NotificationPreviewBuilder, Depends(get_notification_preview_builder)
    ],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
    notification_service: Annotated[
        NotificationService, Depends(get_notification_service)
    ],
    incident_store: Annotated[IncidentStore, Depends(get_incident_store)],
) -> AlertmanagerWebhookResponse:
    """
    Accept Alertmanager webhook payloads and process grouped alerts by
    service/environment/alertname/severity/status.
    """
    results: list[AlertResponse] = []
    for group in build_grouped_alert_inputs(payload):
        if group.status == "resolved":
            result = _build_resolved_response(
                group,
                emit_resolved=settings.alertmanager_emit_resolved,
            )
            results.append(result)
            incident_store.add(result)
            continue

        incident = _analyze_alert(
            group.alert,
            llm_provider,
            prometheus_client,
            loki_client,
            kubernetes_client,
        )
        result = _summarize_alert(incident, notification_preview_builder)
        results.append(result)
        incident_store.add(result)
        notification_service.schedule_alert_delivery(
            background_tasks,
            source=group.alert.source,
            labels=group.alert.labels,
            result=result,
        )

    return _build_webhook_response(results)
