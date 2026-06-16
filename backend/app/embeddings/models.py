from __future__ import annotations

import hashlib
import math


class EmbeddingModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


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


class OpenAIEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str, api_key: str | None) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")

        from openai import OpenAI

        self.model_name = _normalize_openai_embedding_model(model_name)
        self.client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name,
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


class SentenceTransformerEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]


def _normalize_openai_embedding_model(model_name: str) -> str:
    aliases = {
        "text-embedding3": "text-embedding-3-small",
        "text-embedding-3": "text-embedding-3-small",
        "embedding-3": "text-embedding-3-small",
    }
    return aliases.get(model_name.strip().lower(), model_name)
