from __future__ import annotations

import logging
import threading
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


# Trường settings mà provider đọc lúc tạo (BE-12). Provider được cache theo giá trị các
# trường này; đổi bất kỳ trường nào (PUT /config, reset, chọn profile LLM) thì lần gọi sau
# tạo provider mới. `llm_temperature` đọc lúc gọi nên không cần ở đây.
LLM_SETTINGS_FIELDS: tuple[str, ...] = (
    "llm_provider",
    "llm_timeout",
    "llm_max_retries",
    "openai_api_key",
    "openai_model",
    "openai_base_url",
    "gemini_api_key",
    "gemini_model",
    "azure_openai_api_key",
    "azure_openai_endpoint",
    "azure_openai_deployment_name",
    "azure_openai_api_version",
    "openai_compatible_base_url",
    "openai_compatible_api_key",
    "openai_compatible_model",
)

# Tên provider -> (dấu vân tay cấu hình, provider). Provider cũ bị thay không bị đóng ngay
# (request đang chạy có thể còn dùng); client HTTP tự đóng khi bị thu gom.
_provider_cache: dict[str, tuple[tuple, BaseLLMProvider]] = {}
_provider_cache_lock = threading.Lock()


def register_llm_provider(name: str, factory_fn: Callable[[], BaseLLMProvider]) -> None:
    """Register a custom LLM provider factory."""
    key = name.strip().lower()
    with _provider_cache_lock:
        _PROVIDER_REGISTRY[key] = factory_fn
        _provider_cache.pop(key, None)


def reset_llm_provider_cache() -> None:
    """Bỏ mọi provider đã cache (test)."""
    with _provider_cache_lock:
        _provider_cache.clear()


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


def _settings_fingerprint() -> tuple:
    return tuple(getattr(settings, field) for field in LLM_SETTINGS_FIELDS)


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Get the shared LLM provider for ``provider_name`` (default ``settings.llm_provider``).

    Provider (và client HTTP của nó) được tái dùng giữa các lượt chat cho tới khi cấu hình
    LLM trong ``settings`` đổi. Instance dùng chung giữa các thread: không gán thuộc tính
    lên provider trả về.
    """
    name = (provider_name or settings.llm_provider).strip().lower()

    with _provider_cache_lock:
        factory = _PROVIDER_REGISTRY.get(name)
        if factory is None:
            logger.warning("Unknown LLM provider %r, falling back to 'openai'.", name)
            factory = create_openai_provider
        fingerprint = (factory, *_settings_fingerprint())
        cached = _provider_cache.get(name)
        if cached is not None and cached[0] == fingerprint:
            return cached[1]
        provider = factory()
        _provider_cache[name] = (fingerprint, provider)
        return provider


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

