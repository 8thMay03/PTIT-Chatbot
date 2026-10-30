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
  { key: "openai", name: "OpenAI", description: "API chính thức của OpenAI." },
  { key: "gemini", name: "Google Gemini", description: "Gemini qua Google AI Studio." },
  { key: "azure", name: "Azure OpenAI", description: "Deployment OpenAI trên Azure." },
  {
    key: "openai_compatible",
    name: "Tương thích OpenAI",
    description: "Ollama, vLLM, DeepSeek, Qwen… qua endpoint /v1.",
  },
];

export const EMBEDDING_PROVIDERS = [
  { key: "openai", name: "OpenAI", description: "Gọi API embeddings của OpenAI." },
  {
    key: "sentence-transformers",
    name: "Sentence-Transformers",
    description: "Mô hình Hugging Face chạy cục bộ trên máy chủ.",
  },
];

export const RERANKER_PROVIDERS = [
  {
    key: "cross-encoder",
    name: "Cross-Encoder",
    description: "Chấm điểm từng cặp câu hỏi–đoạn, chạy cục bộ. Chính xác hơn heuristic, chậm hơn.",
  },
];

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

// Số chiều của các mô hình nhúng phổ biến: chọn mô hình thì tự điền số chiều.
export const KNOWN_EMBEDDING_DIMENSIONS = {
  "text-embedding-3-small": 1536,
  "text-embedding-3-large": 3072,
  "text-embedding-ada-002": 1536,
  "BAAI/bge-m3": 1024,
  "intfloat/multilingual-e5-base": 768,
  "intfloat/multilingual-e5-large": 1024,
  "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
};

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
      {
        name: "base_url",
        label: "Base URL",
        url: true,
        placeholder: "https://api.openai.com/v1",
        hint: "Để trống nếu gọi thẳng OpenAI. Chỉ điền khi đi qua proxy hoặc gateway riêng.",
      },
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
      { name: "dimension", label: "Số chiều vector", required: true, number: true, placeholder: "1536" },
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
        hint: "Tên mô hình trên Hugging Face; máy chủ tải về ở lần khởi động đầu tiên dùng mô hình.",
      },
      { name: "dimension", label: "Số chiều vector", required: true, number: true, placeholder: "1024" },
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
        hint: "Tên mô hình trên Hugging Face. Lần dùng đầu tiên máy chủ sẽ tải mô hình về; nếu không tải được, hệ thống tự quay về heuristic.",
      },
    ],
  },
};

/**
 * Khoá API: `required` = không có khoá (kể cả khoá `.env`) thì mô hình không chạy;
 * `envFallback` = để trống thì máy chủ dùng khoá trong `.env`.
 */
const KEY_RULES = {
  llm: {
    openai: { envFallback: true },
    gemini: { envFallback: true },
    azure: { envFallback: true },
    openai_compatible: { envFallback: false },
  },
  embedding: { openai: { envFallback: true } },
  reranker: {},
};

export const KINDS = {
  llm: {
    key: "llm",
    label: "LLM model",
    title: "Sinh câu trả lời (LLM)",
    description:
      "Mô hình đọc các đoạn tài liệu tìm được và viết câu trả lời cho sinh viên. Đổi mô hình đang dùng có hiệu lực từ câu hỏi tiếp theo.",
    providers: LLM_PROVIDERS,
  },
  embedding: {
    key: "embedding",
    label: "Embedding model",
    title: "Nhúng văn bản (Embedding)",
    description:
      "Mô hình biến câu hỏi và các đoạn tài liệu thành vector để tìm theo ngữ nghĩa. Đổi mô hình có hiệu lực sau khi khởi động lại backend và cần nạp lại toàn bộ tài liệu.",
    providers: EMBEDDING_PROVIDERS,
  },
  reranker: {
    key: "reranker",
    label: "Rerank model",
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

/** Lỗi theo tên trường; `{}` = hợp lệ. */
export function validateDraft(kind, draft) {
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

/** So sánh bản nháp với bản gốc theo đúng các trường sẽ gửi đi. */
export function isDraftDirty(kind, draft, initial) {
  if (draft.apiKey.trim() || draft.clearApiKey) return true;
  if (draft.name.trim() !== initial.name.trim() || draft.provider !== initial.provider) return true;
  return providerFields(kind, draft.provider).some(
    (field) => String(draft[field.name] ?? "").trim() !== String(initial[field.name] ?? "").trim()
  );
}
