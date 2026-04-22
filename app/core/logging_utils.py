import json
import logging
from typing import Any


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(
        level, json.dumps({"event": event, **fields}, default=str, sort_keys=True)
    )
