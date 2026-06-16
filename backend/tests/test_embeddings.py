from app.embeddings.models import _normalize_openai_embedding_model


def test_normalize_openai_embedding_model_alias() -> None:
    assert _normalize_openai_embedding_model("text-embedding3") == "text-embedding-3-small"


def test_preserve_exact_openai_embedding_model() -> None:
    assert _normalize_openai_embedding_model("text-embedding-3-large") == "text-embedding-3-large"
