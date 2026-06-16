from app.core.config import settings
from app.embeddings.models import (
    EmbeddingModel,
    HashEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)


def create_embedding_model() -> EmbeddingModel:
    if settings.embedding_provider == "hash":
        return HashEmbeddingModel()

    try:
        return SentenceTransformerEmbeddingModel(settings.embedding_model)
    except Exception:
        return HashEmbeddingModel()
