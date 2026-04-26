import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "SREAgent"
    read_only_mode: bool = True
    api_token: str | None = None
    alertmanager_emit_resolved: bool = False
    enable_llm: bool = False
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"
    llm_timeout_seconds: float = 15.0
    telegram_chat_id: str | None = None
    telegram_bot_token: str | None = None
    telegram_bot_token_file: str | None = None
    notification_channels: str = "telegram"
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_access_token_file: str | None = None
    whatsapp_to: str | None = None
    grafana_url: str | None = None
    prometheus_url: str | None = None
    zabbix_url: str | None = None
    kubernetes_api_url: str | None = None
    kubernetes_namespace: str | None = None
    kubernetes_label_key: str = "app"
    kubernetes_token_file: str | None = None
    kubernetes_ca_cert_file: str | None = None
    incident_history_limit: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("SREAGENT_APP_NAME", "SREAgent"),
        read_only_mode=os.getenv("SREAGENT_READ_ONLY_MODE", "true").lower()
        in {"1", "true", "yes", "on"},
        api_token=os.getenv("SREAGENT_API_TOKEN"),
        alertmanager_emit_resolved=os.getenv(
            "SREAGENT_ALERTMANAGER_EMIT_RESOLVED", "false"
        ).lower()
        in {"1", "true", "yes", "on"},
        enable_llm=os.getenv("SREAGENT_ENABLE_LLM", "false").lower()
        in {"1", "true", "yes", "on"},
        llm_provider=os.getenv("SREAGENT_LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("SREAGENT_OPENAI_API_KEY"),
        openai_model=os.getenv("SREAGENT_OPENAI_MODEL", "gpt-5"),
        llm_timeout_seconds=float(os.getenv("SREAGENT_LLM_TIMEOUT_SECONDS", "15")),
        telegram_chat_id=os.getenv("SREAGENT_TELEGRAM_CHAT_ID"),
        telegram_bot_token=os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN"),
        telegram_bot_token_file=os.getenv("SREAGENT_TELEGRAM_BOT_TOKEN_FILE"),
        notification_channels=os.getenv("SREAGENT_NOTIFICATION_CHANNELS", "telegram"),
        whatsapp_phone_number_id=os.getenv("SREAGENT_WHATSAPP_PHONE_NUMBER_ID"),
        whatsapp_access_token=os.getenv("SREAGENT_WHATSAPP_ACCESS_TOKEN"),
        whatsapp_access_token_file=os.getenv("SREAGENT_WHATSAPP_ACCESS_TOKEN_FILE"),
        whatsapp_to=os.getenv("SREAGENT_WHATSAPP_TO"),
        grafana_url=os.getenv("SREAGENT_GRAFANA_URL"),
        prometheus_url=os.getenv("SREAGENT_PROMETHEUS_URL"),
        zabbix_url=os.getenv("SREAGENT_ZABBIX_URL"),
        kubernetes_api_url=os.getenv("SREAGENT_KUBERNETES_API_URL"),
        kubernetes_namespace=os.getenv("SREAGENT_KUBERNETES_NAMESPACE"),
        kubernetes_label_key=os.getenv("SREAGENT_KUBERNETES_LABEL_KEY", "app"),
        kubernetes_token_file=os.getenv("SREAGENT_KUBERNETES_TOKEN_FILE"),
        kubernetes_ca_cert_file=os.getenv("SREAGENT_KUBERNETES_CA_CERT_FILE"),
        incident_history_limit=int(os.getenv("SREAGENT_INCIDENT_HISTORY_LIMIT", "100")),
    )
