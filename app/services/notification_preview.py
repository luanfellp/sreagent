from app.core.settings import Settings
from app.integrations.models import NotificationMessagePreview


def _configured_channels(value: str) -> list[str]:
    channels = [
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    ]
    allowed = {"telegram", "whatsapp"}
    selected = [channel for channel in channels if channel in allowed]
    return selected or ["telegram"]


class ConfigurableNotificationPreviewBuilder:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_notification_preview(
        self, title: str, summary: str
    ) -> NotificationMessagePreview:
        return self.build_notification_previews(title, summary)[0]

    def build_notification_previews(
        self, title: str, summary: str
    ) -> list[NotificationMessagePreview]:
        message = f"🛡️ [SOMENTE LEITURA] {title}\n\n{summary}"
        links = self._links()
        if links:
            message = f"{message}\n\nLinks:\n" + "\n".join(f"- {item}" for item in links)

        return [
            NotificationMessagePreview(channel=channel, message=message)
            for channel in _configured_channels(self._settings.notification_channels)
        ]

    def _links(self) -> list[str]:
        links: list[str] = []
        if self._settings.grafana_url:
            links.append(f"Grafana: {self._settings.grafana_url}")
        if self._settings.prometheus_url:
            links.append(f"Prometheus: {self._settings.prometheus_url}")
        if self._settings.zabbix_url:
            links.append(f"Zabbix: {self._settings.zabbix_url}")
        return links
