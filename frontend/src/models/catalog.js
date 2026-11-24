/*
 * Định nghĩa ba loại mô hình trong kho (LLM, embedding, reranker): nhà cung cấp, trường
 * nhập của từng nhà cung cấp, kiểm tra và payload gửi /api/model-profiles.
 *
 * Chỉ gồm nhà cung cấp backend thật sự chạy được (app/core/model_profiles.py).
 * Tên trường trong bản nháp trùng tên trường của API để không phải ánh xạ.
 */

export const URL_PATTERN = /^https?:\/\/\S+$/i;

const FIELD_NAMES = ["model", "base_url", "endpoint", "deployment_name", "api_version", "dimension"];

export const LLM_PROVIDERS = [
  { key: "openai", name: "OpenAI" },
  { key: "gemini", name: "Google Gemini" },
  { key: "azure", name: "Azure OpenAI" },
  { key: "openai_compatible", name: "Tương thích OpenAI" },
];

export const EMBEDDING_PROVIDERS = [
  { key: "openai", name: "OpenAI" },
  { key: "sentence-transformers", name: "Sentence-Transformers" },
  { key: "voyage", name: "Voyage AI" },
  { key: "cohere", name: "Cohere" },
  { key: "gemini", name: "Google Gemini" },
  { key: "jina", name: "Jina AI" },
  { key: "openai_compatible", name: "Tương thích OpenAI" },
];

export const RERANKER_PROVIDERS = [
  { key: "cross-encoder", name: "Cross-Encoder" },
  { key: "cohere", name: "Cohere" },
  { key: "jina", name: "Jina AI" },
  { key: "voyage", name: "Voyage AI" },
  { key: "pinecone", name: "Pinecone" },
  { key: "tei", name: "HF TEI" },
  { key: "rerank_api", name: "Rerank API" },
];

/** Reranker gọi dịch vụ ngoài (khớp `API_RERANK_PROVIDERS` ở backend). */
export const API_RERANKER_PROVIDERS = ["cohere", "jina", "voyage", "pinecone", "tei", "rerank_api"];
const RERANKER_BASE_URL_PROVIDERS = ["tei", "rerank_api"];

