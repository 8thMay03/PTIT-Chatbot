from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Settings
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_timeout: float = Field(default=30.0, ge=1.0, alias="LLM_TIMEOUT")
    llm_max_retries: int = Field(default=2, ge=0, alias="LLM_MAX_RETRIES")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0, alias="LLM_TEMPERATURE")

    # OpenAI Settings
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")

    # Google Gemini Settings
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # Azure OpenAI Settings
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment_name: str | None = Field(
        default=None,
        alias="AZURE_OPENAI_DEPLOYMENT_NAME",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        alias="AZURE_OPENAI_API_VERSION",
    )

    # OpenAI Compatible / Local Model Settings
    openai_compatible_base_url: str | None = Field(
        default=None,
        alias="OPENAI_COMPATIBLE_BASE_URL",
    )
    openai_compatible_api_key: str | None = Field(
        default=None,
        alias="OPENAI_COMPATIBLE_API_KEY",
    )
    openai_compatible_model: str = Field(
        default="default",
        alias="OPENAI_COMPATIBLE_MODEL",
    )

    ragas_judge_model: str = Field(default="gpt-4.1-mini", alias="RAGAS_JUDGE_MODEL")
    ragas_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="RAGAS_EMBEDDING_MODEL",
    )

    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )

    vector_dim: int = Field(default=1536, ge=1, alias="VECTOR_DIM")
    database_url: str = Field(
        default="postgresql+psycopg://ptit_user:ptit_password@127.0.0.1:5433/ptit_chatbot",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, ge=1, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, ge=0, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: float = Field(default=30.0, ge=1.0, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, ge=0, alias="DB_POOL_RECYCLE")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    documents_path: Path = Field(default=Path("data"), alias="DOCUMENTS_PATH")
    chunk_size: int = Field(default=900, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, alias="CHUNK_OVERLAP")
    parent_child_chunking_enabled: bool = Field(
        default=True,
        alias="PARENT_CHILD_CHUNKING_ENABLED",
    )
    child_chunk_size: int = Field(default=450, ge=100, alias="CHILD_CHUNK_SIZE")
    child_chunk_overlap: int = Field(default=75, ge=0, alias="CHILD_CHUNK_OVERLAP")
    hybrid_vector_weight: float = Field(default=0.65, ge=0, le=1, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_candidate_multiplier: int = Field(default=4, ge=1, alias="HYBRID_CANDIDATE_MULTIPLIER")
    hybrid_rrf_k: int = Field(default=60, ge=1, alias="HYBRID_RRF_K")
    retrieval_min_vector_score: float = Field(default=0.30, alias="RETRIEVAL_MIN_VECTOR_SCORE")
    retrieval_min_bm25_score: float = Field(default=2.0, ge=0, alias="RETRIEVAL_MIN_BM25_SCORE")
    query_rewrite_use_llm: bool = Field(default=False, alias="QUERY_REWRITE_USE_LLM")
    multi_query_enabled: bool = Field(default=True, alias="MULTI_QUERY_ENABLED")
    multi_query_use_llm: bool = Field(default=False, alias="MULTI_QUERY_USE_LLM")
    multi_query_count: int = Field(default=3, ge=1, le=8, alias="MULTI_QUERY_COUNT")
    conversation_memory_enabled: bool = Field(default=True, alias="CONVERSATION_MEMORY_ENABLED")
    conversation_memory_max_messages: int = Field(
        default=6,
        ge=0,
        alias="CONVERSATION_MEMORY_MAX_MESSAGES",
    )
    conversation_memory_max_chars: int = Field(
        default=6000,
        ge=0,
        alias="CONVERSATION_MEMORY_MAX_CHARS",
    )
    reranker_enabled: bool = Field(default=True, alias="RERANKER_ENABLED")
    reranker_provider: str = Field(default="heuristic", alias="RERANKER_PROVIDER")
    reranker_model: str = Field(
        default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        alias="RERANKER_MODEL",
    )
    reranker_candidate_multiplier: int = Field(default=3, ge=1, alias="RERANKER_CANDIDATE_MULTIPLIER")
    reranker_vector_weight: float = Field(default=0.45, ge=0, alias="RERANKER_VECTOR_WEIGHT")
    reranker_bm25_weight: float = Field(default=0.35, ge=0, alias="RERANKER_BM25_WEIGHT")
    reranker_lexical_weight: float = Field(default=0.20, ge=0, alias="RERANKER_LEXICAL_WEIGHT")
    retrieval_default_top_k: int = Field(default=4, ge=1, le=20, alias="RETRIEVAL_DEFAULT_TOP_K")
    retrieval_max_top_k: int = Field(default=10, ge=1, le=50, alias="RETRIEVAL_MAX_TOP_K")
    guardrail_scope_enabled: bool = Field(default=True, alias="GUARDRAIL_SCOPE_ENABLED")
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    def model_post_init(self, __context: object) -> None:
        self.documents_path = _resolve_project_path(self.documents_path)
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            self.database_url = "postgresql+psycopg://" + url.removeprefix("postgres://")
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            self.database_url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        else:
            self.database_url = url

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.database_url

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def database_path(self) -> Path:
        return PROJECT_ROOT / "backend/storage"



def _resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Snapshot initial defaults for reset capability
_INITIAL_SETTINGS = settings.model_dump()


def _mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    cleaned = key.strip()
    if len(cleaned) <= 8:
        return "••••••••"
    return f"{cleaned[:3]}••••••••{cleaned[-4:]}"


def get_runtime_config_dict() -> dict:
    """Return a comprehensive runtime configuration dictionary with masked API keys."""
    provider = settings.llm_provider.lower()
    
    has_active_key = False
    active_model = settings.openai_model
    active_base_url = settings.openai_base_url

    if provider in ("openai",):
        has_active_key = bool(settings.openai_api_key)
        active_model = settings.openai_model
        active_base_url = settings.openai_base_url
    elif provider in ("gemini", "google"):
        has_active_key = bool(settings.gemini_api_key)
        active_model = settings.gemini_model
        active_base_url = None
    elif provider in ("azure", "azure_openai"):
        has_active_key = bool(settings.azure_openai_api_key)
        active_model = settings.azure_openai_deployment_name or "azure-default"
        active_base_url = settings.azure_openai_endpoint
    elif provider in ("openai_compatible", "local", "ollama", "vllm"):
        has_active_key = bool(settings.openai_compatible_api_key) or True  # local often no key needed
        active_model = settings.openai_compatible_model
        active_base_url = settings.openai_compatible_base_url

    return {
        "llm": {
            "provider": settings.llm_provider,
            "model": active_model,
            "temperature": settings.llm_temperature,
            "timeout": settings.llm_timeout,
            "max_retries": settings.llm_max_retries,
            "has_api_key": has_active_key,
            "base_url": active_base_url,
            "openai_model": settings.openai_model,
            "openai_has_key": bool(settings.openai_api_key),
            "gemini_model": settings.gemini_model,
            "gemini_has_key": bool(settings.gemini_api_key),
            "azure_openai_endpoint": settings.azure_openai_endpoint,
            "azure_openai_deployment_name": settings.azure_openai_deployment_name,
            "azure_openai_api_version": settings.azure_openai_api_version,
            "azure_has_key": bool(settings.azure_openai_api_key),
            "openai_compatible_base_url": settings.openai_compatible_base_url,
            "openai_compatible_model": settings.openai_compatible_model,
            "openai_compatible_has_key": bool(settings.openai_compatible_api_key),
        },
        "retrieval": {
            "multi_query_enabled": settings.multi_query_enabled,
            "multi_query_use_llm": settings.multi_query_use_llm,
            "multi_query_count": settings.multi_query_count,
            "query_rewrite_use_llm": settings.query_rewrite_use_llm,
            "top_k": settings.retrieval_default_top_k,
            "max_top_k": settings.retrieval_max_top_k,
            "hybrid_vector_weight": settings.hybrid_vector_weight,
            "hybrid_candidate_multiplier": settings.hybrid_candidate_multiplier,
            "hybrid_rrf_k": settings.hybrid_rrf_k,
        },
        "reranker": {
            "enabled": settings.reranker_enabled,
            "provider": settings.reranker_provider,
            "model": settings.reranker_model,
            "candidate_multiplier": settings.reranker_candidate_multiplier,
            "vector_weight": settings.reranker_vector_weight,
            "bm25_weight": settings.reranker_bm25_weight,
            "lexical_weight": settings.reranker_lexical_weight,
        },
        "guardrails": {
            "scope_enabled": settings.guardrail_scope_enabled,
            "min_vector_score": settings.retrieval_min_vector_score,
            "min_bm25_score": settings.retrieval_min_bm25_score,
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
        },
        "available_providers": {
            "llm": ["openai", "gemini", "azure", "openai_compatible", "anthropic", "deepseek", "cohere", "qwen"],
            "embedding": ["openai", "sentence-transformers", "cohere", "gemini"],
            "reranker": ["heuristic", "cross-encoder", "cohere"],
        },
    }


def update_runtime_config(payload: dict) -> dict:
    """Update runtime settings in-memory and return refreshed config dict."""
    llm = payload.get("llm") or {}
    if "provider" in llm and llm["provider"]:
        settings.llm_provider = str(llm["provider"]).strip().lower()
    if "temperature" in llm and llm["temperature"] is not None:
        settings.llm_temperature = max(0.0, min(2.0, float(llm["temperature"])))
    if "timeout" in llm and llm["timeout"] is not None:
        settings.llm_timeout = max(1.0, float(llm["timeout"]))
    if "max_retries" in llm and llm["max_retries"] is not None:
        settings.llm_max_retries = max(0, int(llm["max_retries"]))

    # Specific LLM Provider fields
    if "openai_model" in llm and llm["openai_model"]:
        settings.openai_model = str(llm["openai_model"]).strip()
    if "openai_api_key" in llm and llm["openai_api_key"] is not None and llm["openai_api_key"] != "":
        settings.openai_api_key = str(llm["openai_api_key"]).strip()
    if "openai_base_url" in llm:
        settings.openai_base_url = str(llm["openai_base_url"]).strip() if llm["openai_base_url"] else None

    if "gemini_model" in llm and llm["gemini_model"]:
        settings.gemini_model = str(llm["gemini_model"]).strip()
    if "gemini_api_key" in llm and llm["gemini_api_key"] is not None and llm["gemini_api_key"] != "":
        settings.gemini_api_key = str(llm["gemini_api_key"]).strip()

    if "azure_openai_api_key" in llm and llm["azure_openai_api_key"] is not None and llm["azure_openai_api_key"] != "":
        settings.azure_openai_api_key = str(llm["azure_openai_api_key"]).strip()
    if "azure_openai_endpoint" in llm and llm["azure_openai_endpoint"]:
        settings.azure_openai_endpoint = str(llm["azure_openai_endpoint"]).strip()
    if "azure_openai_deployment_name" in llm and llm["azure_openai_deployment_name"]:
        settings.azure_openai_deployment_name = str(llm["azure_openai_deployment_name"]).strip()
    if "azure_openai_api_version" in llm and llm["azure_openai_api_version"]:
        settings.azure_openai_api_version = str(llm["azure_openai_api_version"]).strip()

    if "openai_compatible_base_url" in llm and llm["openai_compatible_base_url"]:
        settings.openai_compatible_base_url = str(llm["openai_compatible_base_url"]).strip()
    if "openai_compatible_api_key" in llm and llm["openai_compatible_api_key"] is not None:
        settings.openai_compatible_api_key = str(llm["openai_compatible_api_key"]).strip() or None
    if "openai_compatible_model" in llm and llm["openai_compatible_model"]:
        settings.openai_compatible_model = str(llm["openai_compatible_model"]).strip()

    # Generic api_key / base_url / model field mapping to current active provider
    if "base_url" in llm and llm["base_url"]:
        b_val = str(llm["base_url"]).strip()
        curr_provider = settings.llm_provider.lower()
        if curr_provider in ("openai",):
            settings.openai_base_url = b_val
        elif curr_provider in ("openai_compatible", "local", "ollama", "vllm", "deepseek", "moonshot", "tongyi", "qwen", "zhipu", "xai"):
            settings.openai_compatible_base_url = b_val

    if "api_key" in llm and llm["api_key"] is not None and llm["api_key"] != "":
        key_val = str(llm["api_key"]).strip()
        curr_provider = settings.llm_provider.lower()
        if curr_provider in ("openai",):
            settings.openai_api_key = key_val
        elif curr_provider in ("gemini", "google"):
            settings.gemini_api_key = key_val
        elif curr_provider in ("azure", "azure_openai"):
            settings.azure_openai_api_key = key_val
        elif curr_provider in ("openai_compatible", "local", "ollama", "vllm", "deepseek", "moonshot", "tongyi", "qwen", "zhipu", "xai"):
            settings.openai_compatible_api_key = key_val

    if "model" in llm and llm["model"]:
        model_val = str(llm["model"]).strip()
        curr_provider = settings.llm_provider.lower()
        if curr_provider in ("openai",):
            settings.openai_model = model_val
        elif curr_provider in ("gemini", "google"):
            settings.gemini_model = model_val
        elif curr_provider in ("azure", "azure_openai"):
            settings.azure_openai_deployment_name = model_val
        elif curr_provider in ("openai_compatible", "local", "ollama", "vllm", "deepseek", "moonshot", "tongyi", "qwen", "zhipu", "xai"):
            settings.openai_compatible_model = model_val

    # Retrieval
    retrieval = payload.get("retrieval") or {}
    if "multi_query_enabled" in retrieval and retrieval["multi_query_enabled"] is not None:
        settings.multi_query_enabled = bool(retrieval["multi_query_enabled"])
    if "multi_query_use_llm" in retrieval and retrieval["multi_query_use_llm"] is not None:
        settings.multi_query_use_llm = bool(retrieval["multi_query_use_llm"])
    if "multi_query_count" in retrieval and retrieval["multi_query_count"] is not None:
        settings.multi_query_count = max(1, min(8, int(retrieval["multi_query_count"])))
    if "query_rewrite_use_llm" in retrieval and retrieval["query_rewrite_use_llm"] is not None:
        settings.query_rewrite_use_llm = bool(retrieval["query_rewrite_use_llm"])
    if "top_k" in retrieval and retrieval["top_k"] is not None:
        settings.retrieval_default_top_k = max(1, min(20, int(retrieval["top_k"])))
    if "hybrid_vector_weight" in retrieval and retrieval["hybrid_vector_weight"] is not None:
        settings.hybrid_vector_weight = max(0.0, min(1.0, float(retrieval["hybrid_vector_weight"])))

    # Embedding
    embedding = payload.get("embedding") or {}
    if "provider" in embedding and embedding["provider"]:
        settings.embedding_provider = str(embedding["provider"]).strip().lower()
    if "model" in embedding and embedding["model"]:
        settings.embedding_model = str(embedding["model"]).strip()

    # Reranker
    reranker = payload.get("reranker") or {}
    if "enabled" in reranker and reranker["enabled"] is not None:
        settings.reranker_enabled = bool(reranker["enabled"])
    if "provider" in reranker and reranker["provider"]:
        settings.reranker_provider = str(reranker["provider"]).strip().lower()
    if "model" in reranker and reranker["model"]:
        settings.reranker_model = str(reranker["model"]).strip()
    if "candidate_multiplier" in reranker and reranker["candidate_multiplier"] is not None:
        settings.reranker_candidate_multiplier = max(1, min(8, int(reranker["candidate_multiplier"])))

    # Guardrails
    guardrails = payload.get("guardrails") or {}
    if "scope_enabled" in guardrails and guardrails["scope_enabled"] is not None:
        settings.guardrail_scope_enabled = bool(guardrails["scope_enabled"])
    if "min_vector_score" in guardrails and guardrails["min_vector_score"] is not None:
        settings.retrieval_min_vector_score = float(guardrails["min_vector_score"])
    if "min_bm25_score" in guardrails and guardrails["min_bm25_score"] is not None:
        settings.retrieval_min_bm25_score = float(guardrails["min_bm25_score"])

    return get_runtime_config_dict()


def reset_runtime_config() -> dict:
    """Reset runtime configuration back to fresh default settings."""
    fresh = Settings()
    for field_name in Settings.model_fields.keys():
        if hasattr(settings, field_name) and hasattr(fresh, field_name):
            setattr(settings, field_name, getattr(fresh, field_name))
    return get_runtime_config_dict()
