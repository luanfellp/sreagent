import os
from secrets import compare_digest
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status

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

# Import real HTTP clients if available
try:
    from app.integrations.prometheus_client import PrometheusHTTPClient
    from app.integrations.loki_client import LokiHTTPClient
    _integration_import_error: ImportError | None = None
except ImportError as exc:
    PrometheusHTTPClient = None  # type: ignore
    LokiHTTPClient = None  # type: ignore
    _integration_import_error = exc


def build_prometheus_client() -> PrometheusClient:
    url = os.getenv("SREAGENT_PROMETHEUS_URL")
    if not url:
        return mock_prometheus
    if PrometheusHTTPClient is None:
        raise RuntimeError(
            "SREAGENT_PROMETHEUS_URL is configured but the Prometheus HTTP client "
            "could not be imported."
        ) from _integration_import_error

    p95_metric = os.getenv("SREAGENT_PROMETHEUS_P95_METRIC")
    return PrometheusHTTPClient(url, p95_metric)


def build_loki_client() -> LokiClient:
    url = os.getenv("SREAGENT_LOKI_URL")
    if not url:
        return mock_loki
    if LokiHTTPClient is None:
        raise RuntimeError(
            "SREAGENT_LOKI_URL is configured but the Loki HTTP client could not be "
            "imported."
        ) from _integration_import_error

    return LokiHTTPClient(url)


def close_client(client: Any) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


def get_prometheus_client(request: Request) -> PrometheusClient:
    client = getattr(request.app.state, "prometheus_client", None)
    if client is not None:
        return client

    return build_prometheus_client()


def get_loki_client(request: Request) -> LokiClient:
    client = getattr(request.app.state, "loki_client", None)
    if client is not None:
        return client

    return build_loki_client()


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
