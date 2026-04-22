import logging
from functools import lru_cache

from app.ai.base import BaseLLMProvider
from app.ai.mock_provider import MockLLMProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.logging_utils import log_event
from app.core.settings import Settings


logger = logging.getLogger(__name__)


@lru_cache
def _build_llm_provider(
    enable_llm: bool,
    provider_name: str,
    openai_api_key: str | None,
    openai_model: str,
    timeout_seconds: float,
) -> BaseLLMProvider:
    if not enable_llm:
        log_event(
            logger,
            logging.INFO,
            "llm.provider.selected",
            provider="mock",
            enabled=False,
        )
        return MockLLMProvider(note="LLM disabled by configuration.")

    if provider_name != "openai":
        log_event(
            logger,
            logging.WARNING,
            "llm.provider.fallback",
            requested_provider=provider_name,
            selected_provider="mock",
            reason="unsupported_provider",
        )
        return MockLLMProvider(
            note=f"Unsupported provider '{provider_name}' configured."
        )

    if not openai_api_key:
        log_event(
            logger,
            logging.WARNING,
            "llm.provider.fallback",
            requested_provider=provider_name,
            selected_provider="mock",
            reason="missing_openai_api_key",
        )
        return MockLLMProvider(note="OpenAI API key missing; mock provider selected.")

    log_event(
        logger,
        logging.INFO,
        "llm.provider.selected",
        provider=provider_name,
        enabled=True,
        model=openai_model,
        timeout_seconds=timeout_seconds,
    )
    try:
        return OpenAIProvider(
            api_key=openai_api_key,
            model=openai_model,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "llm.provider.fallback",
            requested_provider=provider_name,
            selected_provider="mock",
            reason="provider_initialization_failed",
            error=str(exc),
        )
        return MockLLMProvider(
            note="OpenAI provider initialization failed; mock provider selected."
        )


def get_llm_provider_from_settings(settings: Settings) -> BaseLLMProvider:
    return _build_llm_provider(
        enable_llm=settings.enable_llm,
        provider_name=settings.llm_provider,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
