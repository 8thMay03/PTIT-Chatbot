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

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )

    vector_db_path: Path = Field(default=Path("backend/storage/chroma"), alias="VECTOR_DB_PATH")
    database_url: str = Field(
        default="sqlite:///backend/storage/ptit_chatbot.db",
        alias="DATABASE_URL",
    )
    documents_path: Path = Field(default=Path("data"), alias="DOCUMENTS_PATH")
    chunk_size: int = Field(default=900, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, alias="CHUNK_OVERLAP")
    hybrid_vector_weight: float = Field(default=0.65, ge=0, le=1, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_candidate_multiplier: int = Field(default=4, ge=1, alias="HYBRID_CANDIDATE_MULTIPLIER")
    hybrid_rrf_k: int = Field(default=60, ge=1, alias="HYBRID_RRF_K")
    retrieval_min_vector_score: float = Field(default=0.30, alias="RETRIEVAL_MIN_VECTOR_SCORE")
    retrieval_min_bm25_score: float = Field(default=2.0, ge=0, alias="RETRIEVAL_MIN_BM25_SCORE")
    query_rewrite_use_llm: bool = Field(default=False, alias="QUERY_REWRITE_USE_LLM")
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
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    def model_post_init(self, __context: object) -> None:
        self.vector_db_path = _resolve_project_path(self.vector_db_path)
        self.documents_path = _resolve_project_path(self.documents_path)
        if self.database_url.startswith("sqlite:///"):
            database_path = _resolve_project_path(Path(self.database_url.removeprefix("sqlite:///")))
            self.database_url = f"sqlite:///{database_path.as_posix()}"

    @property
    def database_path(self) -> Path:
        if not self.database_url.startswith("sqlite:///"):
            return PROJECT_ROOT / "backend/storage"
        return Path(self.database_url.removeprefix("sqlite:///"))


def _resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
