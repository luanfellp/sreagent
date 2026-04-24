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
import os
import httpx

import time
import logging
from prometheus_client import Counter

logger = logging.getLogger("sreagent.telegram")

TELEGRAM_SEND_SUCCESS = Counter('sreagent_telegram_send_success_total','Telegram sends success total')
TELEGRAM_SEND_FAILURE = Counter('sreagent_telegram_send_failure_total','Telegram sends failure total')

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
        time.sleep(backoff * (2 ** i))
    logger.error("Telegram send failed after %d attempts", attempts)
    TELEGRAM_SEND_FAILURE.inc()
    return False


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
    result = summarize_alert(incident, slack_client)

    # If Telegram is configured, send the agent summary there
    bot = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN")
    token_file = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN_FILE")
    if not bot and token_file:
        try:
            with open(token_file) as f:
                bot = f.read().strip()
        except Exception:
            bot = None
    chat = os.getenv("SREAGENT_TELEGRAM_CHAT_ID")
    if bot and chat and result.notifications:
        try:
            # send plain text (no markdown) to avoid Telegram "can't parse entities" errors
            text = f"{result.title}\n{result.notifications[0].message}"
            _send_telegram_with_retry(bot, chat, text)
        except Exception as exc:
            logger.warning("Telegram notification skipped after unexpected error: %s", exc)

    return result


@router.post("/alertmanager", response_model=AlertResponse, dependencies=[Depends(require_api_token)])
def create_alert_from_alertmanager(
    payload: dict,
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
    kubernetes_client: Annotated[KubernetesClient, Depends(get_kubernetes_client)],
    slack_client: Annotated[SlackClient, Depends(get_slack_client)],
    llm_provider: Annotated[BaseLLMProvider, Depends(get_llm_provider)],
) -> AlertResponse:
    """
    Accept Alertmanager webhook payload and convert to internal AlertInput.
    If multiple alerts are present, process the first one.
    """
    alerts = payload.get("alerts") or []
    if not alerts:
        # fallback: try to parse a single alert-like payload
        alerts = [payload]

    a = alerts[0]
    labels = a.get("labels", {}) or {}
    annotations = a.get("annotations", {}) or {}

    normalized = {
        "source": "alertmanager",
        "severity": labels.get("severity", "critical"),
        "message": annotations.get("summary") or annotations.get("description") or labels.get("alertname", "alert"),
        "labels": {k: str(v) for k, v in labels.items()},
    }

    alert_input = AlertInput(**normalized)

    incident = analyze_alert(
        alert_input,
        llm_provider,
        prometheus_client,
        loki_client,
        kubernetes_client,
    )

    result = summarize_alert(incident, slack_client)

    # If Telegram is configured, send the agent summary there
    bot = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN")
    token_file = os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN_FILE")
    if not bot and token_file:
        try:
            with open(token_file) as f:
                bot = f.read().strip()
        except Exception:
            bot = None
    chat = os.getenv("SREAGENT_TELEGRAM_CHAT_ID")
    if bot and chat and result.notifications:
        try:
            # send plain text (no markdown) to avoid Telegram "can't parse entities" errors
            text = f"{result.title}\n{result.notifications[0].message}"
            _send_telegram_with_retry(bot, chat, text)
        except Exception as exc:
            logger.warning("Telegram notification skipped after unexpected error: %s", exc)

    return result
