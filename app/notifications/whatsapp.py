import logging
import time
from pathlib import Path

import httpx
from prometheus_client import Counter

logger = logging.getLogger(__name__)

WHATSAPP_SEND_SUCCESS = Counter(
    "sreagent_whatsapp_send_success_total",
    "WhatsApp sends success total",
)
WHATSAPP_SEND_FAILURE = Counter(
    "sreagent_whatsapp_send_failure_total",
    "WhatsApp sends failure total",
)


def _read_access_token(token: str | None, token_file: str | None) -> str | None:
    if token:
        return token
    if not token_file:
        return None

    try:
        return Path(token_file).read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        logger.warning("whatsapp.token_load_failed", extra={"error": str(exc)})
        return None


class WhatsAppNotifier:
    def __init__(
        self,
        phone_number_id: str | None,
        access_token: str | None,
        to: str | None,
        timeout_seconds: float = 5.0,
        attempts: int = 3,
        backoff_seconds: float = 1.0,
        graph_api_version: str = "v19.0",
    ):
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._to = to
        self._timeout_seconds = timeout_seconds
        self._attempts = attempts
        self._backoff_seconds = backoff_seconds
        self._graph_api_version = graph_api_version

    @classmethod
    def from_settings(
        cls,
        phone_number_id: str | None,
        access_token: str | None,
        access_token_file: str | None,
        to: str | None,
    ) -> "WhatsAppNotifier":
        return cls(
            phone_number_id=phone_number_id,
            access_token=_read_access_token(access_token, access_token_file),
            to=to,
        )

    @property
    def is_enabled(self) -> bool:
        return bool(self._phone_number_id and self._access_token and self._to)

    def send_text(self, text: str) -> bool:
        if not self.is_enabled:
            logger.info("whatsapp.disabled_or_unconfigured")
            return False

        url = (
            f"https://graph.facebook.com/{self._graph_api_version}/"
            f"{self._phone_number_id}/messages"
        )
        headers = {"Authorization": f"Bearer {self._access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": self._to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        for attempt in range(self._attempts):
            try:
                response = httpx.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout_seconds,
                )
                if response.status_code in {200, 201}:
                    logger.info("whatsapp.send_success", extra={"attempt": attempt + 1})
                    WHATSAPP_SEND_SUCCESS.inc()
                    return True

                logger.warning(
                    "whatsapp.send_failed",
                    extra={
                        "attempt": attempt + 1,
                        "status_code": response.status_code,
                        "body": response.text,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "whatsapp.send_exception",
                    extra={"attempt": attempt + 1, "error": str(exc)},
                )

            if attempt == self._attempts - 1:
                break

            time.sleep(self._backoff_seconds * (2**attempt))

        logger.error("whatsapp.send_exhausted_retries")
        WHATSAPP_SEND_FAILURE.inc()
        return False
