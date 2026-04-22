from app.ai.factory import get_llm_provider_from_settings
from app.ai.mock_provider import MockLLMProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.settings import Settings


def test_factory_returns_mock_when_llm_disabled() -> None:
    provider = get_llm_provider_from_settings(Settings(enable_llm=False))

    assert isinstance(provider, MockLLMProvider)


def test_factory_returns_mock_without_openai_key() -> None:
    provider = get_llm_provider_from_settings(
        Settings(enable_llm=True, llm_provider="openai", openai_api_key=None)
    )

    assert isinstance(provider, MockLLMProvider)


def test_factory_returns_openai_provider_when_configuration_is_valid() -> None:
    provider = get_llm_provider_from_settings(
        Settings(
            enable_llm=True,
            llm_provider="openai",
            openai_api_key="test-key",
            openai_model="gpt-5",
            llm_timeout_seconds=10.0,
        )
    )

    assert isinstance(provider, OpenAIProvider)