export const COMPATIBLE_PRESETS = [
  { key: "ollama", label: "Ollama", baseUrl: "http://localhost:11434/v1", model: "qwen2.5:7b" },
  { key: "vllm", label: "vLLM", baseUrl: "http://localhost:8000/v1", model: "" },
  { key: "deepseek", label: "DeepSeek", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  {
    key: "qwen",
    label: "Qwen (DashScope)",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: "qwen-plus",
  },
];

/** Điền nhanh máy chủ embedding tương thích OpenAI (Base URL tới trước /embeddings). */
export const EMBEDDING_COMPATIBLE_PRESETS = [
  { key: "ollama", label: "Ollama", baseUrl: "http://localhost:11434/v1", model: "bge-m3" },
  { key: "vllm", label: "vLLM", baseUrl: "http://localhost:8000/v1", model: "" },
  { key: "tei", label: "HF TEI", baseUrl: "http://localhost:8080/v1", model: "" },
  { key: "mistral", label: "Mistral", baseUrl: "https://api.mistral.ai/v1", model: "mistral-embed" },
];

/** Nút điền nhanh của nhà cung cấp tương thích OpenAI theo loại mô hình. */
export function compatiblePresets(kind) {
  return kind === "embedding" ? EMBEDDING_COMPATIBLE_PRESETS : COMPATIBLE_PRESETS;
}

// Số chiều của các mô hình nhúng phổ biến: chọn mô hình thì tự điền số chiều. Mô hình đổi
// được số chiều (Voyage, Cohere v4, Gemini, Jina v3) điền số vừa với VECTOR_DIM 1536.
export const KNOWN_EMBEDDING_DIMENSIONS = {
  "text-embedding-3-small": 1536,
  "text-embedding-3-large": 3072,
  "text-embedding-ada-002": 1536,
  "BAAI/bge-m3": 1024,
  "intfloat/multilingual-e5-base": 768,
  "intfloat/multilingual-e5-large": 1024,
  "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
  "voyage-3.5": 1024,
  "voyage-3.5-lite": 1024,
  "voyage-3-large": 1024,
  "voyage-multilingual-2": 1024,
  "embed-v4.0": 1536,
  "embed-multilingual-v3.0": 1024,
  "embed-multilingual-light-v3.0": 384,
  "gemini-embedding-001": 1536,
  "text-embedding-004": 768,
  "jina-embeddings-v3": 1024,
  "mistral-embed": 1024,
  "bge-m3": 1024,
  "nomic-embed-text": 768,
};

const DIMENSION_FIELD = { name: "dimension", label: "Số chiều vector", required: true, number: true };

const MODEL_FIELD = { name: "model", label: "Mô hình", required: true };

/** Trường của từng (loại, nhà cung cấp) — khớp `_PROVIDER_FIELDS` ở backend. */
const FIELDS = {
  llm: {
    openai: [
      {
        ...MODEL_FIELD,
        placeholder: "gpt-4.1-mini",
        suggestions: ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
      },
      { name: "base_url", label: "Base URL", url: true, placeholder: "https://api.openai.com/v1" },
    ],
    gemini: [
      {
        ...MODEL_FIELD,
        placeholder: "gemini-2.0-flash",
        suggestions: ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
      },
    ],
    azure: [
      {
        name: "endpoint",
        label: "Endpoint",
        required: true,
        url: true,
        placeholder: "https://<tên-tài-nguyên>.openai.azure.com",
      },
      {
        name: "deployment_name",
        label: "Tên deployment",
        required: true,
        placeholder: "gpt-4o-mini",
        hint: "Tên deployment đã tạo trên Azure, không phải tên mô hình gốc.",
      },
      { name: "api_version", label: "API version", required: true, placeholder: "2024-02-15-preview" },
    ],
    openai_compatible: [
      { name: "base_url", label: "Base URL", required: true, url: true, placeholder: "http://localhost:11434/v1" },
      { ...MODEL_FIELD, placeholder: "qwen2.5:7b" },
    ],
  },
  embedding: {
    openai: [
      {
        ...MODEL_FIELD,
        placeholder: "text-embedding-3-small",
        suggestions: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
      },
      { ...DIMENSION_FIELD, placeholder: "1536" },
    ],
    "sentence-transformers": [
      {
        ...MODEL_FIELD,
        placeholder: "BAAI/bge-m3",
        suggestions: [
          "BAAI/bge-m3",
          "intfloat/multilingual-e5-base",
          "intfloat/multilingual-e5-large",
          "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
      },
      { ...DIMENSION_FIELD, placeholder: "1024" },
    ],
    voyage: [
      {
        ...MODEL_FIELD,
        placeholder: "voyage-3.5",
        suggestions: ["voyage-3.5", "voyage-3.5-lite", "voyage-3-large", "voyage-multilingual-2"],
      },
      { ...DIMENSION_FIELD, placeholder: "1024" },
    ],
    cohere: [
      {
        ...MODEL_FIELD,
        placeholder: "embed-v4.0",
        suggestions: ["embed-v4.0", "embed-multilingual-v3.0", "embed-multilingual-light-v3.0"],
      },
      { ...DIMENSION_FIELD, placeholder: "1536" },
    ],
    gemini: [
      {
        ...MODEL_FIELD,
        placeholder: "gemini-embedding-001",
        suggestions: ["gemini-embedding-001", "text-embedding-004"],
      },
      { ...DIMENSION_FIELD, placeholder: "1536" },
    ],
    jina: [
      {
        ...MODEL_FIELD,
        placeholder: "jina-embeddings-v3",
        suggestions: ["jina-embeddings-v3"],
      },
      { ...DIMENSION_FIELD, placeholder: "1024" },
    ],
    openai_compatible: [
      { name: "base_url", label: "Base URL", required: true, url: true, placeholder: "http://localhost:11434/v1" },
      { ...MODEL_FIELD, placeholder: "bge-m3", suggestions: ["bge-m3", "nomic-embed-text", "mistral-embed"] },
      { ...DIMENSION_FIELD, placeholder: "1024" },
    ],
  },
  reranker: {
    "cross-encoder": [
      {
        ...MODEL_FIELD,
        label: "Mô hình cross-encoder",
        placeholder: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        suggestions: [
          "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
          "BAAI/bge-reranker-base",
          "BAAI/bge-reranker-v2-m3",
        ],
      },
    ],
    rerank_api: [
      { name: "base_url", label: "Base URL", required: true, url: true, placeholder: "https://api.cohere.com/v2" },
      {
        ...MODEL_FIELD,
        placeholder: "rerank-v3.5",
        suggestions: ["rerank-v3.5", "rerank-multilingual-v3.0", "jina-reranker-v2-base-multilingual", "BAAI/bge-reranker-v2-m3"],
      },
    ],
    cohere: [
      {
        ...MODEL_FIELD,
        placeholder: "rerank-v3.5",
        suggestions: ["rerank-v3.5", "rerank-v4.0-pro", "rerank-v4.0-fast", "rerank-multilingual-v3.0"],
      },
    ],
    jina: [
      {
        ...MODEL_FIELD,
        placeholder: "jina-reranker-v3",
        suggestions: ["jina-reranker-v3", "jina-reranker-v2-base-multilingual"],
      },
    ],
    voyage: [
      {
        ...MODEL_FIELD,
        placeholder: "rerank-2.5",
        suggestions: ["rerank-2.5", "rerank-2.5-lite"],
      },
    ],
    pinecone: [
      {
        ...MODEL_FIELD,
        placeholder: "bge-reranker-v2-m3",
        suggestions: ["bge-reranker-v2-m3", "cohere-rerank-4-fast"],
        hint: "bge-reranker-v2-m3 nhận tối đa 100 đoạn mỗi lần (Top-K × hệ số ứng viên).",
      },
    ],
    tei: [
      { name: "base_url", label: "Base URL", required: true, url: true, placeholder: "http://localhost:8080" },
      {
        ...MODEL_FIELD,
        placeholder: "BAAI/bge-reranker-v2-m3",
        suggestions: ["BAAI/bge-reranker-v2-m3", "BAAI/bge-reranker-base", "Alibaba-NLP/gte-multilingual-reranker-base"],
        hint: "TEI mặc định nhận tối đa 32 đoạn mỗi lần (--max-client-batch-size).",
      },
    ],
  },
};

/**
 * Khoá API: `required` = phải có khoá đã lưu hoặc nhập mới (máy chủ từ chối nếu thiếu);
 * `envFallback` = để trống thì máy chủ dùng khoá trong `.env`.
 */
const KEY_RULES = {
  llm: {
    openai: { envFallback: true },
    gemini: { envFallback: true },
    azure: { envFallback: true },
    openai_compatible: { envFallback: false },
  },
  embedding: {
    openai: { envFallback: true },
    voyage: { envFallback: false, required: true },
    cohere: { envFallback: false, required: true },
    gemini: { envFallback: false, required: true },
    jina: { envFallback: false, required: true },
    openai_compatible: { envFallback: false },
  },
  reranker: {
    cohere: { envFallback: false, required: true },
    jina: { envFallback: false, required: true },
    voyage: { envFallback: false, required: true },
    pinecone: { envFallback: false, required: true },
    tei: { envFallback: false },
    rerank_api: { envFallback: false },
  },
};

/** Nhà cung cấp có nút "Kiểm tra kết nối" trong hộp thoại thêm/sửa. */
export function canTestConnection(kind, provider) {
  if (kind === "embedding") return provider !== "sentence-transformers";
  return kind === "llm" || (kind === "reranker" && API_RERANKER_PROVIDERS.includes(provider));
}

/**
 * Nhà cung cấp lấy được danh sách mô hình (khớp `SUPPORTED` trong app/core/provider_models.py).
 * Giá trị: Base URL `"required"`, `"optional"`, hoặc `null` = URL cố định của hãng.
 */
const MODEL_LIST_BASE_URL = {
  llm: { openai: "optional", gemini: null, openai_compatible: "required" },
  embedding: { openai: null, gemini: null, cohere: null, openai_compatible: "required" },
  reranker: { cohere: null, pinecone: null, tei: "required", rerank_api: "required" },
};

/** Ô "Mô hình" có nút "Tải danh sách" lấy mô hình khả dụng từ nhà cung cấp. */
export function canListModels(kind, provider) {
  return Object.hasOwn(MODEL_LIST_BASE_URL[kind] ?? {}, provider);
}

/** Lý do chưa lấy được danh sách (thiếu/sai Base URL, thiếu khoá bắt buộc); `null` = gọi được. */
export function listModelsBlocker(kind, draft, { hasStoredKey = false } = {}) {
  const mode = MODEL_LIST_BASE_URL[kind]?.[draft.provider];
  const baseUrl = String(draft.base_url ?? "").trim();
  if (mode === "required" && !baseUrl) return "Nhập Base URL trước.";
  if (mode && baseUrl && !URL_PATTERN.test(baseUrl)) return "Base URL phải bắt đầu bằng http:// hoặc https://.";
  const keepsStoredKey = hasStoredKey && !draft.clearApiKey;
  if (keyRule(kind, draft.provider)?.required && !draft.apiKey.trim() && !keepsStoredKey) {
    return "Nhập API key trước.";
  }
  return null;
}

/** Các giá trị quyết định danh sách: đổi bất kỳ giá trị nào thì danh sách cũ không còn đúng. */
export function modelListSignature(kind, draft) {
  const mode = MODEL_LIST_BASE_URL[kind]?.[draft.provider];
  const baseUrl = mode ? String(draft.base_url ?? "").trim() : "";
  return JSON.stringify([kind, draft.provider, baseUrl, draft.apiKey.trim(), Boolean(draft.clearApiKey)]);
}

/** Payload POST /model-profiles/list-models: không nhập khoá thì máy chủ dùng khoá đã lưu của profile. */
export function buildListModelsPayload(kind, draft, profileId) {
  const trimmed = (value) => String(value ?? "").trim() || null;
  return {
    kind,
    provider: draft.provider,
    base_url: MODEL_LIST_BASE_URL[kind]?.[draft.provider] ? trimmed(draft.base_url) : null,
    api_key: trimmed(draft.apiKey),
    // "Xoá khoá đã lưu": không dùng khoá đó nữa (nhà cung cấp có khoá `.env` thì máy chủ dùng khoá `.env`).
    profile_id: draft.clearApiKey ? null : (profileId ?? null),
  };
}

export const KINDS = {
  llm: {
    key: "llm",
    label: "Mô hình ngôn ngữ (LLM)",
    title: "Sinh câu trả lời (LLM)",
    description:
      "Mô hình đọc các đoạn tài liệu tìm được và viết câu trả lời cho sinh viên. Đổi mô hình đang dùng có hiệu lực từ câu hỏi tiếp theo.",
    providers: LLM_PROVIDERS,
  },
  embedding: {
    key: "embedding",
    label: "Mô hình nhúng (Embedding)",
    title: "Nhúng văn bản (Embedding)",
    description:
      "Mô hình biến câu hỏi và các đoạn tài liệu thành vector để tìm theo ngữ nghĩa. Đổi mô hình có hiệu lực sau khi khởi động lại backend và cần nạp lại toàn bộ tài liệu.",
    providers: EMBEDDING_PROVIDERS,
  },
  reranker: {
    key: "reranker",
    label: "Mô hình xếp hạng lại (Reranker)",
    title: "Xếp hạng lại (Rerank)",
    description:
      "Sắp xếp lại các đoạn ứng viên theo mức liên quan trước khi đưa vào LLM. Đổi mô hình đang dùng có hiệu lực ngay.",
    providers: RERANKER_PROVIDERS,
  },
};

export const KIND_ORDER = ["llm", "embedding", "reranker"];

export function providerFields(kind, provider) {
  return FIELDS[kind]?.[provider] ?? [];
}

export function keyRule(kind, provider) {
  return KEY_RULES[kind]?.[provider] ?? null;
}

export function providerName(kind, provider) {
  return KINDS[kind]?.providers.find((item) => item.key === provider)?.name ?? provider ?? "—";
}

/** Tên hiển thị ngắn của mô hình: `deployment` với Azure, còn lại là `model`. */
export function profileModelLabel(profile) {
  if (!profile) return "—";
  return (profile.provider === "azure" ? profile.deployment_name : profile.model) || "—";
}

export function emptyDraft(kind) {
  const draft = { name: "", provider: KINDS[kind].providers[0].key, apiKey: "", clearApiKey: false };
  FIELD_NAMES.forEach((name) => {
    draft[name] = "";
  });
  if (kind === "llm") draft.api_version = "2024-02-15-preview";
  return draft;
}

export function draftFromProfile(profile) {
  const draft = { name: profile.name ?? "", provider: profile.provider, apiKey: "", clearApiKey: false };
  FIELD_NAMES.forEach((name) => {
    draft[name] = profile[name] == null ? "" : String(profile[name]);
  });
  return draft;
}

/**
 * Lỗi theo tên trường (`apiKey` cho ô khoá); `{}` = hợp lệ.
 * `hasStoredKey`: profile đang sửa đã có khoá của đúng nhà cung cấp này.
 */
export function validateDraft(kind, draft, { hasStoredKey = false } = {}) {
  const errors = {};
  providerFields(kind, draft.provider).forEach((field) => {
    const value = String(draft[field.name] ?? "").trim();
    if (field.required && !value) errors[field.name] = `Nhập ${field.label.toLowerCase()}.`;
    else if (field.url && value && !URL_PATTERN.test(value))
      errors[field.name] = "Phải bắt đầu bằng http:// hoặc https://.";
    else if (field.number && value && !(Number.isInteger(Number(value)) && Number(value) > 0))
      errors[field.name] = "Phải là số nguyên dương.";
  });
  if (draft.name.trim().length > 100) errors.name = "Tối đa 100 ký tự.";
  if (keyRule(kind, draft.provider)?.required && !draft.apiKey.trim() && !(hasStoredKey && !draft.clearApiKey)) {
    errors.apiKey = "Nhập API key.";
  }
  return errors;
}

/** Tên mặc định khi người dùng để trống: chính tên mô hình. */
export function defaultName(draft) {
  return String((draft.provider === "azure" ? draft.deployment_name : draft.model) ?? "").trim();
}

/** Payload POST (có `kind`) hoặc PUT; chỉ gửi trường của nhà cung cấp đang chọn. */
export function buildPayload(kind, draft, { isEdit = false } = {}) {
  const payload = { name: draft.name.trim() || defaultName(draft), provider: draft.provider };
  if (!isEdit) payload.kind = kind;
  providerFields(kind, draft.provider).forEach((field) => {
    const value = String(draft[field.name] ?? "").trim();
    if (field.number) payload[field.name] = value ? Number(value) : null;
    else payload[field.name] = value || null;
  });
  if (keyRule(kind, draft.provider)) {
    const key = draft.apiKey.trim();
    if (key) payload.api_key = key;
    else if (isEdit && draft.clearApiKey) payload.clear_api_key = true;
  }
  return payload;
}

/** Payload POST /model-profiles/test-llm: không nhập khoá thì máy chủ dùng khoá đã lưu của profile. */
export function buildTestPayload(draft, profileId) {
  const trimmed = (value) => String(value ?? "").trim() || null;
  return {
    provider: draft.provider,
    model: trimmed(draft.provider === "azure" ? draft.deployment_name : draft.model),
    api_key: trimmed(draft.apiKey),
    base_url: trimmed(draft.base_url),
    endpoint: trimmed(draft.endpoint),
    deployment_name: trimmed(draft.deployment_name),
    api_version: trimmed(draft.api_version),
    profile_id: profileId ?? null,
  };
}

/** Payload POST /model-profiles/test-reranker: không nhập khoá thì máy chủ dùng khoá đã lưu của profile. */
export function buildRerankerTestPayload(draft, profileId) {
  const trimmed = (value) => String(value ?? "").trim() || null;
  return {
    provider: draft.provider,
    model: trimmed(draft.model),
    base_url: RERANKER_BASE_URL_PROVIDERS.includes(draft.provider) ? trimmed(draft.base_url) : null,
    api_key: trimmed(draft.apiKey),
    profile_id: profileId ?? null,
  };
}

/** Payload POST /model-profiles/test-embedding: không nhập khoá thì máy chủ dùng khoá đã lưu của profile. */
export function buildEmbeddingTestPayload(draft, profileId) {
  const trimmed = (value) => String(value ?? "").trim() || null;
  const dimension = trimmed(draft.dimension);
  return {
    provider: draft.provider,
    model: trimmed(draft.model),
    base_url: draft.provider === "openai_compatible" ? trimmed(draft.base_url) : null,
    dimension: dimension ? Number(dimension) : null,
    api_key: trimmed(draft.apiKey),
    profile_id: profileId ?? null,
  };
}

/** So sánh bản nháp với bản gốc theo đúng các trường sẽ gửi đi. */
export function isDraftDirty(kind, draft, initial) {
  if (draft.apiKey.trim() || draft.clearApiKey) return true;
  if (draft.name.trim() !== initial.name.trim() || draft.provider !== initial.provider) return true;
  return providerFields(kind, draft.provider).some(
    (field) => String(draft[field.name] ?? "").trim() !== String(initial[field.name] ?? "").trim()
  );
}
