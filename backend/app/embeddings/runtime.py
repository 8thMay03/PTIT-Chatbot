"""Mô hình nhúng dùng chung cho cả process, tạo lười và an toàn khi nhiều thread.

- Không tạo gì lúc import: thiếu key thì app vẫn khởi động, ``status()`` báo
  ``not_configured`` và route cần embedding trả 503.
- Đã ``ready`` thì ghim: đổi provider/model/key lúc chạy không thay mô hình đang dùng
  (tránh trộn hai không gian vector); cần khởi động lại.
- Chưa ``ready`` thì nhớ lỗi theo dấu vân tay cấu hình (provider, model, key, số chiều):
  cấu hình giữ nguyên → trả lại lỗi đã nhớ, không thử tải lại mỗi request; cấu hình đổi
  (lưu key qua /config, chọn profile) → tạo lại ở lần dùng kế tiếp, không cần restart.
- ``runtime_embedding_model`` kiểm số chiều mỗi lần ``embed``; sai thì chuyển ``error``
  và ném lỗi trước khi bên gọi ghi gì vào DB.
"""

from __future__ import annotations

import hashlib
import logging
import threading

from app.core.config import settings
from app.embeddings.embedder import EmbeddingUnavailableError
from app.embeddings.models import EmbeddingModel

logger = logging.getLogger(__name__)

READY = "ready"


def _settings_fingerprint() -> tuple:
    provider = (settings.embedding_provider or "").strip().lower()
    key = (settings.embedding_api_key or settings.openai_api_key) if provider == "openai" else None
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest() if key else None
    return (provider, settings.embedding_model, key_hash, settings.vector_dim)


class EmbeddingRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: EmbeddingModel | None = None
        self._dimensions: int | None = None
        # Dấu vân tay của lần tạo gần nhất: (provider, model, sha256(key), vector_dim).
        self._fingerprint: tuple | None = None
        # Lỗi của lần tạo gần nhất: (lớp lỗi, lý do). Ném bản mới mỗi lần để traceback không dồn.
        self._failure: tuple[type[EmbeddingUnavailableError], str] | None = None

    def get(self) -> EmbeddingModel:
        """Mô hình đang dùng; tạo ở lần gọi đầu. Ném ``EmbeddingUnavailableError`` nếu không dùng được."""
        return self._acquire()[0]

    def _acquire(self) -> tuple[EmbeddingModel, int]:
        with self._lock:
            if self._model is not None:
                return self._model, self._dimensions
            fingerprint = _settings_fingerprint()
            if self._failure is not None and fingerprint == self._fingerprint:
                error_cls, reason = self._failure
                raise error_cls(reason)
            self._fingerprint = fingerprint
            try:
                model = self._build()
            except EmbeddingUnavailableError as exc:
                self._failure = (type(exc), exc.reason)
                logger.warning("Mô hình nhúng chưa sẵn sàng: %s", exc.reason)
                raise
            self._install(model, fingerprint)
            return model, self._dimensions

    def load(self) -> EmbeddingModel:
        """Tạo mô hình theo settings hiện tại và thay mô hình đang dùng (áp profile embedding).

        Lỗi thì ném ``EmbeddingUnavailableError`` và giữ nguyên trạng thái cũ.
        """
        with self._lock:
            fingerprint = _settings_fingerprint()
            model = self._build()
            self._install(model, fingerprint)
            return model

    def warm_up(self) -> None:
        """Thử tạo mô hình lúc khởi động; chỉ ghi log, không bao giờ ném."""
        try:
            self.get()
        except EmbeddingUnavailableError:
            return
        logger.info("Mô hình nhúng sẵn sàng (%s · %s).", settings.embedding_provider, settings.embedding_model)

    def is_ready(self) -> bool:
        with self._lock:
            return self._model is not None

    def status(self) -> dict:
        """``{state, reason, provider, model}``; ``state`` là ready | not_configured | error."""
        try:
            self.get()
        except EmbeddingUnavailableError:
            pass
        with self._lock:
            provider, model = (self._fingerprint or (None, None))[:2]
            if self._model is not None:
                return {"state": READY, "reason": None, "provider": provider, "model": model}
            if self._failure is None:  # Một thread vừa đánh dấu lỗi rồi thread khác đang tạo lại.
                return {"state": "error", "reason": None, "provider": provider, "model": model}
            error_cls, reason = self._failure
            return {"state": error_cls.state, "reason": reason, "provider": provider, "model": model}

    def mark_failed(self, model: EmbeddingModel, reason: str) -> None:
        """Mô hình ``model`` trả kết quả sai: bỏ nó, chuyển ``error`` cho tới khi cấu hình đổi."""
        with self._lock:
            if self._model is not model:
                return
            self._model = None
            self._dimensions = None
            self._failure = (EmbeddingUnavailableError, reason)
        logger.error("Tắt mô hình nhúng: %s", reason)

    def override(self, model: EmbeddingModel) -> None:
        """Chỉ cho test: dùng ``model`` như mô hình đã ``ready``."""
        with self._lock:
            self._install(model, _settings_fingerprint())

    def reset(self) -> None:
        """Chỉ cho test: về trạng thái chưa tạo."""
        with self._lock:
            self._model = None
            self._dimensions = None
            self._fingerprint = None
            self._failure = None

    def _install(self, model: EmbeddingModel, fingerprint: tuple) -> None:
        self._model = model
        self._dimensions = fingerprint[3]
        self._fingerprint = fingerprint
        self._failure = None

    @staticmethod
    def _build() -> EmbeddingModel:
        # Gọi qua thuộc tính package để monkeypatch("app.embeddings.create_embedding_model") có hiệu lực.
        from app import embeddings

        try:
            return embeddings.create_embedding_model()
        except EmbeddingUnavailableError:
            raise
        except Exception as exc:
            raise EmbeddingUnavailableError(f"Không tạo được mô hình nhúng ({type(exc).__name__}).") from exc


class RuntimeEmbeddingModel(EmbeddingModel):
    """Embedder mặc định của retriever/ingestion: chuyển tới ``EmbeddingRuntime`` và kiểm số chiều."""

    def __init__(self, runtime: EmbeddingRuntime) -> None:
        self.runtime = runtime

    def embed(self, texts: list[str]) -> list[list[float]]:
        model, dimensions = self.runtime._acquire()
        vectors = model.embed(texts)
        reason = None
        if len(vectors) != len(texts):
            reason = f"Mô hình nhúng trả {len(vectors)} vector cho {len(texts)} đoạn văn bản."
        else:
            wrong = next((len(vector) for vector in vectors if len(vector) != dimensions), None)
            if wrong is not None:
                reason = f"Mô hình nhúng trả vector {wrong} chiều nhưng VECTOR_DIM={dimensions}."
        if reason is not None:
            self.runtime.mark_failed(model, reason)
            raise EmbeddingUnavailableError(reason)
        return vectors


embedding_runtime = EmbeddingRuntime()
runtime_embedding_model = RuntimeEmbeddingModel(embedding_runtime)
