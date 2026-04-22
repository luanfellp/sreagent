from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.base import BaseLLMProvider
from app.dependencies import (
    get_kubernetes_client,
    get_llm_provider,
    get_loki_client,
    get_prometheus_client,
    require_api_token,
)
from app.domain.postmortem_models import PostmortemDraft, PostmortemDraftRequest
from app.integrations.interfaces import KubernetesClient, LokiClient, PrometheusClient
from app.services.incident_pipeline import analyze_alert
from app.services.postmortem import build_postmortem_draft


router = APIRouter(prefix="/postmortems", tags=["postmortems"])


@router.post(
    "/draft",
    response_model=PostmortemDraft,
    dependencies=[Depends(require_api_token)],
)
def create_postmortem_draft(
    request: PostmortemDraftRequest,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
) -> PostmortemDraft:
    incident = analyze_alert(
        request.alert,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
    )
    return build_postmortem_draft(incident, request)
