import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._-]{8,}", re.IGNORECASE)
SENSITIVE_KEYWORDS = {
    "authorization",
    "api_key",
    "apikey",
    "key",
    "password",
    "secret",
    "token",
}


def redact_text(value: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    redacted = IPV4_RE.sub("[REDACTED_IP]", redacted)
    redacted = OPENAI_KEY_RE.sub("[REDACTED_TOKEN]", redacted)
    redacted = BEARER_RE.sub("Bearer [REDACTED_TOKEN]", redacted)
    return redacted


def redact_value(value: Any, field_name: str | None = None) -> Any:
    normalized_field_name = (field_name or "").strip().lower()
    if normalized_field_name and any(
        keyword in normalized_field_name for keyword in SENSITIVE_KEYWORDS
    ):
        return "[REDACTED]"

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item, field_name) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item, key) for key, item in value.items()}
    return value
