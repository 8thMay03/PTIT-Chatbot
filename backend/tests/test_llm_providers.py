import json
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.generation.llm import answer_with_llm, stream_answer_with_llm
from app.llm import (
    AzureOpenAIProvider,
    BaseLLMProvider,
    GeminiProvider,
    LLMConfigurationError,
    LLMMessage,
    LLMProviderError,
    OpenAICompatibleProvider,
    OpenAIProvider,
    get_llm_provider,
    register_llm_provider,
)


class MockCustomProvider(BaseLLMProvider):
    def __init__(self, response_text: str = "Mock answer [1]") -> None:
        super().__init__(model_name="mock-model")
        self.response_text = response_text
        self.generate_called = False
        self.stream_called = False

    def is_configured(self) -> bool:
        return True

    def generate(self, messages, temperature=0.0, max_tokens=None, **kwargs) -> str:
        self.generate_called = True
        return self.response_text

    def generate_stream(self, messages, temperature=0.2, max_tokens=None, **kwargs) -> Iterator[str]:
        self.stream_called = True
        for word in self.response_text.split():
            yield word + " "


class UnconfiguredProvider(BaseLLMProvider):
    def is_configured(self) -> bool:
        return False

    def generate(self, messages, temperature=0.0, max_tokens=None, **kwargs) -> str:
        raise LLMConfigurationError("Provider not configured")

    def generate_stream(self, messages, temperature=0.2, max_tokens=None, **kwargs) -> Iterator[str]:
        raise LLMConfigurationError("Provider not configured")


def test_base_provider_retry_succeeds_after_transient_failure() -> None:
    attempts = 0

    class TransientFailProvider(BaseLLMProvider):
        def is_configured(self) -> bool:
            return True

        def generate(self, messages, **kwargs) -> str:
            def _call():
                nonlocal attempts
                attempts += 1
                if attempts < 2:
                    raise ValueError("Temporary connection drop")
                return "Success after retry"

            return self._execute_with_retry(_call, operation_name="Test")

        def generate_stream(self, messages, **kwargs):
            yield "unused"

    provider = TransientFailProvider(max_retries=2)
    with patch("time.sleep", return_value=None):
        result = provider.generate([{"role": "user", "content": "hello"}])

    assert result == "Success after retry"
    assert attempts == 2


def test_base_provider_retry_raises_error_after_max_retries() -> None:
    class AlwaysFailProvider(BaseLLMProvider):
        def is_configured(self) -> bool:
            return True

        def generate(self, messages, **kwargs) -> str:
            def _call():
                raise ConnectionError("Server unreachable")

            return self._execute_with_retry(_call, operation_name="FailTest")

        def generate_stream(self, messages, **kwargs):
            yield "unused"

    provider = AlwaysFailProvider(max_retries=1)
    with patch("time.sleep", return_value=None):
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate([{"role": "user", "content": "hello"}])

    assert "FailTest failed" in str(exc_info.value)


def test_openai_provider_generate() -> None:
    provider = OpenAIProvider(api_key="test-key", model_name="gpt-4.1-mini")
    assert provider.is_configured() is True

    fake_client = MagicMock()
    fake_choice = SimpleNamespace(message=SimpleNamespace(content="PTIT response [1]"))
    fake_client.chat.completions.create.return_value = SimpleNamespace(choices=[fake_choice])
    provider._client = fake_client

    messages = [LLMMessage(role="user", content="Học phí PTIT?")]
    result = provider.generate(messages)

    assert result == "PTIT response [1]"
    fake_client.chat.completions.create.assert_called_once()


def test_openai_provider_generate_stream() -> None:
    provider = OpenAIProvider(api_key="test-key", model_name="gpt-4.1-mini")

    fake_client = MagicMock()
    chunk1 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Học "))])
    chunk2 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="phí "))])
    fake_client.chat.completions.create.return_value = iter([chunk1, chunk2])
    provider._client = fake_client

    chunks = list(provider.generate_stream([{"role": "user", "content": "Học phí"}]))
    assert chunks == ["Học ", "phí "]


