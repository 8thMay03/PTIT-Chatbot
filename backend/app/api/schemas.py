from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class Source(BaseModel):
    citation_id: int
    source_name: str
    heading: str | None = None
    section_path: str | None = None
    article: str | None = None
    clauses: list[str] = Field(default_factory=list)
    points: list[str] = Field(default_factory=list)
    locator: str | None = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    user_id: str | None = None
    top_k: int | None = None

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int | None) -> int | None:
        if value is not None:
            max_limit = getattr(settings, "retrieval_max_top_k", 10)
            if value < 1 or value > max_limit:
                raise ValueError(f"top_k must be between 1 and {max_limit}")
        return value

    @property
    def effective_top_k(self) -> int:
        if self.top_k is not None:
            return self.top_k
        return getattr(settings, "retrieval_default_top_k", 4)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    collection: str


class DocumentItem(BaseModel):
    id: str
    title: str
    file_name: str
    source_path: str
    file_type: str | None = None
    status: str = "active"
    chunk_count: int = 0
    size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentDetail(DocumentItem):
    preview: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class DocumentDeleteResponse(BaseModel):
    id: str
    deleted: bool = True


# ==========================================
# Configuration Schemas
# ==========================================

class LLMConfigPayload(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    temperature: float = 0.0
    timeout: float = 30.0
    max_retries: int = 2
    has_api_key: bool = False
    base_url: str | None = None
    openai_model: str | None = None
    openai_has_key: bool = False
    gemini_model: str | None = None
    gemini_has_key: bool = False
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    azure_has_key: bool = False
    openai_compatible_base_url: str | None = None
    openai_compatible_model: str | None = None
    openai_compatible_has_key: bool = False


class RetrievalConfigPayload(BaseModel):
    multi_query_enabled: bool = True
    multi_query_use_llm: bool = False
    multi_query_count: int = 3
    query_rewrite_use_llm: bool = False
    top_k: int = 4
    max_top_k: int = 10
    hybrid_vector_weight: float = 0.65
    hybrid_candidate_multiplier: int = 4
    hybrid_rrf_k: int = 60


class RerankerConfigPayload(BaseModel):
    enabled: bool = True
    provider: str = "heuristic"
    model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    candidate_multiplier: int = 3
    vector_weight: float = 0.45
    bm25_weight: float = 0.35
    lexical_weight: float = 0.20


class GuardrailsConfigPayload(BaseModel):
    scope_enabled: bool = True
    min_vector_score: float = 0.30
    min_bm25_score: float = 2.0


class EmbeddingConfigPayload(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"


class AvailableProviders(BaseModel):
    llm: list[str] = ["openai", "gemini", "azure", "openai_compatible", "anthropic", "deepseek", "cohere", "qwen"]
    embedding: list[str] = ["openai", "sentence-transformers", "cohere", "gemini"]
    reranker: list[str] = ["heuristic", "cross-encoder", "cohere"]


class FullConfigResponse(BaseModel):
    llm: LLMConfigPayload
    retrieval: RetrievalConfigPayload
    reranker: RerankerConfigPayload
    guardrails: GuardrailsConfigPayload
    embedding: EmbeddingConfigPayload = Field(default_factory=EmbeddingConfigPayload)
    available_providers: AvailableProviders


class UpdateLLMConfig(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    timeout: float | None = None
    max_retries: int | None = None
    openai_model: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    gemini_model: str | None = None
    gemini_api_key: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None


class UpdateEmbeddingConfig(BaseModel):
    provider: str | None = None
    model: str | None = None


class UpdateRetrievalConfig(BaseModel):
    multi_query_enabled: bool | None = None
    multi_query_use_llm: bool | None = None
    multi_query_count: int | None = None
    query_rewrite_use_llm: bool | None = None
    top_k: int | None = None
    hybrid_vector_weight: float | None = None


class UpdateRerankerConfig(BaseModel):
    enabled: bool | None = None
    provider: str | None = None
    model: str | None = None
    candidate_multiplier: int | None = None


class UpdateGuardrailsConfig(BaseModel):
    scope_enabled: bool | None = None
    min_vector_score: float | None = None
    min_bm25_score: float | None = None


class UpdateConfigRequest(BaseModel):
    llm: UpdateLLMConfig | None = None
    embedding: UpdateEmbeddingConfig | None = None
    retrieval: UpdateRetrievalConfig | None = None
    reranker: UpdateRerankerConfig | None = None
    guardrails: UpdateGuardrailsConfig | None = None


class TestLLMRequest(BaseModel):
    provider: str
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    endpoint: str | None = None
    deployment_name: str | None = None
    api_version: str | None = None


class TestLLMResponse(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None
    sample_output: str | None = None
