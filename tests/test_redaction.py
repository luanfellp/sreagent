from app.services.redaction import redact_text, redact_value


def test_redact_text_masks_email_ip_and_token() -> None:
    value = "Contact dev@example.com from 10.0.0.3 with key sk-abcdefghi123456"

    redacted = redact_text(value)

    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_IP]" in redacted
    assert "[REDACTED_TOKEN]" in redacted


def test_redact_value_masks_sensitive_keys() -> None:
    value = {"api_token": "secret-value", "owner": "dev@example.com"}

    redacted = redact_value(value)

    assert redacted["api_token"] == "[REDACTED]"
    assert redacted["owner"] == "[REDACTED_EMAIL]"
