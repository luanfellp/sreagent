import logging

from fastapi import BackgroundTasks

from app.domain.models import AlertResponse
from app.notifications.telegram import TelegramNotifier
from app.notifications.whatsapp import WhatsAppNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        telegram_notifier: TelegramNotifier,
        whatsapp_notifier: WhatsAppNotifier | None = None,
    ):
        self._telegram_notifier = telegram_notifier
        self._whatsapp_notifier = whatsapp_notifier

    def schedule_alert_delivery(
        self,
        background_tasks: BackgroundTasks,
        source: str,
        labels: dict[str, str],
        result: AlertResponse,
    ) -> None:
        for notification in result.notifications:
            if not self._should_send_channel(
                source,
                labels,
                result,
                notification.channel,
            ):
                continue

            if notification.channel == "telegram":
                background_tasks.add_task(
                    self._send_telegram_notification,
                    result.title,
                    notification.message,
                )
            elif notification.channel == "whatsapp":
                background_tasks.add_task(
                    self._send_whatsapp_notification,
                    result.title,
                    notification.message,
                )

    def _should_send_channel(
        self,
        source: str,
        labels: dict[str, str],
        result: AlertResponse,
        channel: str,
    ) -> bool:
        if result.status not in {"analyzed", "observed"}:
            logger.info("notification.skipped_non_active", extra={"status": result.status})
            return False

        if not result.notifications:
            logger.info("notification.skipped_without_preview")
            return False

        if (
            source == "alertmanager"
            and labels.get("alertname") in {"TelegramSendFailure", "WhatsAppSendFailure"}
        ):
            logger.warning("notification.skipped_notification_feedback_loop")
            return False

        if channel == "telegram":
            if not self._telegram_notifier.is_enabled:
                logger.info("notification.telegram_disabled")
                return False
            return True

        if channel == "whatsapp":
            if self._whatsapp_notifier is None or not self._whatsapp_notifier.is_enabled:
                logger.info("notification.whatsapp_disabled")
                return False
            return True

        logger.warning(
            "notification.skipped_unsupported_preview_channel",
            extra={"channel": channel},
        )
        return False

    def _send_telegram_notification(self, title: str, message: str) -> None:
        if not self._telegram_notifier.send_text(f"{title}\n{message}"):
            logger.warning("notification.telegram_delivery_failed")

    def _send_whatsapp_notification(self, title: str, message: str) -> None:
        if self._whatsapp_notifier is None:
            return
        if not self._whatsapp_notifier.send_text(f"{title}\n{message}"):
            logger.warning("notification.whatsapp_delivery_failed")
