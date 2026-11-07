import logging

from app.core.config import settings
from app.db.models import Chunk
from app.embeddings.models import (
    EmbeddingModel,
    HashEmbeddingModel,
    OpenAIEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)

logger = logging.getLogger(__name__)

# Số chiều cột `chunks.embedding`; VECTOR_DIM và mọi vector ghi vào kho phải khớp.
VECTOR_COLUMN_DIM: int = Chunk.__table__.c.embedding.type.dim


class EmbeddingUnavailableError(RuntimeError):
    """Không dùng được mô hình nhúng.

    ``reason`` hiện cho admin nên chỉ chứa provider/model, loại exception, số chiều —
    không bao giờ kèm chuỗi lỗi thô của SDK (có thể chứa một phần API key).
    """

    state = "error"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EmbeddingNotConfiguredError(EmbeddingUnavailableError):
    """Thiếu cấu hình bắt buộc (ví dụ API key của provider openai)."""

    state = "not_configured"


def create_embedding_model() -> EmbeddingModel:
    """Tạo mô hình nhúng theo settings; không dùng được thì ném lỗi, không quay về Hash."""
    provider = (settings.embedding_provider or "").strip().lower()
    model_name = settings.embedding_model
    dimensions = settings.vector_dim
    if dimensions != VECTOR_COLUMN_DIM:
        raise EmbeddingUnavailableError(
            f"VECTOR_DIM={dimensions} khác số chiều cột vector trong cơ sở dữ liệu ({VECTOR_COLUMN_DIM})."
        )

    if provider == "hash":
        logger.warning("EMBEDDING_PROVIDER=hash: embedding băm chỉ dùng cho test/phát triển.")
        return HashEmbeddingModel(dimensions=dimensions)

    if provider == "openai":
        api_key = settings.embedding_api_key or settings.openai_api_key
        if not api_key:
            raise EmbeddingNotConfiguredError(
                "Chưa có API key cho embedding OpenAI (EMBEDDING_API_KEY hoặc OPENAI_API_KEY)."
            )
        try:
            return OpenAIEmbeddingModel(model_name, api_key)
        except Exception as exc:
            raise EmbeddingUnavailableError(
                f"Không khởi tạo được embedding OpenAI '{model_name}' ({type(exc).__name__})."
            ) from exc

    if provider == "sentence-transformers":
        try:
            model = SentenceTransformerEmbeddingModel(model_name)
        except Exception as exc:
            raise EmbeddingUnavailableError(
                f"Không tải được mô hình sentence-transformers '{model_name}' ({type(exc).__name__})."
            ) from exc
        model_dim = model.dimensions
        if model_dim is not None and model_dim != dimensions:
            raise EmbeddingUnavailableError(
                f"Mô hình '{model_name}' có {model_dim} chiều nhưng VECTOR_DIM={dimensions}."
            )
        return model

    raise EmbeddingUnavailableError(f"Provider embedding '{provider}' chưa được hỗ trợ.")
