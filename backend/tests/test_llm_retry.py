"""Một tầng retry duy nhất cho lời gọi LLM (BE-12, AC-01).

Provider thật (SDK ``openai`` với ``max_retries=0``, Gemini qua ``httpx``) gọi tới
``httpx.MockTransport`` đếm request; không gọi mạng. ``time.sleep`` của backoff được
thay bằng bản ghi lại thời gian chờ.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.generation.llm import stream_answer_deltas_with_llm
from app.llm import (
    AzureOpenAIProvider,
    GeminiProvider,
    LLMProviderError,
    LLMStreamError,
    OpenAICompatibleProvider,
    OpenAIProvider,
)

MESSAGES = [{"role": "user", "content": "Học phí?"}]
CONTEXTS = [{"source_name": "handbook.md", "heading": "Học phí", "section_path": "Học phí", "text": "Nội dung."}]
SECRET_KEY = "sk-test-secret-0123456789abcdef"


def _completion(content: str = "Trả lời [1]") -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-test",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
    }


def _sse_chunk(content: str) -> str:
    chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "gpt-test",
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def _sse_body(*contents: str) -> bytes:
    return ("".join(_sse_chunk(c) for c in contents) + "data: [DONE]\n\n").encode("utf-8")


class CountingTransport(httpx.MockTransport):
    """MockTransport trả lần lượt các response trong ``responses`` (phần tử cuối lặp lại)."""

    def __init__(self, responses: list) -> None:
        self.requests: list[httpx.Request] = []
        self._responses = responses
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        index = min(len(self.requests), len(self._responses)) - 1
        response = self._responses[index]
        return response(request) if callable(response) else response


def _error(status: int, message: str = "upstream error", headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message}}, headers=headers)


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    recorded: list[float] = []
    monkeypatch.setattr("app.llm.base.time.sleep", recorded.append)
    return recorded


def _openai(transport: httpx.MockTransport, max_retries: int = 2) -> OpenAIProvider:
    return OpenAIProvider(
        api_key=SECRET_KEY,
        model_name="gpt-test",
        max_retries=max_retries,
        http_client=httpx.Client(transport=transport),
    )


def _compatible(transport: httpx.MockTransport) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="http://llm.local/v1",
        api_key=SECRET_KEY,
        model_name="local-model",
        http_client=httpx.Client(transport=transport),
    )


def _azure(transport: httpx.MockTransport) -> AzureOpenAIProvider:
    return AzureOpenAIProvider(
        api_key=SECRET_KEY,
        endpoint="https://res.openai.azure.com",
        deployment_name="gpt-deploy",
        http_client=httpx.Client(transport=transport),
    )


def _gemini(transport: httpx.MockTransport) -> GeminiProvider:
    return GeminiProvider(
        api_key="AIzaSyTestKey0123456789abcdefgh",
        model_name="gemini-test",
        http_client=httpx.Client(transport=transport),
    )


PROVIDER_FACTORIES = {
    "openai": _openai,
    "openai_compatible": _compatible,
    "azure": _azure,
    "gemini": _gemini,
}


@pytest.mark.parametrize("name", sorted(PROVIDER_FACTORIES))
def test_persistent_5xx_makes_at_most_one_plus_max_retries_requests(name, sleeps) -> None:
    transport = CountingTransport([_error(500)])
    provider = PROVIDER_FACTORIES[name](transport)

    with pytest.raises(LLMProviderError) as exc_info:
        provider.generate(MESSAGES)

    # SDK không tự retry (max_retries=0): 1 + LLM_MAX_RETRIES (mặc định 2) = 3 request.
    assert len(transport.requests) == 3
    assert exc_info.value.status_code == 500
    assert exc_info.value.retryable is True
    assert len(sleeps) == 2


@pytest.mark.parametrize("name", sorted(PROVIDER_FACTORIES))
@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_are_not_retried(name, status, sleeps) -> None:
    transport = CountingTransport([_error(status)])
    provider = PROVIDER_FACTORIES[name](transport)

    with pytest.raises(LLMProviderError) as exc_info:
        provider.generate(MESSAGES)

    assert len(transport.requests) == 1
    assert exc_info.value.status_code == status
    assert exc_info.value.retryable is False
    assert sleeps == []


def test_transient_failure_then_success_returns_answer(sleeps) -> None:
    transport = CountingTransport([_error(503), _error(502), httpx.Response(200, json=_completion())])

    assert _openai(transport).generate(MESSAGES) == "Trả lời [1]"
    assert len(transport.requests) == 3


def test_max_retries_zero_means_single_request(sleeps) -> None:
    transport = CountingTransport([_error(500)])

    with pytest.raises(LLMProviderError):
        _openai(transport, max_retries=0).generate(MESSAGES)

    assert len(transport.requests) == 1


def test_rate_limit_honours_retry_after(sleeps) -> None:
    transport = CountingTransport(
        [_error(429, headers={"retry-after": "2"}), httpx.Response(200, json=_completion("Sau khi chờ"))]
    )

    assert _openai(transport).generate(MESSAGES) == "Sau khi chờ"
    assert len(transport.requests) == 2
    assert sleeps == [2.0]


def test_retry_after_longer_than_cap_stops_retrying(sleeps) -> None:
    transport = CountingTransport([_error(429, headers={"retry-after": "3600"})])

    with pytest.raises(LLMProviderError) as exc_info:
        _openai(transport).generate(MESSAGES)

    assert len(transport.requests) == 1
    assert exc_info.value.status_code == 429
    assert sleeps == []


def test_network_error_is_retried(sleeps) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = CountingTransport([refuse])

    with pytest.raises(LLMProviderError):
        _openai(transport).generate(MESSAGES)

    assert len(transport.requests) == 3


def test_error_message_and_logs_do_not_contain_api_key(sleeps, caplog) -> None:
    transport = CountingTransport([_error(401, message=f"Incorrect API key provided: {SECRET_KEY}.")])

    with caplog.at_level("DEBUG"), pytest.raises(LLMProviderError) as exc_info:
        _openai(transport).generate(MESSAGES)

    assert SECRET_KEY not in str(exc_info.value)
    assert SECRET_KEY not in caplog.text
    # Admin "thử kết nối" vẫn thấy loại lỗi.
    assert "401" in str(exc_info.value)


def test_stream_open_is_retried_until_first_chunk(sleeps) -> None:
    transport = CountingTransport(
        [
            _error(503),
            _error(503),
            httpx.Response(200, content=_sse_body("Học ", "phí"), headers={"content-type": "text/event-stream"}),
        ]
    )

    chunks = list(_openai(transport).generate_stream(MESSAGES))

    assert chunks == ["Học ", "phí"]
    assert len(transport.requests) == 3
    assert transport.requests[-1].extensions["timeout"]["read"] == pytest.approx(30.0)


class _BrokenStream(httpx.SyncByteStream):
    """Body SSE gửi một chunk rồi đứt kết nối."""

    def __iter__(self):
        yield _sse_chunk("Học ").encode("utf-8")
        raise httpx.ReadError("connection reset by peer")


def test_stream_failure_after_first_chunk_is_not_retried(sleeps) -> None:
    transport = CountingTransport(
        [lambda request: httpx.Response(200, stream=_BrokenStream(), headers={"content-type": "text/event-stream"})]
    )
    provider = _openai(transport)

    deltas = []
    with pytest.raises(LLMStreamError):
        for delta in stream_answer_deltas_with_llm("Học phí?", CONTEXTS, provider=provider):
            deltas.append(delta.text)

    assert deltas == ["Học "]
    assert len(transport.requests) == 1


def test_compatible_stream_deltas_retry_open(sleeps) -> None:
    transport = CountingTransport(
        [_error(500), httpx.Response(200, content=_sse_body("OK"), headers={"content-type": "text/event-stream"})]
    )

    deltas = list(_compatible(transport).generate_stream_deltas(MESSAGES))

    assert [d.text for d in deltas] == ["OK"]
    assert len(transport.requests) == 2


def test_gemini_sends_key_in_header_not_url(sleeps) -> None:
    transport = CountingTransport(
        [httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Xin chào"}]}}]})]
    )
    provider = _gemini(transport)

    assert provider.generate(MESSAGES) == "Xin chào"

    request = transport.requests[0]
    assert "key=" not in str(request.url)
    assert request.headers["x-goog-api-key"] == "AIzaSyTestKey0123456789abcdefgh"


def test_gemini_stream_retries_5xx_and_not_4xx(sleeps) -> None:
    sse = 'data: {"candidates": [{"content": {"parts": [{"text": "Học phí"}]}}]}\n\n'
    ok = CountingTransport([_error(503), httpx.Response(200, content=sse.encode("utf-8"))])
    assert list(_gemini(ok).generate_stream(MESSAGES)) == ["Học phí"]
    assert len(ok.requests) == 2
    assert ok.requests[-1].url.params["alt"] == "sse"
    assert "key" not in ok.requests[-1].url.params

    bad = CountingTransport([_error(400, message="Invalid argument")])
    with pytest.raises(LLMProviderError) as exc_info:
        list(_gemini(bad).generate_stream(MESSAGES))
    assert len(bad.requests) == 1
    assert exc_info.value.status_code == 400


def test_gemini_reuses_one_http_client() -> None:
    transport = CountingTransport(
        [httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "a"}]}}]})]
    )
    provider = GeminiProvider(api_key="AIzaSyTestKey0123456789abcdefgh", model_name="gemini-test")
    provider._http_client = httpx.Client(transport=transport)
    first = provider._get_http_client()

    provider.generate(MESSAGES)
    provider.generate(MESSAGES)

    assert provider._get_http_client() is first
    assert len(transport.requests) == 2
