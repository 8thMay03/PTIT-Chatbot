from __future__ import annotations

import hashlib
import math


class EmbeddingModel:
    # True: câu hỏi được nhúng khác đoạn tài liệu (``embed_query`` khác ``embed``).
    distinguishes_queries: bool = False

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Nhúng đoạn tài liệu (khi nạp tài liệu)."""
        raise NotImplementedError

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        """Nhúng câu hỏi khi tìm kiếm; mặc định giống ``embed``."""
        return self.embed(texts)


class HashEmbeddingModel(EmbeddingModel):
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


# Số chiều mặc định của mô hình OpenAI nhận tham số `dimensions`.
_OPENAI_DEFAULT_DIMENSIONS = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}


class OpenAIEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str, api_key: str | None, dimensions: int | None = None) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")

        from openai import OpenAI

        self.model_name = _normalize_openai_embedding_model(model_name)
        self.client = OpenAI(api_key=api_key)
        # Chỉ gửi `dimensions` khi khác mặc định, để request với số chiều mặc định giữ nguyên như cũ.
        default = _OPENAI_DEFAULT_DIMENSIONS.get(self.model_name)
        self.request_dimensions = dimensions if default is not None and dimensions not in (None, default) else None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        batch_size = 500
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            extra = {"dimensions": self.request_dimensions} if self.request_dimensions else {}
            response = self.client.embeddings.create(
                input=batch,
                model=self.model_name,
                **extra,
            )
            batch_embeddings = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
            all_embeddings.extend(batch_embeddings)
        return all_embeddings


class SentenceTransformerEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.dimensions: int | None = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]


class PaddedEmbeddingModel(EmbeddingModel):
    """Đệm số 0 vào cuối vector ``dimensions`` chiều cho đủ ``target_dimensions`` (D-02).

    Cột vector dùng khoảng cách cosine; đệm 0 không đổi tích vô hướng và độ dài nên kết
    quả tìm kiếm giống vector gốc. Vector khác ``dimensions`` chiều được trả nguyên để bên
    gọi (``RuntimeEmbeddingModel``) phát hiện mô hình trả sai số chiều.
    """

    def __init__(self, inner: EmbeddingModel, dimensions: int, target_dimensions: int) -> None:
        self.inner = inner
        self.dimensions = dimensions
        self.target_dimensions = target_dimensions
        self.model_name = getattr(inner, "model_name", None)
        self.distinguishes_queries = inner.distinguishes_queries

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._pad(self.inner.embed(texts))

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return self._pad(self.inner.embed_query(texts))

    def _pad(self, vectors: list[list[float]]) -> list[list[float]]:
        padding = [0.0] * (self.target_dimensions - self.dimensions)
        return [list(vector) + padding if len(vector) == self.dimensions else vector for vector in vectors]


def _normalize_openai_embedding_model(model_name: str) -> str:
    aliases = {
        "text-embedding3": "text-embedding-3-small",
        "text-embedding-3": "text-embedding-3-small",
        "embedding-3": "text-embedding-3-small",
    }
    return aliases.get(model_name.strip().lower(), model_name)
