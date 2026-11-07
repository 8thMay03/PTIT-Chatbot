"""Factory embedding nghiêm ngặt và runtime embedding dùng chung (BE-13).

- AC-04: ``sentence-transformers`` tải lỗi / provider không hỗ trợ → lỗi rõ, không quay về
  ``HashEmbeddingModel``; ``EMBEDDING_PROVIDER=hash`` dùng ``VECTOR_DIM`` chiều.
- AC-05: ``VECTOR_DIM`` khác cột ``Vector(1536)`` hoặc mô hình trả sai số chiều → ``error``.
- AC-06: đã ``ready`` thì ghim; chưa ``ready`` thì nhớ lỗi theo cấu hình, cấu hình đổi thì
  thử lại; nhiều thread chỉ tạo một lần.

Mỗi test dùng một ``EmbeddingRuntime`` mới; factory được thay qua monkeypatch, không gọi mạng.
"""

from __future__ import annotations

import threading
import time

import pytest

from app.core.config import settings
from app.embeddings import (
    EmbeddingModel,
    EmbeddingNotConfiguredError,
    EmbeddingRuntime,
    EmbeddingUnavailableError,
    HashEmbeddingModel,
    OpenAIEmbeddingModel,
    create_embedding_model,
    embedder,
)
from app.embeddings.embedder import VECTOR_COLUMN_DIM
from app.embeddings.runtime import RuntimeEmbeddingModel

SECRET_KEY = "sk-unit-test-secret-key-0123456789"


class _FixedModel(EmbeddingModel):
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [[0.1] * self.dimensions for _ in texts]


@pytest.fixture(autouse=True)
def _embedding_settings(monkeypatch):
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embedding_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "vector_dim", VECTOR_COLUMN_DIM)


@pytest.fixture
def factory(monkeypatch):
    """Thay ``app.embeddings.create_embedding_model``; ``factory.result`` là model hoặc lỗi trả về."""

    class _Factory:
        calls = 0
        result: object = None

        def __call__(self):
            self.calls += 1
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result

    fake = _Factory()
    monkeypatch.setattr("app.embeddings.create_embedding_model", fake)
    return fake


# ==========================================
# Factory (AC-04, AC-05)
# ==========================================
def test_openai_without_key_is_not_configured() -> None:
    with pytest.raises(EmbeddingNotConfiguredError) as info:
        create_embedding_model()
    assert info.value.state == "not_configured"
    assert "API key" in info.value.reason


