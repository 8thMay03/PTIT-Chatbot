from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.core import user_auth
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


class RetrievalTestRequest(BaseModel):
    query: str
    top_k: int = 10
    similarity_threshold: float | None = None
    vector_similarity_weight: float | None = None
    rerank_model: str | None = None
    use_knowledge_graph: bool = False
    cross_language_search: str | None = None
    meta_data: str | None = None


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    collection: str


class ChunkAllResponse(IngestResponse):
    # Documents without a stored parse result (indexed before parse/chunk were split).
    skipped: int = 0


class DocumentItem(BaseModel):
    id: str
    title: str
    file_name: str
    source_path: str
    file_type: str | None = None
    status: str = "active"
    markdown_edited: bool = False
    parsed_at: datetime | None = None
    chunk_count: int = 0
    size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentDetail(DocumentItem):
    preview: str | None = None
    full_text: str | None = None


class ParseJobItem(BaseModel):
    """Progress and result of a background parse run."""

    id: str
    kind: str
    status: str
    document_id: str | None = None
    file_name: str | None = None
    parser_name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: DocumentItem | None = None
    progress: int = 0
    progress_message: str | None = None


class ParseJobListResponse(BaseModel):
    jobs: list[ParseJobItem]


# Large handbooks parse to a few hundred thousand characters; the cap only rejects abuse.
MAX_MARKDOWN_CHARS = 5_000_000


class DocumentMarkdown(BaseModel):
    document_id: str
    text: str
    content_hash: str
    status: str
    parsed_at: datetime | None = None
    markdown_edited: bool = False


class UpdateMarkdownRequest(BaseModel):
    text: str = Field(max_length=MAX_MARKDOWN_CHARS)
    # content_hash the editor started from; a mismatch means someone else changed it.
    base_hash: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Markdown không được để trống.")
        return value


class ChunkItem(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int | None = None
    chunk_metadata: dict | None = None
    created_at: datetime | None = None


class DocumentChunksResponse(BaseModel):
    total: int
    chunks: list[ChunkItem]


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


class ConfigPersistenceInfo(BaseModel):
    # false: thiếu/sai CONFIG_ENCRYPTION_KEY, PUT /config từ chối mọi thay đổi API key.
    secret_encryption_enabled: bool = False


class FullConfigResponse(BaseModel):
    llm: LLMConfigPayload
    retrieval: RetrievalConfigPayload
    reranker: RerankerConfigPayload
    guardrails: GuardrailsConfigPayload
    embedding: EmbeddingConfigPayload = Field(default_factory=EmbeddingConfigPayload)
    available_providers: AvailableProviders
    persistence: ConfigPersistenceInfo = Field(default_factory=ConfigPersistenceInfo)


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


# ==========================================
# Admin session schemas (FE-06)
# ==========================================
class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class AdminSessionResponse(BaseModel):
    """Trạng thái phiên admin; route session luôn trả 200, không bao giờ 401."""

    authenticated: bool = False
    expires_at: str | None = None
    configured: bool = False


# ==========================================
# User account schemas (landing-user-auth)
# ==========================================
# Lỗi 422 giữ định dạng mặc định FastAPI (detail[].loc/msg); msg tiếng Việt để
# frontend hiện thẳng cạnh ô tương ứng.
def _validate_email(value: str) -> str:
    email = user_auth.normalize_email(value)
    if not user_auth.is_valid_email(email):
        raise PydanticCustomError("email_format", "Email không đúng định dạng.")
    return email


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        name = " ".join(value.split())
        if not name:
            raise PydanticCustomError("full_name_empty", "Vui lòng nhập họ tên.")
        if len(name) > user_auth.FULL_NAME_MAX_LENGTH:
            raise PydanticCustomError(
                "full_name_too_long",
                "Họ tên tối đa {max} ký tự.",
                {"max": user_auth.FULL_NAME_MAX_LENGTH},
            )
        return name

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = _validate_email(value)
        if not user_auth.is_allowed_email_domain(email):
            raise PydanticCustomError(
                "email_domain",
                "Chỉ chấp nhận email thuộc tên miền: {domains}.",
                {"domains": ", ".join(settings.allowed_email_domains)},
            )
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < user_auth.PASSWORD_MIN_LENGTH:
            raise PydanticCustomError(
                "password_too_short",
                "Mật khẩu phải có ít nhất {min} ký tự.",
                {"min": user_auth.PASSWORD_MIN_LENGTH},
            )
        if len(value) > user_auth.PASSWORD_MAX_LENGTH:
            raise PydanticCustomError(
                "password_too_long",
                "Mật khẩu tối đa {max} ký tự.",
                {"max": user_auth.PASSWORD_MAX_LENGTH},
            )
        return value


class LoginRequest(BaseModel):
    email: str = Field(max_length=1024)
    # Không áp quy tắc độ dài của đăng ký: mật khẩu sai độ dài chỉ là sai mật khẩu (401).
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class AuthUser(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime | None = None


class AuthSessionResponse(BaseModel):
    """Trạng thái phiên người dùng; GET /auth/me luôn 200, không bao giờ 401."""

    authenticated: bool = False
    user: AuthUser | None = None
    registration_enabled: bool = True


# ==========================================
# Conversation history schemas
# ==========================================
class ConversationItem(BaseModel):
    id: str
    title: str | None = None
    message_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Owner key (conversations.user_id); chỉ điền ở route admin xem hội thoại.
    owner: str | None = None


class ConversationListResponse(BaseModel):
    total: int
    conversations: list[ConversationItem]


class ConversationMessage(BaseModel):
    id: str
    role: str
    content: str
    sources: list[Source] = Field(default_factory=list)
    # Reasoning/steps được lưu trong metadata lúc sinh câu trả lời; hội thoại
    # cũ (trước khi có trường này) sẽ trả về None/rỗng.
    reasoning: str | None = None
    steps: list[dict] = Field(default_factory=list)
    created_at: datetime | None = None


class ConversationDetail(ConversationItem):
    messages: list[ConversationMessage] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
