from __future__ import annotations

import logging
from typing import Callable

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.providers.azure_openai_provider import AzureOpenAIProvider
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.llm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# Registry of provider factory functions
_PROVIDER_REGISTRY: dict[str, Callable[[], BaseLLMProvider]] = {}


def register_llm_provider(name: str, factory_fn: Callable[[], BaseLLMProvider]) -> None:
    """Register a custom LLM provider factory."""
    _PROVIDER_REGISTRY[name.strip().lower()] = factory_fn


def create_openai_provider() -> OpenAIProvider:
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model_name=settings.openai_model,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def create_gemini_provider() -> GeminiProvider:
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def create_azure_openai_provider() -> AzureOpenAIProvider:
    return AzureOpenAIProvider(
        api_key=settings.azure_openai_api_key,
        endpoint=settings.azure_openai_endpoint,
        deployment_name=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def create_openai_compatible_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key,
        model_name=settings.openai_compatible_model,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


PROVIDER_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "tongyi": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "xai": "https://api.x.ai/v1",
    "ollama": "http://localhost:11434/v1",
    "local": "http://localhost:11434/v1",
    "vllm": "http://localhost:8000/v1",
}

# Register default providers
register_llm_provider("openai", create_openai_provider)
register_llm_provider("gemini", create_gemini_provider)
register_llm_provider("google", create_gemini_provider)
register_llm_provider("azure", create_azure_openai_provider)
register_llm_provider("azure_openai", create_azure_openai_provider)
register_llm_provider("openai_compatible", create_openai_compatible_provider)
register_llm_provider("local", create_openai_compatible_provider)
register_llm_provider("ollama", create_openai_compatible_provider)
register_llm_provider("vllm", create_openai_compatible_provider)
register_llm_provider("deepseek", create_openai_compatible_provider)
register_llm_provider("moonshot", create_openai_compatible_provider)
register_llm_provider("tongyi", create_openai_compatible_provider)
register_llm_provider("qwen", create_openai_compatible_provider)
register_llm_provider("zhipu", create_openai_compatible_provider)
register_llm_provider("xai", create_openai_compatible_provider)


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Get or create an LLM provider based on name or settings.llm_provider."""
    name = (provider_name or settings.llm_provider).strip().lower()

    factory = _PROVIDER_REGISTRY.get(name)
    if factory is not None:
        return factory()

    logger.warning("Unknown LLM provider %r, falling back to 'openai'.", name)
    return create_openai_provider()


def create_llm_provider_from_config(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    endpoint: str | None = None,
    deployment_name: str | None = None,
    api_version: str | None = None,
    timeout: float = 15.0,
) -> BaseLLMProvider:
    """Create a temporary provider instance with explicit credentials for testing/dry-run."""
    name = provider.strip().lower()
    default_base = PROVIDER_DEFAULT_BASE_URLS.get(name)

    if name in ("gemini", "google"):
        return GeminiProvider(
            api_key=api_key or settings.gemini_api_key,
            model_name=model or settings.gemini_model,
            timeout=timeout,
            max_retries=1,
        )
    elif name in ("azure", "azure_openai"):
        return AzureOpenAIProvider(
            api_key=api_key or settings.azure_openai_api_key,
            endpoint=endpoint or settings.azure_openai_endpoint,
            deployment_name=deployment_name or model or settings.azure_openai_deployment_name,
            api_version=api_version or settings.azure_openai_api_version,
            timeout=timeout,
            max_retries=1,
        )
    elif name in (
        "openai_compatible",
        "local",
        "ollama",
        "vllm",
        "deepseek",
        "moonshot",
        "tongyi",
        "qwen",
        "zhipu",
        "xai",
    ):
        return OpenAICompatibleProvider(
            base_url=base_url or default_base or settings.openai_compatible_base_url,
            api_key=api_key or settings.openai_compatible_api_key,
            model_name=model or settings.openai_compatible_model,
            timeout=timeout,
            max_retries=1,
        )
    else:  # default openai
        return OpenAIProvider(
            api_key=api_key or settings.openai_api_key,
            model_name=model or settings.openai_model,
            base_url=base_url or settings.openai_base_url,
            timeout=timeout,
            max_retries=1,
        )

