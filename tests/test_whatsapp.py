import httpx

from app.notifications.whatsapp import WhatsAppNotifier


def test_whatsapp_notifier_is_disabled_without_required_settings() -> None:
    notifier = WhatsAppNotifier(phone_number_id=None, access_token=None, to=None)

    assert notifier.is_enabled is False


def test_whatsapp_notifier_sends_text(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(200, json={"messages": [{"id": "wamid.test"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    notifier = WhatsAppNotifier(
        phone_number_id="123",
        access_token="token",
        to="5511999999999",
    )

    assert notifier.send_text("hello") is True
    assert calls[0]["url"] == "https://graph.facebook.com/v19.0/123/messages"
    assert calls[0]["json"] == {
        "messaging_product": "whatsapp",
        "to": "5511999999999",
        "type": "text",
        "text": {"preview_url": False, "body": "hello"},
    }
