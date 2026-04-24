from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai.base import BaseLLMProvider
from app.core.settings import Settings, get_settings
from app.dependencies import (
    get_kubernetes_client,
    get_llm_provider,
    get_loki_client,
    get_prometheus_client,
    get_slack_client,
    require_api_token,
)
from app.domain.llm_models import LLMAnalysisResult
from app.domain.models import AlertInput, AlertResponse
from app.integrations.interfaces import (
    KubernetesClient,
    LokiClient,
    PrometheusClient,
    SlackClient,
)
from app.services.incident_pipeline import analyze_alert
from app.services.summarization import summarize_alert
import os
import httpx

import time
import logging
from prometheus_client import Counter

logger = logging.getLogger("sreagent.telegram")

TELEGRAM_SEND_SUCCESS = Counter('sreagent_telegram_send_success_total','Telegram sends success total')
TELEGRAM_SEND_FAILURE = Counter('sreagent_telegram_send_failure_total','Telegram sends failure total')

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

SEVERITY_ALIASES = {
    "warning": "medium",
    "warn": "medium",
    "error": "high",
}

def _send_telegram_with_retry(bot: str, chat: str, text: str, attempts: int = 3, backoff: float = 1.0) -> bool:
    url = f"https://api.telegram.org/bot{bot}/sendMessage"
    for i in range(attempts):
        try:
            resp = httpx.post(url, json={"chat_id": chat, "text": text}, timeout=5)
            if resp.status_code == 200:
                logger.info("Telegram message sent (attempt %d)", i + 1)
                TELEGRAM_SEND_SUCCESS.inc()
                return True
            else:
                logger.warning("Telegram send failed (attempt %d): status=%s body=%s", i + 1, resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Telegram send exception (attempt %d): %s", i + 1, e)
        if i == attempts - 1:
            break
        time.sleep(backoff * (2 ** i))
    logger.error("Telegram send failed after %d attempts", attempts)
    TELEGRAM_SEND_FAILURE.inc()
    return False


def _normalize_severity(value: str | None) -> str:
    normalized = (value or "info").strip().lower()
    return SEVERITY_ALIASES.get(normalized, normalized)


def _shared_mapping(alerts: list[dict], field: str) -> dict[str, str]:
    if not alerts:
        return {}

    first = alerts[0].get(field, {}) or {}
    shared = {key: str(value) for key, value in first.items()}
    for alert in alerts[1:]:
        current = alert.get(field, {}) or {}
        shared = {
            key: value
            for key, value in shared.items()
            if key in current and str(current[key]) == value
        }
    return shared


def _highest_group_severity(alerts: list[dict], labels: dict[str, str]) -> str:
    candidates = [labels.get("severity")]
    candidates.extend((alert.get("labels", {}) or {}).get("severity") for alert in alerts)
    normalized = [_normalize_severity(value) for value in candidates if value]
    if not normalized:
        return "critical"
    return max(normalized, key=lambda value: SEVERITY_RANK.get(value, -1))


def _normalize_alertmanager_payload(payload: dict) -> tuple[AlertInput, bool, int]:
    alerts = payload.get("alerts") or []
    if not alerts:
        alerts = [payload]

    payload_status = str(payload.get("status") or "").strip().lower()
    statuses = {
        str((alert.get("status") or payload_status or "firing")).strip().lower()
        for alert in alerts
    }
    is_resolved = bool(statuses) and statuses == {"resolved"}

    common_labels = payload.get("commonLabels") or _shared_mapping(alerts, "labels")
    common_annotations = payload.get("commonAnnotations") or _shared_mapping(
        alerts, "annotations"
    )

    labels = {key: str(value) for key, value in common_labels.items()}
    labels["alert_count"] = str(len(alerts))
    labels["alertmanager_status"] = "resolved" if is_resolved else "firing"

    if "service" not in labels:
        services = {
            str((alert.get("labels", {}) or {}).get("service")).strip()
            for alert in alerts
            if (alert.get("labels", {}) or {}).get("service")
        }
        if len(services) == 1:
            labels["service"] = services.pop()

    if "environment" not in labels:
        environments = {
            str((alert.get("labels", {}) or {}).get("environment")).strip()
            for alert in alerts
            if (alert.get("labels", {}) or {}).get("environment")
        }
        if len(environments) == 1:
            labels["environment"] = environments.pop()

    severity = _highest_group_severity(alerts, labels)

    annotations = common_annotations
    message = (
        annotations.get("summary")
        or annotations.get("description")
        or labels.get("alertname")
        or "alert"
    )
    if len(alerts) > 1:
        message = f"{message} ({len(alerts)} alerts grouped by Alertmanager)"

    return (
        AlertInput(
            source="alertmanager",
            severity=severity,
            message=message,
            labels=labels,
        ),
        is_resolved,
        len(alerts),
    )


def _build_resolved_response(alert: AlertInput, alert_count: int) -> AlertResponse:
    service = alert.labels.get("service") or alert.source
    environment = alert.labels.get("environment", "unknown")
    title = f"✅ Alerta resolvido em {service}"
    next_steps = [
        "Validar se a recuperação permaneceu estável antes de encerrar a investigação.",
    ]
    return AlertResponse(
        mode="read-only",
        status="resolved",
        title=title,
        alert={
            "source": alert.source,
            "severity": alert.severity,
            "message": alert.message,
            "service": service,
            "environment": environment,
            "labels": alert.labels,
        },
        signals={
            "recent_deploy": False,
            "dominant_error": None,
            "restart_detected": False,
            "crashloop_detected": False,
        },
        correlation={
            "dedup_key": f"{service}:{environment}:{alert.severity}",
            "rule": "alertmanager-resolved",
            "confidence": "low",
        },
        evidence=[],
        hypotheses=[],
        diagnosis={
            "probable_component": service,
            "probable_failure_type": "resolved",
            "probable_scope": "single-service",
            "confidence": "low",
            "supporting_evidence_ids": [],
        },
        llm_analysis=LLMAnalysisResult(
            summary=(
                f"Alertmanager reportou a resolucao de {alert_count} alerta(s) para "
                f"{service} em {environment}; nenhuma nova analise foi executada."
            ),
            hypotheses_refined=[],
            next_steps=next_steps,
            confidence_notes=[
                "O grupo chegou com status resolved e foi tratado sem reenviar notificacoes.",
            ],
        ),
        actions=next_steps,
        notifications=[],
    )


def _should_send_telegram(alert: AlertInput, result: AlertResponse) -> bool:
    if result.status not in {"analyzed", "observed"}:
        return False
    if not result.notifications:
        return False
    if alert.source == "alertmanager" and alert.labels.get("alertname") == "TelegramSendFailure":
        return False
    return True


def _load_telegram_bot_token() -> str | None:
    bot = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN")
    token_file = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN_FILE")
    if bot or not token_file:
        return bot

    try:
        with open(token_file, encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return None


def _send_result_to_telegram(alert: AlertInput, result: AlertResponse) -> None:
    if not _should_send_telegram(alert, result):
        return

    bot = _load_telegram_bot_token()
    chat = os.getenv("SREAGENT_TELEGRAM_CHAT_ID")
    if not bot or not chat:
        return

    try:
        text = f"{result.title}\n{result.notifications[0].message}"
        _send_telegram_with_retry(bot, chat, text)
    except Exception as exc:
        logger.warning("Telegram notification skipped after unexpected error: %s", exc)


def _analyze_and_summarize(
    alert: AlertInput,
    llm_provider: BaseLLMProvider,
    prometheus_client: PrometheusClient,
    loki_client: LokiClient,
    kubernetes_client: KubernetesClient,
    slack_client: SlackClient,
) -> AlertResponse:
    incident = analyze_alert(
        alert,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
    )
    return summarize_alert(incident, slack_client)


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
    slack_client: Annotated[SlackClient, Depends(get_slack_client)],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AlertResponse:
    result = _analyze_and_summarize(
        alert,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
        slack_client,
    )
    if settings.read_only_mode:
        background_tasks.add_task(_send_result_to_telegram, alert, result)

    return result


@router.post("/alertmanager", response_model=AlertResponse, dependencies=[Depends(require_api_token)])
def create_alert_from_alertmanager(
    background_tasks: BackgroundTasks,
    payload: dict,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    slack_client: Annotated[SlackClient, Depends(get_slack_client)],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AlertResponse:
    """
    Accept Alertmanager webhook payload and convert it to an internal AlertInput.
    Grouped alerts are normalized using common labels/annotations when available.
    Resolved groups are acknowledged without triggering a fresh incident analysis.
    """
    alert_input, is_resolved, alert_count = _normalize_alertmanager_payload(payload)
    if is_resolved:
        return _build_resolved_response(alert_input, alert_count)

    result = _analyze_and_summarize(
        alert_input,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
        slack_client,
    )
    if settings.read_only_mode:
        background_tasks.add_task(_send_result_to_telegram, alert_input, result)

    return result
