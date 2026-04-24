import pytest
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import create_app


def test_app_refuses_to_start_without_read_only_mode(monkeypatch) -> None:
    monkeypatch.setenv("SREAGENT_READ_ONLY_MODE", "false")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="read-only"):
            with TestClient(create_app()):
                pass
    finally:
        monkeypatch.delenv("SREAGENT_READ_ONLY_MODE", raising=False)
        get_settings.cache_clear()
