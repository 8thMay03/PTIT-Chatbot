import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownUp,
  ArrowRight,
  Binary,
  Check,
  CheckCircle2,
  Cloud,
  Copy,
  Cpu,
  Eye,
  EyeOff,
  HardDrive,
  Info,
  ListOrdered,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Save,
  Server,
  Undo2,
  Zap,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { apiError } from "./lib/format";
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
    description: "Kết hợp điểm vector, BM25 và độ phủ từ khoá. Nhanh, không cần tải mô hình.",
    Icon: ListOrdered,
  },
  {
    key: "cross-encoder",
    name: "Cross-Encoder",
    description: "Mô hình chấm điểm từng cặp câu hỏi–đoạn, chạy cục bộ trên máy chủ. Chính xác hơn, chậm hơn.",
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

function StatusPill({ tone = "muted", children }) {
  return <span className={`mdl-pill is-${tone}`}>{children}</span>;
}

function Section({ id, icon, title, description, current, children, footer }) {
  return (
    <section className="mdl-card" aria-labelledby={`${id}-title`} id={id}>
      <header className="mdl-card-head">
        <span className="mdl-card-icon" aria-hidden="true">
          {icon}
        </span>
        <div className="mdl-card-heading">
          <h3 id={`${id}-title`}>{title}</h3>
          <p>{description}</p>
          {current && <div className="mdl-current">{current}</div>}
        </div>
      </header>
      <div className="mdl-card-body">{children}</div>
      {footer && <footer className="mdl-card-foot">{footer}</footer>}
    </section>
  );
}

function ChoiceGroup({ name, legend, options, value, onChange }) {
  return (
    <fieldset className="mdl-choice-group">
      <legend>{legend}</legend>
      <div className="mdl-choices">
        {options.map(({ key, name: label, description, Icon }) => (
          <label key={key} className={`mdl-choice ${value === key ? "is-selected" : ""}`}>
            <input
              type="radio"
              name={name}
              value={key}
              checked={value === key}
              onChange={() => onChange(key)}
            />
            <span className="mdl-choice-icon" aria-hidden="true">
              <Icon size={18} />
            </span>
            <span className="mdl-choice-text">
              <strong>{label}</strong>
              <span>{description}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function TextField({ id, field, value, onChange, error }) {
  const listId = field.suggestions ? `${id}-suggestions` : undefined;
  const hintId = `${id}-hint`;
  const describedBy = [error ? `${id}-error` : null, field.hint ? hintId : null].filter(Boolean).join(" ");
  return (
    <div className="mdl-field">
      <label htmlFor={id}>
        {field.label}
        {!field.required && <span className="mdl-optional">Tuỳ chọn</span>}
      </label>
      <input
        id={id}
        type="text"
        className={`mdl-input ${error ? "is-invalid" : ""}`}
        value={value}
        placeholder={field.placeholder}
        list={listId}
        spellCheck={false}
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {listId && (
        <datalist id={listId}>
          {field.suggestions.map((item) => (
            <option key={item} value={item} />
          ))}
        </datalist>
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
        <label htmlFor={id}>{label}</label>
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
        Khoá được gửi thẳng tới máy chủ, không lưu trong trình duyệt và không bao giờ hiển thị lại.
      </span>
    </div>
  );
}

function SectionActions({ dirty, saving, onReset, onSave, children }) {
  return (
    <>
      <span className="mdl-dirty" role="status">
        {dirty ? "Có thay đổi chưa lưu" : ""}
      </span>
      <div className="mdl-actions">
        {children}
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

async function putConfig(payload) {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(apiError(data, "Máy chủ từ chối cập nhật cấu hình."));
  return data;
}

function describeSaveError(err) {
  return err instanceof TypeError ? "Không kết nối được máy chủ." : err.message;
}

// ---------------------------------------------------------------------------
// Mục LLM
// ---------------------------------------------------------------------------

function LlmSection({ llm, onSaved }) {
  const toast = useToast();
  const initial = useMemo(() => llmDraftFromConfig(llm), [llm]);
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const bodyRef = useRef(null);

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
    bodyRef.current?.querySelector(`#llm-${provider}-${first?.name}`)?.focus();
    return false;
  }

  async function handleTest() {
    if (!ensureValid()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const response = await fetch(`${API_BASE_URL}/config/test-llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildTestPayload(draft)),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(data, "Máy chủ từ chối yêu cầu kiểm tra."));
      setTestResult(data);
    } catch (err) {
      setTestResult({ success: false, message: describeSaveError(err) });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    if (!ensureValid()) return;
    setSaving(true);
    try {
      const next = await putConfig(buildLlmPayload(draft, initial));
      onSaved(next);
      toast.success(`Chatbot đã chuyển sang ${next.llm?.model ?? "mô hình mới"} · ${llmProviderName(provider)}.`);
    } catch (err) {
      toast.error(`Chưa lưu được mô hình LLM. ${describeSaveError(err)}`);
    } finally {
      setSaving(false);
    }
  }

  const currentProvider = normalizeLlmProvider(llm.provider);
  const currentHasKey = Boolean(llm[KEY_FIELD[currentProvider].hasKey]);

  return (
    <Section
      id="mdl-llm"
      icon={<MessageSquareText size={18} />}
      title="Sinh câu trả lời (LLM)"
      description="Mô hình đọc các đoạn tài liệu tìm được và viết câu trả lời cho sinh viên. Thay đổi có hiệu lực từ câu hỏi tiếp theo."
      current={
        <>
          <span>
            Đang dùng <strong>{llm.model || "—"}</strong> · {llmProviderName(currentProvider)}
          </span>
          {KEY_FIELD[currentProvider].required && !currentHasKey && (
            <StatusPill tone="warn">
              <AlertTriangle size={12} /> Chưa có API key — chatbot sẽ không trả lời được
            </StatusPill>
          )}
        </>
      }
      footer={
        <SectionActions dirty={dirty} saving={saving} onReset={resetDraft} onSave={handleSave}>
          <button type="button" className="ghost-btn" onClick={handleTest} disabled={testing || saving}>
            {testing ? <Loader2 size={15} className="spin" /> : <Zap size={15} />}
            {testing ? "Đang kiểm tra..." : "Kiểm tra kết nối"}
          </button>
        </SectionActions>
      }
    >
      <div ref={bodyRef} className="mdl-stack">
        <ChoiceGroup
          name="llm-provider"
          legend="Nhà cung cấp"
          options={LLM_PROVIDERS}
          value={provider}
          onChange={selectProvider}
        />

        {provider === "openai_compatible" && (
          <div className="mdl-presets" role="group" aria-label="Điền nhanh địa chỉ máy chủ">
            <span>Điền nhanh:</span>
            {COMPATIBLE_PRESETS.map((preset) => (
              <button
                key={preset.key}
                type="button"
                className="mdl-preset"
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
      icon={<Binary size={18} />}
      title="Nhúng văn bản (Embedding)"
      description="Mô hình biến câu hỏi và các đoạn tài liệu thành vector để tìm kiếm theo ngữ nghĩa."
      current={
        <>
          <span>
            Đang dùng <strong>{embedding.model || "—"}</strong> ·{" "}
            {EMBEDDING_PROVIDER_NAMES[provider] ?? (provider || "—")}
          </span>
          {provider === "openai" && !openaiHasKey && (
            <StatusPill tone="warn">
              <AlertTriangle size={12} /> Chưa có API key OpenAI
            </StatusPill>
          )}
        </>
      }
    >
      <div className="mdl-stack">
        <div className="inline-alert is-info">
          <Info size={16} />
          <span>
            Mô hình nhúng được nạp một lần khi backend khởi động và quyết định số chiều của mọi vector đã lưu
            trong kho, nên không đổi được tại đây.
            {provider === "openai" && " Mô hình này dùng chung API key OpenAI ở mục LLM."}
          </span>
        </div>

        <div className="mdl-howto">
          <h4>Muốn đổi mô hình nhúng</h4>
          <ol>
            <li>
              Sửa tệp <code>.env</code> của backend:
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
              Đặt <code>VECTOR_DIM</code> bằng số chiều của mô hình mới.
            </li>
            <li>Khởi động lại backend.</li>
            <li>
              Vào <strong>Dataset</strong> → <strong>Nạp lại toàn bộ</strong> để tạo lại vector cho mọi tài liệu.
            </li>
          </ol>
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Mục Reranker
// ---------------------------------------------------------------------------

function RerankerSection({ reranker, onSaved }) {
  const toast = useToast();
  const initial = useMemo(() => rerankerDraftFromConfig(reranker), [reranker]);
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
      const next = await putConfig(payload);
      onSaved(next);
      toast.success(
        usesModel
          ? `Đã chuyển reranker sang ${next.reranker?.model ?? draft.model}.`
          : "Đã chuyển reranker sang heuristic."
      );
    } catch (err) {
      toast.error(`Chưa lưu được reranker. ${describeSaveError(err)}`);
    } finally {
      setSaving(false);
    }
  }

  const currentIsModel = reranker.provider === "cross-encoder";

  return (
    <Section
      id="mdl-reranker"
      icon={<ArrowDownUp size={18} />}
      title="Xếp hạng lại (Reranker)"
      description="Sắp xếp lại các đoạn ứng viên theo mức liên quan trước khi đưa vào LLM."
      current={
        <>
          <span>
            Đang dùng <strong>{currentIsModel ? reranker.model : "Heuristic"}</strong>
            {currentIsModel && " · Cross-Encoder"}
          </span>
          {reranker.enabled === false ? (
            <StatusPill tone="warn">Đang tắt</StatusPill>
          ) : (
            <StatusPill tone="ok">Đang bật</StatusPill>
          )}
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
      <div className="mdl-stack">
        {reranker.enabled === false && (
          <div className="inline-alert is-warning">
            <AlertTriangle size={16} />
            <span>
              Reranker đang tắt nên lựa chọn bên dưới chưa được dùng.{" "}
              <a className="mdl-inline-link" href="#settings/config">
                Bật trong Cấu hình RAG <ArrowRight size={13} />
              </a>
            </span>
          </div>
        )}

        <ChoiceGroup
          name="reranker-provider"
          legend="Cách xếp hạng"
          options={RERANKER_PROVIDERS}
          value={draft.provider}
          onChange={(provider) => setDraft((current) => ({ ...current, provider }))}
        />

        {usesModel && (
          <div ref={modelRef} className="mdl-grid">
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
// Màn chính
// ---------------------------------------------------------------------------

export default function ModelsView() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const response = await fetch(`${API_BASE_URL}/config`);
      if (!response.ok) throw new Error("Máy chủ trả về lỗi khi đọc cấu hình.");
      setConfig(await response.json());
    } catch (err) {
      setLoadError(err instanceof TypeError ? "Không kết nối được máy chủ." : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Dọn dữ liệu của màn cũ: danh sách "nhà cung cấp đã thêm" chỉ từng tồn tại trên giao diện.
    try {
      localStorage.removeItem("ptit_added_providers");
    } catch {
      /* storage bị chặn — không có gì để dọn */
    }
  }, [load]);

  // Mỗi mục chỉ nhận phần cấu hình của mình; giữ tham chiếu cũ khi nội dung không
  // đổi để lưu ở mục này không xoá bản nháp đang sửa ở mục kia.
  const llmKey = JSON.stringify(config?.llm ?? null);
  const rerankerKey = JSON.stringify(config?.reranker ?? null);
  const llm = useMemo(() => JSON.parse(llmKey) ?? {}, [llmKey]);
  const reranker = useMemo(() => JSON.parse(rerankerKey) ?? {}, [rerankerKey]);

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
        <h3>Không đọc được cấu hình mô hình</h3>
        <p>{loadError} Màn này cần cấu hình thật của máy chủ trước khi cho phép thay đổi.</p>
        <button type="button" className="primary-btn" onClick={load} disabled={loading}>
          {loading ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
          Thử lại
        </button>
      </div>
    );
  } else {
    body = (
      <>
        <div className="inline-alert is-info">
          <HardDrive size={16} />
          <span>
            Thay đổi ở đây áp dụng ngay cho máy chủ đang chạy nhưng không ghi vào tệp <code>.env</code>. Khi
            khởi động lại backend, cấu hình quay về giá trị trong <code>.env</code>.
          </span>
        </div>
        <LlmSection llm={llm} onSaved={setConfig} />
        <RerankerSection reranker={reranker} onSaved={setConfig} />
        <EmbeddingSection embedding={config.embedding ?? {}} openaiHasKey={Boolean(llm.openai_has_key)} />
      </>
    );
  }

  return (
    <div className="models-page-wrapper">
      <div className="settings-subtabs-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box red-gradient">
            <Cpu size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Mô hình AI</h2>
            <p className="config-main-desc">
              Chọn mô hình cho từng khâu của hệ thống hỏi đáp: sinh câu trả lời, xếp hạng lại và nhúng văn bản.
            </p>
          </div>
        </div>
      </div>
      <div className="mdl-page">
        <div className="mdl-content">{body}</div>
      </div>
    </div>
  );
}