def test_openai_with_key_creates_model_without_network(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", SECRET_KEY)
    assert isinstance(create_embedding_model(), OpenAIEmbeddingModel)


def test_openai_client_failure_reason_has_no_sdk_message(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_api_key", SECRET_KEY)

    def broken(model_name, api_key):
        raise RuntimeError(f"bad key {api_key}")

    monkeypatch.setattr(embedder, "OpenAIEmbeddingModel", broken)
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert info.value.state == "error"
    assert "RuntimeError" in info.value.reason
    assert SECRET_KEY not in info.value.reason


def test_sentence_transformers_load_failure_is_error_not_hash(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "sentence-transformers")
    monkeypatch.setattr(settings, "embedding_model", "unit-test/missing-model")

    def broken(model_name):
        raise OSError("không tải được từ mạng")

    monkeypatch.setattr(embedder, "SentenceTransformerEmbeddingModel", broken)
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert info.value.state == "error"
    assert "unit-test/missing-model" in info.value.reason
    assert "OSError" in info.value.reason


def test_sentence_transformers_dimension_must_match_vector_dim(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "sentence-transformers")
    monkeypatch.setattr(embedder, "SentenceTransformerEmbeddingModel", lambda name: _FixedModel(384))
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert "384" in info.value.reason
    assert f"VECTOR_DIM={VECTOR_COLUMN_DIM}" in info.value.reason


@pytest.mark.parametrize("provider", ["cohere", "gemini", "lạ"])
def test_unsupported_provider_is_error(monkeypatch, provider) -> None:
    monkeypatch.setattr(settings, "embedding_provider", provider)
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert info.value.state == "error"
    assert "chưa được hỗ trợ" in info.value.reason


def test_hash_provider_uses_vector_dim(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    model = create_embedding_model()
    assert isinstance(model, HashEmbeddingModel)
    assert len(model.embed(["học phí"])[0]) == VECTOR_COLUMN_DIM


def test_vector_dim_must_match_vector_column(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    monkeypatch.setattr(settings, "vector_dim", 768)
    with pytest.raises(EmbeddingUnavailableError) as info:
        create_embedding_model()
    assert "VECTOR_DIM=768" in info.value.reason
    assert str(VECTOR_COLUMN_DIM) in info.value.reason


# ==========================================
# Runtime (AC-04..AC-06)
# ==========================================
def test_runtime_is_lazy_and_reports_not_configured() -> None:
    runtime = EmbeddingRuntime()
    with pytest.raises(EmbeddingNotConfiguredError):
        runtime.get()
    status = runtime.status()
    assert status["state"] == "not_configured"
    assert status["provider"] == "openai"
    assert status["reason"]


def test_runtime_unsupported_provider_status_is_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "cohere")
    status = EmbeddingRuntime().status()
    assert status["state"] == "error"
    assert "chưa được hỗ trợ" in status["reason"]


def test_failure_is_remembered_until_config_changes(factory, monkeypatch) -> None:
    runtime = EmbeddingRuntime()
    factory.result = EmbeddingUnavailableError("Không tải được mô hình (OSError).")
    for _ in range(3):
        with pytest.raises(EmbeddingUnavailableError):
            runtime.get()
    runtime.status()
    assert factory.calls == 1

    # Lưu key mới (qua /config): lần dùng kế tiếp tạo lại, không cần restart.
    model = _FixedModel(VECTOR_COLUMN_DIM)
    factory.result = model
    monkeypatch.setattr(settings, "openai_api_key", SECRET_KEY)
    assert runtime.get() is model
    assert factory.calls == 2
    assert runtime.status()["state"] == "ready"


def test_unexpected_factory_exception_is_wrapped_without_message(factory) -> None:
    runtime = EmbeddingRuntime()
    factory.result = ValueError(f"lỗi kèm {SECRET_KEY}")
    runtime.warm_up()  # không bao giờ ném
    status = runtime.status()
    assert status["state"] == "error"
    assert "ValueError" in status["reason"]
    assert SECRET_KEY not in status["reason"]


def test_ready_model_is_pinned_when_config_changes(factory, monkeypatch) -> None:
    runtime = EmbeddingRuntime()
    first = _FixedModel(VECTOR_COLUMN_DIM)
    factory.result = first
    monkeypatch.setattr(settings, "openai_api_key", SECRET_KEY)
    assert runtime.get() is first

    factory.result = _FixedModel(VECTOR_COLUMN_DIM)
    monkeypatch.setattr(settings, "openai_api_key", "sk-another-key")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-large")
    assert runtime.get() is first
    assert runtime.status()["state"] == "ready"
    assert factory.calls == 1


def test_concurrent_get_creates_model_once(monkeypatch) -> None:
    runtime = EmbeddingRuntime()
    model = _FixedModel(VECTOR_COLUMN_DIM)
    calls = []

    def slow_factory():
        calls.append(1)
        time.sleep(0.05)
        return model

    monkeypatch.setattr("app.embeddings.create_embedding_model", slow_factory)
    results: list[object] = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(runtime.get())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1
    assert results == [model] * 8


def test_proxy_rejects_wrong_dimension_and_marks_error(factory) -> None:
    runtime = EmbeddingRuntime()
    proxy = RuntimeEmbeddingModel(runtime)
    factory.result = _FixedModel(384)

    with pytest.raises(EmbeddingUnavailableError) as info:
        proxy.embed(["học phí"])
    assert "384" in info.value.reason
    status = runtime.status()
    assert status["state"] == "error"
    assert "384" in status["reason"]
    # Cùng cấu hình: không tạo lại mô hình hỏng ở mỗi request.
    with pytest.raises(EmbeddingUnavailableError):
        runtime.get()
    assert factory.calls == 1


def test_proxy_returns_vectors_of_vector_dim(factory) -> None:
    runtime = EmbeddingRuntime()
    model = _FixedModel(VECTOR_COLUMN_DIM)
    factory.result = model
    vectors = RuntimeEmbeddingModel(runtime).embed(["a", "b"])
    assert [len(vector) for vector in vectors] == [VECTOR_COLUMN_DIM, VECTOR_COLUMN_DIM]
    assert model.calls == 1


def test_load_failure_keeps_current_model(factory) -> None:
    runtime = EmbeddingRuntime()
    current = _FixedModel(VECTOR_COLUMN_DIM)
    runtime.override(current)
    factory.result = EmbeddingUnavailableError("Provider embedding 'cohere' chưa được hỗ trợ.")
    with pytest.raises(EmbeddingUnavailableError):
        runtime.load()
    assert runtime.get() is current

    replacement = _FixedModel(VECTOR_COLUMN_DIM)
    factory.result = replacement
    assert runtime.load() is replacement
    assert runtime.get() is replacement
