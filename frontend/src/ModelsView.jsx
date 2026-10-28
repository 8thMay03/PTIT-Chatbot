import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownUp,
  ArrowRight,
  Binary,
  Check,
  CheckCircle2,
  ChevronRight,
  Cloud,
  Copy,
  Cpu,
  Eye,
  EyeOff,
  ListOrdered,
  Loader2,
  Lock,
  MessageSquareText,
  RefreshCw,
  Save,
  Server,
  ShieldAlert,
  ShieldCheck,
  Undo2,
  Zap,
} from "lucide-react";
import { configApi, describeError, errorMessage, queryKeys } from "./api";
import { useToast } from "./components/Toast";

/*
 * Màn chọn mô hình cho đúng ba khâu backend thật sự dùng:
 *   - LLM sinh câu trả lời: đọc lại cấu hình ở mỗi request → đổi được ngay.
 *   - Reranker: đọc lại cấu hình ở mỗi lần xếp hạng → đổi được ngay.
 *   - Embedding: Retriever và IngestionPipeline tạo mô hình nhúng một lần khi
 *     backend khởi động, nên đổi qua API không có tác dụng → chỉ hiển thị.
 *
 * Bản trước là một "kho nhà cung cấp" viết cứng có cả VLM/ASR/TTS/OCR mà backend
 * không hỗ trợ, và báo "đã lưu" cho những lựa chọn không hề được gửi đi.
 *
 * Bố cục: thanh "luồng xử lý" xếp ba khâu theo đúng thứ tự một câu hỏi đi qua
 * (nhúng → xếp hạng lại → sinh câu trả lời), chọn khâu nào thì mở bảng chỉnh
 * của khâu đó. Ba bảng luôn mounted để không mất bản nháp khi đổi khâu.
 */

function OpenAILogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.475 4.475 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1683a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4947zm-9.66-4.996a4.47 4.47 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1402-2.517zm-1.808-9.4582a4.4607 4.4607 0 0 1 2.342-1.9729v.1656l-.0047 5.5164a.79.79 0 0 0 .3927.6813l5.8429 3.3686-2.02 1.1682a.0757.0757 0 0 1-.071 0l-4.8304-2.7913a4.4944 4.4944 0 0 1-1.6515-6.1359zm15.0845-2.054a.7854.7854 0 0 0-.7807 0l-5.8428 3.3685V6.977a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.4944 4.4851 4.4703 4.4703 0 0 1-.0047.5284l-.142-.0852-4.6344-2.6599zm2.4578 4.0984a4.4703 4.4703 0 0 1-.5347 3.0137l-.142-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685V10.743a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.1402 2.517 4.4703 4.4703 0 0 1 .0327.3995zm-8.8136 2.054a.79.79 0 0 0-.3927-.6813L8.29 8.083l2.02-1.1682a.0757.0757 0 0 1 .071 0l4.8304 2.7913a4.4944 4.4944 0 0 1 1.6515 6.1359 4.4607 4.4607 0 0 1-2.342 1.9729v-.1656l.0047-5.5164zm-1.0268.5916l2.3948 1.3824-2.3948 1.3824-2.3948-1.3824 2.3948-1.3824z" />
    </svg>
  );
}

function GeminiLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z"
        fill="url(#mdl-gemini-grad)"
      />
      <defs>
        <linearGradient id="mdl-gemini-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.33" stopColor="#9B72CB" />
          <stop offset="0.66" stopColor="#D96570" />
          <stop offset="1" stopColor="#F4B400" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// LLM
// ---------------------------------------------------------------------------

const LLM_PROVIDERS = [
  { key: "openai", name: "OpenAI", description: "API chính thức của OpenAI.", Icon: OpenAILogo },
  { key: "gemini", name: "Google Gemini", description: "Gemini qua Google AI Studio.", Icon: GeminiLogo },
  { key: "azure", name: "Azure OpenAI", description: "Deployment OpenAI trên Azure.", Icon: Cloud },
  {
    key: "openai_compatible",
    name: "Tương thích OpenAI",
    description: "Ollama, vLLM, DeepSeek, Qwen… qua endpoint /v1.",
    Icon: Server,
  },
];

// Tên nhà cung cấp mà backend đăng ký vào OpenAICompatibleProvider (app/llm/factory.py).
const COMPATIBLE_ALIASES = [
  "openai_compatible",
  "local",
  "ollama",
  "vllm",
  "deepseek",
  "moonshot",
  "tongyi",
  "qwen",
  "zhipu",
  "xai",
];

