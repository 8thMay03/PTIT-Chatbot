import logging

from app.core.config import settings
from app.db.models import Chunk
from app.embeddings.api_clients import API_PROVIDERS, ApiEmbeddingModel
from app.embeddings.errors import EmbeddingNotConfiguredError, EmbeddingUnavailableError
from app.embeddings.models import (
    EmbeddingModel,
    HashEmbeddingModel,
    OpenAIEmbeddingModel,
    PaddedEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)

logger = logging.getLogger(__name__)

# Số chiều cột `chunks.embedding`; VECTOR_DIM và mọi vector ghi vào kho phải khớp.
VECTOR_COLUMN_DIM: int = Chunk.__table__.c.embedding.type.dim

__all__ = [
    "VECTOR_COLUMN_DIM",
    "EmbeddingNotConfiguredError",
    "EmbeddingUnavailableError",
    "create_embedding_model",
    "embedding_signature",
    "model_dimensions",
]


def model_dimensions() -> int:
    """Số chiều mô hình nhúng trả về: ``EMBEDDING_DIMENSION``, trống thì ``VECTOR_DIM``."""
    return settings.embedding_dimension or settings.vector_dim


def embedding_signature() -> str:
    """Chữ ký không gian vector của cấu hình embedding hiện tại: ``provider:model:số chiều``.

    Base URL chỉ có nghĩa với ``openai_compatible`` (máy chủ khác có thể phục vụ mô hình khác
    cùng tên) nên được nối thêm ``@base_url``. Khoá API không đổi không gian vector nên không
    nằm trong chữ ký.
    """
    provider = (settings.embedding_provider or "").strip().lower()
    signature = f"{provider}:{(settings.embedding_model or '').strip()}:{model_dimensions()}"
    base_url = (settings.embedding_base_url or "").strip().rstrip("/")
    if provider == "openai_compatible" and base_url:
        signature = f"{signature}@{base_url}"
    return signature


def create_embedding_model() -> EmbeddingModel:
    """Tạo mô hình nhúng theo settings; không dùng được thì ném lỗi, không quay về Hash.

    Mô hình ít chiều hơn ``VECTOR_DIM`` được bọc ``PaddedEmbeddingModel`` (đệm 0, D-02) để
    mọi vector trả về đều có ``VECTOR_DIM`` chiều.
    """
    vector_dim = settings.vector_dim
    if vector_dim != VECTOR_COLUMN_DIM:
        raise EmbeddingUnavailableError(
            f"VECTOR_DIM={vector_dim} khác số chiều cột vector trong cơ sở dữ liệu ({VECTOR_COLUMN_DIM})."
        )
    dimensions = model_dimensions()
    if dimensions > vector_dim:
        raise EmbeddingUnavailableError(
            f"Mô hình nhúng có {dimensions} chiều, nhiều hơn VECTOR_DIM={vector_dim} của kho vector."
        )
    model = _create_model(dimensions)
    if dimensions < vector_dim:
        return PaddedEmbeddingModel(model, dimensions, vector_dim)
    return model


def _create_model(dimensions: int) -> EmbeddingModel:
    provider = (settings.embedding_provider or "").strip().lower()
    model_name = settings.embedding_model

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
            return OpenAIEmbeddingModel(model_name, api_key, dimensions=dimensions)
        except Exception as exc:
            raise EmbeddingUnavailableError(
                f"Không khởi tạo được embedding OpenAI '{model_name}' ({type(exc).__name__})."
            ) from exc

    if provider in API_PROVIDERS:
        # Không dự phòng khoá `.env` khác (D-04): chỉ EMBEDDING_API_KEY hoặc khoá của profile.
        return ApiEmbeddingModel(
            provider,
            model_name,
            settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            dimensions=dimensions,
        )

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
                f"Mô hình '{model_name}' có {model_dim} chiều nhưng cấu hình là {dimensions} chiều "
                f"(EMBEDDING_DIMENSION, mặc định VECTOR_DIM={settings.vector_dim})."
            )
        return model

    raise EmbeddingUnavailableError(f"Provider embedding '{provider}' chưa được hỗ trợ.")