def test_gemini_provider_message_conversion() -> None:
    provider = GeminiProvider(api_key="test-key", model_name="gemini-1.5-flash")
    assert provider.is_configured() is True

    messages = [
        {"role": "system", "content": "Bạn là trợ lý PTIT."},
        {"role": "user", "content": "Học phí bao nhiêu?"},
        {"role": "assistant", "content": "Khoảng 20 triệu."},
        {"role": "user", "content": "Còn học bổng?"},
    ]

    system_instruction, contents = provider._convert_messages(messages)
    assert system_instruction == {"parts": [{"text": "Bạn là trợ lý PTIT."}]}
    assert contents == [
        {"role": "user", "parts": [{"text": "Học phí bao nhiêu?"}]},
        {"role": "model", "parts": [{"text": "Khoảng 20 triệu."}]},
        {"role": "user", "parts": [{"text": "Còn học bổng?"}]},
    ]


def test_gemini_provider_generate_mock_http() -> None:
    provider = GeminiProvider(api_key="test-key", model_name="gemini-1.5-flash")

    mock_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Câu trả lời từ Gemini [1]"}]
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        answer = provider.generate([{"role": "user", "content": "Chào"}])

    assert answer == "Câu trả lời từ Gemini [1]"


def test_gemini_provider_generate_stream_mock_http() -> None:
    provider = GeminiProvider(api_key="test-key", model_name="gemini-1.5-flash")

    mock_sse_lines = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "Gemini "}]}}]}\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "streaming"}]}}]}\n',
        b'data: [DONE]\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(mock_sse_lines)
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        chunks = list(provider.generate_stream([{"role": "user", "content": "Chào"}]))

    assert chunks == ["Gemini ", "streaming"]


def test_azure_openai_provider_configuration() -> None:
    provider = AzureOpenAIProvider(
        api_key="azure-key",
        endpoint="https://my-resource.openai.azure.com",
        deployment_name="gpt-4-deployment",
    )
    assert provider.is_configured() is True

    unconfigured = AzureOpenAIProvider()
    assert unconfigured.is_configured() is False


def test_openai_compatible_provider() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model_name="llama3",
    )
    assert provider.is_configured() is True

    fake_client = MagicMock()
    fake_choice = SimpleNamespace(message=SimpleNamespace(content="Ollama response [1]"))
    fake_client.chat.completions.create.return_value = SimpleNamespace(choices=[fake_choice])
    provider._client = fake_client

    result = provider.generate([{"role": "user", "content": "Test"}])
    assert result == "Ollama response [1]"


def test_llm_factory_resolves_providers(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.llm_provider", "openai")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)

    gemini_provider = get_llm_provider("gemini")
    assert isinstance(gemini_provider, GeminiProvider)

    azure_provider = get_llm_provider("azure")
    assert isinstance(azure_provider, AzureOpenAIProvider)

    local_provider = get_llm_provider("local")
    assert isinstance(local_provider, OpenAICompatibleProvider)

    # Custom registration
    register_llm_provider("custom_mock", lambda: MockCustomProvider("custom response"))
    custom = get_llm_provider("custom_mock")
    assert isinstance(custom, MockCustomProvider)


def test_answer_with_llm_uses_custom_provider() -> None:
    contexts = [
        {
            "source_name": "handbook.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung học phí.",
        }
    ]
    mock_provider = MockCustomProvider("Học phí theo quy định [1].")
    answer = answer_with_llm("Học phí?", contexts, provider=mock_provider)

    assert mock_provider.generate_called is True
    assert "Học phí theo quy định [1]." in answer


def test_stream_answer_with_llm_uses_custom_provider() -> None:
    contexts = [
        {
            "source_name": "handbook.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung học phí.",
        }
    ]
    mock_provider = MockCustomProvider("Học phí")
    chunks = list(stream_answer_with_llm("Học phí?", contexts, provider=mock_provider))

    assert mock_provider.stream_called is True
    assert "".join(chunks).strip() == "Học phí"


def test_answer_with_llm_falls_back_to_extractive_when_unconfigured() -> None:
    contexts = [
        {
            "source_name": "handbook.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung học phí trích xuất.",
        }
    ]
    answer = answer_with_llm("Học phí?", contexts, provider=UnconfiguredProvider())
    assert "Chưa cấu hình API Key cho LLM" in answer
    assert "Nội dung học phí trích xuất" in answer
