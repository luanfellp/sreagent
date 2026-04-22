from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.ai.base import BaseLLMProvider
from app.ai.factory import get_llm_provider_from_settings
from app.core.settings import Settings, get_settings
from app.integrations.interfaces import (
    KubernetesClient,
    LokiClient,
    PrometheusClient,
    SlackClient,
)
from app.integrations.mocks import (
    mock_kubernetes,
    mock_loki,
    mock_prometheus,
    mock_slack,
)


def get_prometheus_client() -> PrometheusClient:
    return mock_prometheus


def get_loki_client() -> LokiClient:
    return mock_loki


def get_kubernetes_client() -> KubernetesClient:
    return mock_kubernetes


def get_slack_client() -> SlackClient:
    return mock_slack


def get_llm_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BaseLLMProvider:
    return get_llm_provider_from_settings(settings)


def require_api_token(
    settings: Annotated[Settings, Depends(get_settings)],
    api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    if settings.api_token is None:
        return

    if api_token is None or not compare_digest(api_token, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token.",
        )
