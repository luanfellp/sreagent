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
    NotificationPreviewBuilder,
    PrometheusClient,
)
from app.integrations.mocks import (
    mock_kubernetes,
    mock_loki,
    mock_prometheus,
)
from app.notifications.telegram import TelegramNotifier
from app.notifications.whatsapp import WhatsAppNotifier
from app.services.incident_store import IncidentStore
from app.services.notification_preview import ConfigurableNotificationPreviewBuilder
from app.services.notification_service import NotificationService

# Import real HTTP clients if available
try:
    from app.integrations.kubernetes_client import KubernetesHTTPClient
    from app.integrations.loki_client import LokiHTTPClient
    from app.integrations.prometheus_client import PrometheusHTTPClient
    _integration_import_error: ImportError | None = None
except ImportError as exc:
    KubernetesHTTPClient = None  # type: ignore
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


def build_kubernetes_client(settings: Settings | None = None) -> KubernetesClient:
    settings = settings or get_settings()
    url = settings.kubernetes_api_url
    if not url:
        host = os.getenv("KUBERNETES_SERVICE_HOST")
        port = os.getenv("KUBERNETES_SERVICE_PORT", "443")
        if host:
            url = f"https://{host}:{port}"

    if not url:
        return mock_kubernetes
    if KubernetesHTTPClient is None:
        raise RuntimeError(
            "Kubernetes API is configured but the Kubernetes HTTP client could not "
            "be imported."
        ) from _integration_import_error

    return KubernetesHTTPClient(
        url,
        namespace=settings.kubernetes_namespace,
        label_key=settings.kubernetes_label_key,
        token_file=settings.kubernetes_token_file,
        ca_cert_file=settings.kubernetes_ca_cert_file,
    )


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


def get_kubernetes_client(request: Request) -> KubernetesClient:
    client = getattr(request.app.state, "kubernetes_client", None)
    if client is not None:
        return client

    return build_kubernetes_client()


def get_notification_preview_builder(
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationPreviewBuilder:
    return ConfigurableNotificationPreviewBuilder(settings)


def get_incident_store(request: Request) -> IncidentStore:
    store = getattr(request.app.state, "incident_store", None)
    if store is None:
        store = IncidentStore()
        request.app.state.incident_store = store
    return store


def build_telegram_notifier(settings: Settings) -> TelegramNotifier:
    return TelegramNotifier.from_settings(
        chat_id=settings.telegram_chat_id,
        bot_token=settings.telegram_bot_token,
        bot_token_file=settings.telegram_bot_token_file,
    )


def build_whatsapp_notifier(settings: Settings) -> WhatsAppNotifier:
    return WhatsAppNotifier.from_settings(
        phone_number_id=settings.whatsapp_phone_number_id,
        access_token=settings.whatsapp_access_token,
        access_token_file=settings.whatsapp_access_token_file,
        to=settings.whatsapp_to,
    )


def get_notification_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationService:
    service = getattr(request.app.state, "notification_service", None)
    if service is not None:
        return service

    return NotificationService(
        build_telegram_notifier(settings),
        build_whatsapp_notifier(settings),
    )


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
