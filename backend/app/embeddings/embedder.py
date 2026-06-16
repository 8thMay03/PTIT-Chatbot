from app.core.config import settings
from app.embeddings.models import (
    EmbeddingModel,
    HashEmbeddingModel,
    OpenAIEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)


def create_embedding_model() -> EmbeddingModel:
    provider = settings.embedding_provider.lower()
    if provider == "hash":
        return HashEmbeddingModel()

    if provider == "openai":
        return OpenAIEmbeddingModel(settings.embedding_model, settings.openai_api_key)

    if provider == "sentence-transformers":
        try:
            return SentenceTransformerEmbeddingModel(settings.embedding_model)
        except Exception:
            return HashEmbeddingModel()

    try:
        return SentenceTransformerEmbeddingModel(settings.embedding_model)
    except Exception:
        return HashEmbeddingModel()
