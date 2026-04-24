import logging

from fastapi import BackgroundTasks

from app.domain.models import AlertResponse
from app.notifications.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, telegram_notifier: TelegramNotifier):
        self._telegram_notifier = telegram_notifier

    def schedule_alert_delivery(
        self,
        background_tasks: BackgroundTasks,
        source: str,
        labels: dict[str, str],
        result: AlertResponse,
    ) -> None:
        if not self._should_send_telegram(source, labels, result):
            return

        background_tasks.add_task(self._send_telegram_notification, result)

    def _should_send_telegram(
        self,
        source: str,
        labels: dict[str, str],
        result: AlertResponse,
    ) -> bool:
        if result.status not in {"analyzed", "observed"}:
            logger.info("notification.skipped_non_active", extra={"status": result.status})
            return False

        if not result.notifications:
            logger.info("notification.skipped_without_preview")
            return False

        if (
            source == "alertmanager"
            and labels.get("alertname") == "TelegramSendFailure"
        ):
            logger.warning("notification.skipped_telegram_feedback_loop")
            return False

        if not self._telegram_notifier.is_enabled:
            logger.info("notification.telegram_disabled")
            return False

        return True

    def _send_telegram_notification(self, result: AlertResponse) -> None:
        message = f"{result.title}\n{result.notifications[0].message}"
        if not self._telegram_notifier.send_text(message):
            logger.warning("notification.telegram_delivery_failed")