const COMPATIBLE_PRESETS = [
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

const URL_PATTERN = /^https?:\/\/\S+$/i;

/** Các trường riêng của từng nhà cung cấp, ánh xạ thẳng sang UpdateLLMConfig. */
const LLM_FIELDS = {
  openai: [
    {
      name: "model",
      label: "Mô hình",
      payloadKey: "openai_model",
      required: true,
      placeholder: "gpt-4.1-mini",
      suggestions: ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
    },
    {
      name: "baseUrl",
      label: "Base URL",
      payloadKey: "openai_base_url",
      url: true,
      // Máy chủ chỉ trả base URL của nhà cung cấp đang dùng, nên chỉ gửi khi
      // người dùng thật sự sửa — tránh xoá nhầm giá trị họ không nhìn thấy.
      sendOnlyIfChanged: true,
      placeholder: "https://api.openai.com/v1",
      hint: "Để trống nếu gọi thẳng OpenAI. Chỉ điền khi đi qua proxy hoặc gateway riêng.",
    },
  ],
  gemini: [
    {
      name: "model",
      label: "Mô hình",
      payloadKey: "gemini_model",
      required: true,
      placeholder: "gemini-2.0-flash",
      suggestions: ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    },
  ],
  azure: [
    {
      name: "endpoint",
      label: "Endpoint",
      payloadKey: "azure_openai_endpoint",
      required: true,
      url: true,
      placeholder: "https://<tên-tài-nguyên>.openai.azure.com",
    },
    {
      name: "deployment",
      label: "Tên deployment",
      payloadKey: "azure_openai_deployment_name",
      required: true,
      placeholder: "gpt-4o-mini",
      hint: "Tên deployment đã tạo trên Azure, không phải tên mô hình gốc.",
    },
    {
      name: "apiVersion",
      label: "API version",
      payloadKey: "azure_openai_api_version",
      required: true,
      placeholder: "2024-02-15-preview",
    },
  ],
  openai_compatible: [
    {
      name: "baseUrl",
      label: "Base URL",
      payloadKey: "openai_compatible_base_url",
      required: true,
      url: true,
      placeholder: "http://localhost:11434/v1",
    },
    {
      name: "model",
      label: "Mô hình",
      payloadKey: "openai_compatible_model",
      required: true,
      placeholder: "qwen2.5:7b",
    },
  ],
};

const KEY_FIELD = {
  openai: { payloadKey: "openai_api_key", hasKey: "openai_has_key", required: true },
  gemini: { payloadKey: "gemini_api_key", hasKey: "gemini_has_key", required: true },
  azure: { payloadKey: "azure_openai_api_key", hasKey: "azure_has_key", required: true },
  openai_compatible: {
    payloadKey: "openai_compatible_api_key",
    hasKey: "openai_compatible_has_key",
    required: false,
  },
};

function normalizeLlmProvider(value) {
  const name = String(value || "").trim().toLowerCase();
  if (name === "gemini" || name === "google") return "gemini";
  if (name === "azure" || name === "azure_openai") return "azure";
  if (COMPATIBLE_ALIASES.includes(name)) return "openai_compatible";
  // Tên lạ thì backend cũng quay về OpenAI (get_llm_provider).
  return "openai";
}

function llmProviderName(key) {
  return LLM_PROVIDERS.find((item) => item.key === key)?.name ?? key;
}

function llmDraftFromConfig(llm = {}) {
  const provider = normalizeLlmProvider(llm.provider);
  return {
    provider,
    openai: {
      model: llm.openai_model || "",
      baseUrl: provider === "openai" ? llm.base_url || "" : "",
      apiKey: "",
    },
    gemini: { model: llm.gemini_model || "", apiKey: "" },
    azure: {
      endpoint: llm.azure_openai_endpoint || "",
      deployment: llm.azure_openai_deployment_name || "",
      apiVersion: llm.azure_openai_api_version || "",
      apiKey: "",
    },
    openai_compatible: {
      baseUrl: llm.openai_compatible_base_url || "",
      model: llm.openai_compatible_model || "",
      apiKey: "",
    },
  };
}

function validateLlm(draft) {
  const errors = {};
  const values = draft[draft.provider];
  LLM_FIELDS[draft.provider].forEach((field) => {
    const value = values[field.name].trim();
    if (field.required && !value) errors[field.name] = `Nhập ${field.label.toLowerCase()}.`;
    else if (field.url && value && !URL_PATTERN.test(value))
      errors[field.name] = "Phải bắt đầu bằng http:// hoặc https://.";
  });
  return errors;
}

function isLlmDirty(draft, initial) {
  if (draft.provider !== initial.provider) return true;
  const values = draft[draft.provider];
  const base = initial[draft.provider];
  if (values.apiKey.trim()) return true;
  return LLM_FIELDS[draft.provider].some((field) => values[field.name].trim() !== base[field.name].trim());
}

function buildLlmPayload(draft, initial) {
  const provider = draft.provider;
  const values = draft[provider];
  const base = initial[provider];
  const llm = { provider };
  LLM_FIELDS[provider].forEach((field) => {
    const value = values[field.name].trim();
    if (field.sendOnlyIfChanged) {
      if (value !== base[field.name].trim()) llm[field.payloadKey] = value || null;
    } else {
      llm[field.payloadKey] = value;
    }
  });
  // Backend coi chuỗi rỗng là "xoá khoá" với một số nhà cung cấp, nên chỉ gửi khi có nhập.
  const key = values.apiKey.trim();
  if (key) llm[KEY_FIELD[provider].payloadKey] = key;
  return { llm };
}

function buildTestPayload(draft) {
  const provider = draft.provider;
  const values = draft[provider];
  const trimmed = (value) => (value ?? "").trim() || null;
  return {
    provider,
    model: trimmed(provider === "azure" ? values.deployment : values.model),
    // Không nhập khoá thì backend dùng khoá đang lưu trên máy chủ.
    api_key: trimmed(values.apiKey),
    base_url: trimmed(values.baseUrl),
    endpoint: trimmed(values.endpoint),
    deployment_name: trimmed(values.deployment),
    api_version: trimmed(values.apiVersion),
  };
}

// ---------------------------------------------------------------------------
// Reranker & Embedding
// ---------------------------------------------------------------------------

const RERANKER_PROVIDERS = [
  {
    key: "heuristic",
    name: "Heuristic",
    description: "Kết hợp điểm vector, BM25 và độ phủ từ khoá.",
    traits: ["Nhanh", "Không cần tải mô hình"],
    Icon: ListOrdered,
  },
  {
    key: "cross-encoder",
    name: "Cross-Encoder",
    description: "Mô hình chấm điểm từng cặp câu hỏi–đoạn, chạy cục bộ trên máy chủ.",
    traits: ["Chính xác hơn", "Chậm hơn", "Tải mô hình lần đầu"],
    Icon: Cpu,
  },
];

const CROSS_ENCODER_SUGGESTIONS = [
  "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
  "BAAI/bge-reranker-base",
  "BAAI/bge-reranker-v2-m3",
];

function rerankerDraftFromConfig(reranker = {}) {
  return {
    provider: reranker.provider === "cross-encoder" ? "cross-encoder" : "heuristic",
    model: reranker.model || "",
  };
}

const EMBEDDING_PROVIDER_NAMES = {
  openai: "OpenAI",
  "sentence-transformers": "Sentence-Transformers (chạy cục bộ)",
  hash: "Hash (chỉ dùng để thử nghiệm)",
};

// ---------------------------------------------------------------------------
// Thành phần giao diện dùng lại trong màn này
// ---------------------------------------------------------------------------

function useWarnBeforeUnload(active) {
  useEffect(() => {
    if (!active) return undefined;
    function onBeforeUnload(event) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [active]);
}

/** Báo trạng thái "có thay đổi chưa lưu" lên thanh luồng xử lý. */
function useReportDirty(dirty, onDirtyChange) {
  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);
}

function StatusPill({ tone = "muted", children }) {
  return <span className={`mdl-pill is-${tone}`}>{children}</span>;
}

function Section({ id, title, description, badge, children, footer }) {
  return (
    <section className="mdl-card" aria-labelledby={`${id}-title`} id={id}>
      <header className="mdl-card-head">
        <div className="mdl-card-heading">
          <h3 id={`${id}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        {badge && <span className="mdl-card-badge">{badge}</span>}
      </header>
      <div className="mdl-card-body">{children}</div>
      {footer && <footer className="mdl-card-foot">{footer}</footer>}
    </section>
  );
}

/** Radio dạng thẻ; `layout="list"` xếp dọc (nhà cung cấp LLM), `"grid"` chia cột. */
function OptionGroup({ name, legend, options, value, onChange, layout = "grid" }) {
  return (
    <fieldset className={`mdl-options is-${layout}`}>
      <legend className="mdl-label">{legend}</legend>
      <div className="mdl-options-items">
        {options.map(({ key, name: label, description, traits, Icon }) => {
          const selected = value === key;
          return (
            <label key={key} className={`mdl-option ${selected ? "is-selected" : ""}`}>
              <input
                type="radio"
                className="sr-only"
                name={name}
                value={key}
                checked={selected}
                onChange={() => onChange(key)}
              />
              <span className="mdl-option-icon" aria-hidden="true">
                <Icon size={18} />
              </span>
              <span className="mdl-option-text">
                <strong>{label}</strong>
                <span>{description}</span>
                {traits && (
                  <span className="mdl-traits">
                    {traits.map((trait) => (
                      <span key={trait} className="mdl-trait">
                        {trait}
                      </span>
                    ))}
                  </span>
                )}
              </span>
              <span className="mdl-option-check" aria-hidden="true">
                {selected && <Check size={12} strokeWidth={3} />}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function TextField({ id, field, value, onChange, error }) {
  const hintId = `${id}-hint`;
  const describedBy = [error ? `${id}-error` : null, field.hint ? hintId : null].filter(Boolean).join(" ");
  return (
    <div className="mdl-field">
      <label htmlFor={id} className="mdl-label">
        {field.label}
        {!field.required && <span className="mdl-optional">Tuỳ chọn</span>}
      </label>
      <input
        id={id}
        type="text"
        className={`mdl-input ${error ? "is-invalid" : ""}`}
        value={value}
        placeholder={field.placeholder}
        spellCheck={false}
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {field.suggestions && (
        <div className="mdl-suggestions" role="group" aria-label={`Gợi ý ${field.label.toLowerCase()}`}>
          {field.suggestions.map((item) => (
            <button
              key={item}
              type="button"
              className="mdl-chip"
              aria-pressed={value.trim() === item}
              onClick={() => onChange(item)}
            >
              {item}
            </button>
          ))}
        </div>
      )}
      {error && (
        <span className="mdl-field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
      {field.hint && (
        <span className="mdl-field-hint" id={hintId}>
          {field.hint}
        </span>
      )}
    </div>
  );
}

function ApiKeyField({ id, value, onChange, hasKey, required, label = "API key" }) {
  const [visible, setVisible] = useState(false);
  const hintId = `${id}-hint`;
  return (
    <div className="mdl-field">
      <div className="mdl-field-label-row">
        <label htmlFor={id} className="mdl-label">
          {label}
        </label>
        {hasKey ? (
          <StatusPill tone="ok">
            <Check size={12} /> Máy chủ đã có khoá
          </StatusPill>
        ) : required ? (
          <StatusPill tone="warn">
            <AlertTriangle size={12} /> Chưa có khoá
          </StatusPill>
        ) : (
          <StatusPill>Không bắt buộc</StatusPill>
        )}
      </div>
      <div className="mdl-secret">
        <input
          id={id}
          type={visible ? "text" : "password"}
          className="mdl-input"
          value={value}
          placeholder={hasKey ? "Để trống để giữ khoá hiện tại" : "Dán API key"}
          autoComplete="new-password"
          spellCheck={false}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          type="button"
          className="mdl-secret-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? "Ẩn API key" : "Hiện API key"}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      <span className="mdl-field-hint" id={hintId}>
        Khoá được mã hoá trước khi lưu trên máy chủ, không lưu trong trình duyệt và không bao giờ hiển thị lại.
      </span>
    </div>
  );
}

function SectionActions({ dirty, saving, onReset, onSave }) {
  return (
    <>
      <span className={`mdl-dirty ${dirty ? "is-dirty" : ""}`} role="status">
        {dirty ? "Có thay đổi chưa lưu" : ""}
      </span>
      <div className="mdl-actions">
        {dirty && (
          <button type="button" className="ghost-btn" onClick={onReset} disabled={saving}>
            <Undo2 size={15} />
            Hoàn tác
          </button>
        )}
        <button type="button" className="primary-btn" onClick={onSave} disabled={!dirty || saving}>
          {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
          {saving ? "Đang lưu..." : "Lưu"}
        </button>
      </div>
    </>
  );
}

/** Ghi cấu hình mới vào cache chung rồi yêu cầu đọc lại để hai tab cùng đồng bộ. */
async function saveConfig(queryClient, payload) {
  const next = await configApi.update(payload);
  queryClient.setQueryData(queryKeys.config, next);
  await queryClient.invalidateQueries({ queryKey: queryKeys.config });
  return next;
}

// ---------------------------------------------------------------------------
// Mục LLM
// ---------------------------------------------------------------------------

function LlmSection({ llm, onDirtyChange }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  // Chỉ tạo lại bản nháp khi trường liên quan đến LLM đổi; lưu temperature ở tab
  // Cấu hình RAG không được xoá mô hình/API key đang nhập dở.
  const initialKey = [
    llm.provider,
    llm.openai_model,
    llm.base_url,
    llm.gemini_model,
    llm.azure_openai_endpoint,
    llm.azure_openai_deployment_name,
    llm.azure_openai_api_version,
    llm.openai_compatible_base_url,
    llm.openai_compatible_model,
  ].join("\u0000");
  const initial = useMemo(() => llmDraftFromConfig(llm), [initialKey]);
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const formRef = useRef(null);

  useEffect(() => {
    setDraft(initial);
    setShowErrors(false);
    setTestResult(null);
  }, [initial]);

  const provider = draft.provider;
  const values = draft[provider];
  const keyField = KEY_FIELD[provider];
  const hasKey = Boolean(llm[keyField.hasKey]);
  const errors = useMemo(() => validateLlm(draft), [draft]);
  const dirty = isLlmDirty(draft, initial);
  useWarnBeforeUnload(dirty);
  useReportDirty(dirty, onDirtyChange);

  function update(name, value) {
    setDraft((current) => ({ ...current, [provider]: { ...current[provider], [name]: value } }));
    setTestResult(null);
  }

  function selectProvider(next) {
    setDraft((current) => ({ ...current, provider: next }));
    setShowErrors(false);
    setTestResult(null);
  }

  function resetDraft() {
    setDraft(initial);
    setShowErrors(false);
    setTestResult(null);
  }

  function applyPreset(preset) {
    setDraft((current) => ({
      ...current,
      openai_compatible: {
        ...current.openai_compatible,
        baseUrl: preset.baseUrl,
        model: preset.model || current.openai_compatible.model,
      },
    }));
    setTestResult(null);
  }

  /** Trả về true nếu hợp lệ; nếu không thì hiện lỗi và đưa focus tới ô đầu tiên sai. */
  function ensureValid() {
    if (Object.keys(errors).length === 0) return true;
    setShowErrors(true);
    const first = LLM_FIELDS[provider].find((field) => errors[field.name]);
    formRef.current?.querySelector(`#llm-${provider}-${first?.name}`)?.focus();
    return false;
  }

  async function handleTest() {
    if (!ensureValid()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const data = await configApi.testLlm(buildTestPayload(draft));
      setTestResult(data);
    } catch (err) {
      setTestResult({
        success: false,
        message: errorMessage(err, "Máy chủ từ chối yêu cầu kiểm tra."),
      });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    if (!ensureValid()) return;
    setSaving(true);
    try {
      const next = await saveConfig(queryClient, buildLlmPayload(draft, initial));
      // Lưu chỉ API key không đổi provider/model, nên effect theo `initialKey` không chạy.
      // Đồng bộ lại bản nháp từ response để khoá đã lưu không còn nằm trong input.
      setDraft(llmDraftFromConfig(next.llm ?? {}));
      setShowErrors(false);
      setTestResult(null);
      toast.success(`Chatbot đã chuyển sang ${next.llm?.model ?? "mô hình mới"} · ${llmProviderName(provider)}.`);
    } catch (err) {
      toast.error(
        `Chưa lưu được mô hình LLM. ${errorMessage(err, "Máy chủ từ chối cập nhật cấu hình.")}`
      );
    } finally {
      setSaving(false);
    }
  }

  const currentProvider = normalizeLlmProvider(llm.provider);
  const currentMissingKey =
    KEY_FIELD[currentProvider].required && !llm[KEY_FIELD[currentProvider].hasKey];

  return (
    <Section
      id="mdl-llm"
      title="Sinh câu trả lời (LLM)"
      description="Mô hình đọc các đoạn tài liệu tìm được và viết câu trả lời cho sinh viên."
      badge={
        <>
          <Zap size={13} /> Áp dụng từ câu hỏi tiếp theo
        </>
      }
      footer={<SectionActions dirty={dirty} saving={saving} onReset={resetDraft} onSave={handleSave} />}
    >
      {currentMissingKey && (
        <div className="inline-alert is-warning mdl-alert">
          <AlertTriangle size={16} />
          <span>
            {llmProviderName(currentProvider)} đang được dùng nhưng máy chủ chưa có API key — chatbot sẽ không
            trả lời được cho tới khi lưu khoá.
          </span>
        </div>
      )}

      <div className="mdl-llm-layout">
        <OptionGroup
          name="llm-provider"
          legend="Nhà cung cấp"
          layout="list"
          options={LLM_PROVIDERS}
          value={provider}
          onChange={selectProvider}
        />

        <div ref={formRef} className="mdl-llm-form">
          <div className="mdl-form-head">
            <h4>Kết nối {llmProviderName(provider)}</h4>
            {provider === currentProvider ? (
              <StatusPill tone="brand">Đang dùng</StatusPill>
            ) : (
              <StatusPill tone="warn">Chưa áp dụng — bấm Lưu để chuyển</StatusPill>
            )}
          </div>

          {provider === "openai_compatible" && (
            <div className="mdl-presets" role="group" aria-label="Điền nhanh địa chỉ máy chủ">
              <span>Điền nhanh</span>
              {COMPATIBLE_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  className="mdl-chip"
                  aria-pressed={values.baseUrl === preset.baseUrl}
                  onClick={() => applyPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          )}

          <div className="mdl-grid">
            {LLM_FIELDS[provider].map((field) => (
              <TextField
                key={`${provider}-${field.name}`}
                id={`llm-${provider}-${field.name}`}
                field={field}
                value={values[field.name]}
                onChange={(value) => update(field.name, value)}
                error={
                  showErrors || (field.url && values[field.name].trim()) ? errors[field.name] : undefined
                }
              />
            ))}
          </div>

          <ApiKeyField
            key={provider}
            id={`llm-${provider}-key`}
            value={values.apiKey}
            onChange={(value) => update("apiKey", value)}
            hasKey={hasKey}
            required={keyField.required}
          />

          <div className="mdl-test">
            <div className="mdl-test-row">
              <div className="mdl-test-intro">
                <strong>Kiểm tra kết nối</strong>
                <span>Gửi một yêu cầu ngắn bằng thông tin đang nhập, chưa cần lưu. Để trống API key thì dùng khoá trên máy chủ.</span>
              </div>
              <button type="button" className="ghost-btn" onClick={handleTest} disabled={testing || saving}>
                {testing ? <Loader2 size={15} className="spin" /> : <Zap size={15} />}
                {testing ? "Đang kiểm tra..." : "Kiểm tra"}
              </button>
            </div>

            {testResult && (
              <div
                className={`mdl-test-result ${testResult.success ? "is-ok" : "is-error"}`}
                role={testResult.success ? "status" : "alert"}
              >
                {testResult.success ? <CheckCircle2 size={17} /> : <AlertCircle size={17} />}
                <div>
                  <strong>{testResult.success ? "Kết nối thành công" : "Kết nối thất bại"}</strong>
                  <p>{testResult.message}</p>
                  {(testResult.latency_ms != null || testResult.sample_output) && (
                    <p className="mdl-test-meta">
                      {testResult.latency_ms != null && <>Thời gian phản hồi: {Math.round(testResult.latency_ms)} ms</>}
                      {testResult.sample_output && <> · Mô hình trả lời: “{testResult.sample_output}”</>}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Mục Embedding (chỉ đọc)
// ---------------------------------------------------------------------------

function EmbeddingSection({ embedding, openaiHasKey }) {
  const [copied, setCopied] = useState(false);
  const provider = (embedding.provider || "").toLowerCase();
  const snippet = `EMBEDDING_PROVIDER=${provider || "openai"}\nEMBEDDING_MODEL=${embedding.model || ""}`;

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard bị chặn (http hoặc quyền) — người dùng vẫn chọn và chép tay được */
    }
  }

  return (
    <Section
      id="mdl-embedding"
      title="Nhúng văn bản (Embedding)"
      description="Mô hình biến câu hỏi và các đoạn tài liệu thành vector để tìm kiếm theo ngữ nghĩa."
      badge={
        <>
          <Lock size={13} /> Chỉ đọc · đổi qua <code>.env</code>
        </>
      }
    >
      <dl className="mdl-spec">
        <div>
          <dt>Nhà cung cấp</dt>
          <dd>{EMBEDDING_PROVIDER_NAMES[provider] ?? (provider || "—")}</dd>
        </div>
        <div>
          <dt>Mô hình</dt>
          <dd className="is-mono">{embedding.model || "—"}</dd>
        </div>
        <div>
          <dt>API key</dt>
          <dd>
            {provider !== "openai" ? (
              "Không cần"
            ) : openaiHasKey ? (
              "Dùng chung khoá OpenAI ở khâu LLM"
            ) : (
              <StatusPill tone="warn">
                <AlertTriangle size={12} /> Chưa có API key OpenAI
              </StatusPill>
            )}
          </dd>
        </div>
      </dl>

      <p className="mdl-note">
        Mô hình nhúng được nạp một lần khi backend khởi động và quyết định số chiều của mọi vector đã lưu trong
        kho, nên không đổi được tại đây.
      </p>

      <div className="mdl-howto">
        <h4>Muốn đổi mô hình nhúng</h4>
        <ol className="mdl-steps">
          <li>
            <span>
              Sửa tệp <code>.env</code> của backend:
            </span>
            <div className="mdl-code">
              <pre>{snippet}</pre>
              <button
                type="button"
                className="mdl-code-copy"
                onClick={copySnippet}
                aria-label="Chép cấu hình hiện tại"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Đã chép" : "Chép"}
              </button>
            </div>
          </li>
          <li>
            <span>
              Đặt <code>VECTOR_DIM</code> bằng số chiều của mô hình mới.
            </span>
          </li>
          <li>
            <span>Khởi động lại backend.</span>
          </li>
          <li>
            <span>
              Vào <strong>Dataset</strong> → <strong>Nạp lại toàn bộ</strong> để tạo lại vector cho mọi tài liệu.
            </span>
          </li>
        </ol>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Mục Reranker
// ---------------------------------------------------------------------------

function RerankerSection({ reranker, onDirtyChange }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const initialKey = `${reranker.provider ?? ""}\u0000${reranker.model ?? ""}`;
  const initial = useMemo(() => rerankerDraftFromConfig(reranker), [initialKey]);
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const modelRef = useRef(null);

  useEffect(() => {
    setDraft(initial);
    setShowErrors(false);
  }, [initial]);

  const usesModel = draft.provider === "cross-encoder";
  const modelError = usesModel && !draft.model.trim() ? "Nhập tên mô hình cross-encoder." : undefined;
  const dirty =
    draft.provider !== initial.provider || (usesModel && draft.model.trim() !== initial.model.trim());
  useWarnBeforeUnload(dirty);
  useReportDirty(dirty, onDirtyChange);

  async function handleSave() {
    if (modelError) {
      setShowErrors(true);
      modelRef.current?.querySelector("input")?.focus();
      return;
    }
    setSaving(true);
    try {
      const payload = { reranker: { provider: draft.provider } };
      if (usesModel) payload.reranker.model = draft.model.trim();
      const next = await saveConfig(queryClient, payload);
      toast.success(
        usesModel
          ? `Đã chuyển reranker sang ${next.reranker?.model ?? draft.model}.`
          : "Đã chuyển reranker sang heuristic."
      );
    } catch (err) {
      toast.error(
        `Chưa lưu được reranker. ${errorMessage(err, "Máy chủ từ chối cập nhật cấu hình.")}`
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Section
      id="mdl-reranker"
      title="Xếp hạng lại (Reranker)"
      description="Sắp xếp lại các đoạn ứng viên theo mức liên quan trước khi đưa vào LLM."
      badge={
        <>
          <Zap size={13} /> Áp dụng từ lần tìm kiếm tiếp theo
        </>
      }
      footer={
        <SectionActions
          dirty={dirty}
          saving={saving}
          onReset={() => {
            setDraft(initial);
            setShowErrors(false);
          }}
          onSave={handleSave}
        />
      }
    >
      {reranker.enabled === false && (
        <div className="inline-alert is-warning mdl-alert">
          <AlertTriangle size={16} />
          <span>
            Reranker đang tắt nên lựa chọn bên dưới chưa được dùng.{" "}
            <a className="mdl-inline-link" href="#settings/config">
              Bật trong Cấu hình RAG <ArrowRight size={13} />
            </a>
          </span>
        </div>
      )}

      <div className="mdl-stack">
        <OptionGroup
          name="reranker-provider"
          legend="Cách xếp hạng"
          options={RERANKER_PROVIDERS}
          value={draft.provider}
          onChange={(provider) => setDraft((current) => ({ ...current, provider }))}
        />

        {usesModel && (
          <div ref={modelRef} className="mdl-reranker-model">
            <TextField
              id="reranker-model"
              field={{
                label: "Mô hình cross-encoder",
                required: true,
                placeholder: CROSS_ENCODER_SUGGESTIONS[0],
                suggestions: CROSS_ENCODER_SUGGESTIONS,
                hint: "Tên mô hình trên Hugging Face. Lần dùng đầu tiên máy chủ sẽ tải mô hình về; nếu không tải được, hệ thống tự quay về heuristic.",
              }}
              value={draft.model}
              onChange={(model) => setDraft((current) => ({ ...current, model }))}
              error={showErrors ? modelError : undefined}
            />
          </div>
        )}
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Thanh luồng xử lý
// ---------------------------------------------------------------------------

const STAGES = [
  { key: "embedding", label: "Nhúng văn bản", Icon: Binary },
  { key: "reranker", label: "Xếp hạng lại", Icon: ArrowDownUp },
  { key: "llm", label: "Sinh câu trả lời", Icon: MessageSquareText },
];

/** Tóm tắt khâu đang chạy trên máy chủ để hiện trên thẻ của thanh luồng xử lý. */
function stageSummaries(config) {
  const llm = config.llm ?? {};
  const reranker = config.reranker ?? {};
  const embedding = config.embedding ?? {};
  const llmProvider = normalizeLlmProvider(llm.provider);
  const embeddingProvider = (embedding.provider || "").toLowerCase();
  const rerankerIsModel = reranker.provider === "cross-encoder";

  return {
    embedding: {
      model: embedding.model || "—",
      meta: EMBEDDING_PROVIDER_NAMES[embeddingProvider] ?? (embeddingProvider || "—"),
      status:
        embeddingProvider === "openai" && !llm.openai_has_key
          ? { tone: "warn", Icon: AlertTriangle, text: "Thiếu API key" }
          : { tone: "muted", Icon: Lock, text: "Cố định khi chạy" },
    },
    reranker: {
      model: rerankerIsModel ? reranker.model || "—" : "Heuristic",
      meta: rerankerIsModel ? "Cross-Encoder" : "Vector + BM25 + từ khoá",
      status:
        reranker.enabled === false
          ? { tone: "warn", text: "Đang tắt" }
          : { tone: "ok", text: "Đang bật" },
    },
    llm: {
      model: llm.model || "—",
      meta: llmProviderName(llmProvider),
      status:
        KEY_FIELD[llmProvider].required && !llm[KEY_FIELD[llmProvider].hasKey]
          ? { tone: "warn", Icon: AlertTriangle, text: "Thiếu API key" }
          : { tone: "ok", Icon: Check, text: "Đã cấu hình" },
    },
  };
}

function Pipeline({ summaries, active, dirtyStages, onSelect }) {
  const tabRefs = useRef({});

  function handleKeyDown(event, index) {
    const last = STAGES.length - 1;
    let next = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = index === last ? 0 : index + 1;
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = index === 0 ? last : index - 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = last;
    if (next == null) return;
    event.preventDefault();
    const key = STAGES[next].key;
    onSelect(key);
    tabRefs.current[key]?.focus();
  }

  return (
    <div className="mdl-flow">
      <p className="mdl-flow-caption" id="mdl-flow-caption">
        Luồng xử lý một câu hỏi — chọn một khâu để cấu hình
      </p>
      <div className="mdl-pipeline" role="tablist" aria-labelledby="mdl-flow-caption">
        {STAGES.map(({ key, label, Icon }, index) => {
          const summary = summaries[key];
          const selected = active === key;
          const StatusIcon = summary.status.Icon;
          return (
            <React.Fragment key={key}>
              {index > 0 && (
                <span className="mdl-flow-arrow" aria-hidden="true">
                  <ChevronRight size={16} />
                </span>
              )}
              <button
                ref={(node) => {
                  tabRefs.current[key] = node;
                }}
                type="button"
                role="tab"
                id={`mdl-tab-${key}`}
                aria-selected={selected}
                aria-controls={`mdl-panel-${key}`}
                tabIndex={selected ? 0 : -1}
                className={`mdl-stage ${selected ? "is-active" : ""}`}
                onClick={() => onSelect(key)}
                onKeyDown={(event) => handleKeyDown(event, index)}
              >
                <span className="mdl-stage-top">
                  <span className="mdl-stage-icon" aria-hidden="true">
                    <Icon size={16} />
                  </span>
                  <span className="mdl-stage-step">Bước {index + 1}</span>
                  {dirtyStages[key] && (
                    <span className="mdl-stage-dirty">
                      <span aria-hidden="true" /> Chưa lưu
                    </span>
                  )}
                </span>
                <span className="mdl-stage-label">{label}</span>
                <span className="mdl-stage-model" title={summary.model}>
                  {summary.model}
                </span>
                <span className="mdl-stage-meta">{summary.meta}</span>
                <span className="mdl-stage-status">
                  <StatusPill tone={summary.status.tone}>
                    {StatusIcon && <StatusIcon size={12} />}
                    {summary.status.text}
                  </StatusPill>
                </span>
              </button>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Màn chính
// ---------------------------------------------------------------------------

export default function ModelsView() {
  const configQuery = useQuery({
    queryKey: queryKeys.config,
    queryFn: ({ signal }) => configApi.get({ signal }),
  });
  const config = configQuery.data ?? null;
  const loading = configQuery.isPending;
  const loadError = configQuery.error
    ? describeError(configQuery.error, {
        fallbackTitle: "Không đọc được cấu hình mô hình",
        fallbackDetail: "Máy chủ trả về lỗi khi đọc cấu hình.",
      })
    : null;
  const [activeStage, setActiveStage] = useState("llm");
  const [dirtyStages, setDirtyStages] = useState({});
  const onLlmDirty = useCallback(
    (dirty) => setDirtyStages((current) => (current.llm === dirty ? current : { ...current, llm: dirty })),
    []
  );
  const onRerankerDirty = useCallback(
    (dirty) =>
      setDirtyStages((current) => (current.reranker === dirty ? current : { ...current, reranker: dirty })),
    []
  );

  useEffect(() => {
    // Dọn dữ liệu của màn cũ: danh sách "nhà cung cấp đã thêm" chỉ từng tồn tại trên giao diện.
    try {
      localStorage.removeItem("ptit_added_providers");
    } catch {
      /* storage bị chặn — không có gì để dọn */
    }
  }, []);

  const llm = config?.llm ?? {};
  const reranker = config?.reranker ?? {};
  const encryptionEnabled = Boolean(config?.persistence?.secret_encryption_enabled);

  let body;
  if (loading && !config) {
    body = (
      <div className="model-mgmt-loading" aria-busy="true">
        <div className="model-mgmt-spinner" />
        <p>Đang đọc cấu hình mô hình...</p>
      </div>
    );
  } else if (loadError && !config) {
    body = (
      <div className="state-block is-error">
        <span className="state-icon">
          <AlertTriangle size={24} />
        </span>
        <h3>{loadError.title}</h3>
        <p>{loadError.detail} Màn này cần cấu hình thật của máy chủ trước khi cho phép thay đổi.</p>
        <button
          type="button"
          className="primary-btn"
          onClick={() => configQuery.refetch()}
          disabled={configQuery.isFetching}
        >
          {configQuery.isFetching ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
          Thử lại
        </button>
      </div>
    );
  } else {
    const panels = {
      embedding: <EmbeddingSection embedding={config.embedding ?? {}} openaiHasKey={Boolean(llm.openai_has_key)} />,
      reranker: <RerankerSection reranker={reranker} onDirtyChange={onRerankerDirty} />,
      llm: <LlmSection llm={llm} onDirtyChange={onLlmDirty} />,
    };
    body = (
      <>
        {!encryptionEnabled && (
          <div className="inline-alert is-warning mdl-alert" role="alert">
            <ShieldAlert size={16} />
            <span>
              Máy chủ chưa có <code>CONFIG_ENCRYPTION_KEY</code> hợp lệ nên sẽ từ chối lưu API key mới. Các thay
              đổi khác vẫn lưu bình thường.
            </span>
          </div>
        )}
        <Pipeline
          summaries={stageSummaries(config)}
          active={activeStage}
          dirtyStages={dirtyStages}
          onSelect={setActiveStage}
        />
        {/* Giữ cả ba bảng mounted để không mất bản nháp khi đổi khâu. */}
        {STAGES.map(({ key }) => (
          <div
            key={key}
            role="tabpanel"
            id={`mdl-panel-${key}`}
            aria-labelledby={`mdl-tab-${key}`}
            className="mdl-panel"
            hidden={activeStage !== key}
          >
            {panels[key]}
          </div>
        ))}
      </>
    );
  }

  return (
    <div className="models-page-wrapper">
      <div className="settings-subtabs-header mdl-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box red-gradient">
            <Cpu size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Mô hình AI</h2>
            <p className="config-main-desc">
              Mỗi khâu lưu riêng vào cơ sở dữ liệu và giữ nguyên khi backend khởi động lại; khâu chưa đổi dùng giá
              trị trong <code>.env</code>.
            </p>
          </div>
        </div>
        {config && (
          <span className={`mdl-persist ${encryptionEnabled ? "is-ok" : "is-warn"}`}>
            {encryptionEnabled ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
            {encryptionEnabled ? "API key được mã hoá khi lưu" : "Chưa bật mã hoá API key"}
          </span>
        )}
      </div>
      <div className="mdl-page">
        <div className="mdl-content">{body}</div>
      </div>
    </div>
  );
}
