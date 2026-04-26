from app.core.settings import Settings
from app.services.notification_preview import ConfigurableNotificationPreviewBuilder


def test_notification_preview_builder_uses_configured_channels_and_links() -> None:
    builder = ConfigurableNotificationPreviewBuilder(
        Settings(
            notification_channels="telegram,whatsapp",
            grafana_url="http://grafana:3000",
            prometheus_url="http://prometheus:9090",
            zabbix_url="http://zabbix",
        )
    )

    previews = builder.build_notification_previews("Incidente", "Resumo")

    assert [preview.channel for preview in previews] == ["telegram", "whatsapp"]
    assert "Grafana: http://grafana:3000" in previews[0].message
    assert "Prometheus: http://prometheus:9090" in previews[0].message
    assert "Zabbix: http://zabbix" in previews[0].message
