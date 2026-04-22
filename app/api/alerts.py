from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.base import BaseLLMProvider
from app.dependencies import (
    get_kubernetes_client,
    get_llm_provider,
    get_loki_client,
    get_prometheus_client,
    get_slack_client,
    require_api_token,
)
from app.domain.models import AlertInput, AlertResponse
from app.integrations.interfaces import (
    KubernetesClient,
    LokiClient,
    PrometheusClient,
    SlackClient,
)
from app.services.incident_pipeline import analyze_alert
from app.services.summarization import summarize_alert


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post(
    "", response_model=AlertResponse, dependencies=[Depends(require_api_token)]
)
def create_alert(
    alert: AlertInput,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    slack_client: Annotated[SlackClient, Depends(get_slack_client)],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
) -> AlertResponse:
    incident = analyze_alert(
        alert,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
    )
    return summarize_alert(incident, slack_client)
