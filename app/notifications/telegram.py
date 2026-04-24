import logging
import time

import httpx
from prometheus_client import Counter

logger = logging.getLogger(__name__)

TELEGRAM_SEND_SUCCESS = Counter(
    "sreagent_telegram_send_success_total",
    "Telegram sends success total",
)
TELEGRAM_SEND_FAILURE = Counter(
    "sreagent_telegram_send_failure_total",
    "Telegram sends failure total",
)


def _read_bot_token(token: str | None, token_file: str | None) -> str | None:
    if token:
        return token
    if not token_file:
        return None

    try:
        with open(token_file, encoding="utf-8") as file:
            return file.read().strip() or None
    except OSError as exc:
        logger.warning("telegram.token_load_failed", extra={"error": str(exc)})
        return None


class TelegramNotifier:
    def __init__(
        self,
        chat_id: str | None,
        bot_token: str | None,
        timeout_seconds: float = 5.0,
        attempts: int = 3,
        backoff_seconds: float = 1.0,
    ):
        self._chat_id = chat_id
        self._bot_token = bot_token
        self._timeout_seconds = timeout_seconds
        self._attempts = attempts
        self._backoff_seconds = backoff_seconds

    @classmethod
    def from_settings(
        cls,
        chat_id: str | None,
        bot_token: str | None,
        bot_token_file: str | None,
    ) -> "TelegramNotifier":
        return cls(
            chat_id=chat_id,
            bot_token=_read_bot_token(bot_token, bot_token_file),
        )

    @property
    def is_enabled(self) -> bool:
        return bool(self._chat_id and self._bot_token)

    def send_text(self, text: str) -> bool:
        if not self.is_enabled:
            logger.info("telegram.disabled_or_unconfigured")
            return False

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        for attempt in range(self._attempts):
            try:
                response = httpx.post(
                    url,
                    json={"chat_id": self._chat_id, "text": text},
                    timeout=self._timeout_seconds,
                )
                if response.status_code == 200:
                    logger.info("telegram.send_success", extra={"attempt": attempt + 1})
                    TELEGRAM_SEND_SUCCESS.inc()
                    return True

                logger.warning(
                    "telegram.send_failed",
                    extra={
                        "attempt": attempt + 1,
                        "status_code": response.status_code,
                        "body": response.text,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "telegram.send_exception",
                    extra={"attempt": attempt + 1, "error": str(exc)},
                )

            if attempt == self._attempts - 1:
                break

            time.sleep(self._backoff_seconds * (2**attempt))

        logger.error("telegram.send_exhausted_retries")
        TELEGRAM_SEND_FAILURE.inc()
        return False
