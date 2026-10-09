import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Eye,
  EyeOff,
  Info,
  Key,
  Search,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import Modal from "./components/Modal";
import { useToast } from "./components/Toast";

// =============================================================================
// Provider Logos (SVGs & Brand Marks)
// =============================================================================
function ProviderLogo({ providerId, size = 20, className = "" }) {
  const p = (providerId || "").toLowerCase();

  if (p.includes("openai")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="currentColor"
        className={className}
      >
        <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.475 4.475 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1683a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4947zm-9.66-4.996a4.47 4.47 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1402-2.517zm-1.808-9.4582a4.4607 4.4607 0 0 1 2.342-1.9729v.1656l-.0047 5.5164a.79.79 0 0 0 .3927.6813l5.8429 3.3686-2.02 1.1682a.0757.0757 0 0 1-.071 0l-4.8304-2.7913a4.4944 4.4944 0 0 1-1.6515-6.1359zm15.0845-2.054a.7854.7854 0 0 0-.7807 0l-5.8428 3.3685V6.977a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.4944 4.4851 4.4703 4.4703 0 0 1-.0047.5284l-.142-.0852-4.6344-2.6599zm2.4578 4.0984a4.4703 4.4703 0 0 1-.5347 3.0137l-.142-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685V10.743a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.1402 2.517 4.4703 4.4703 0 0 1 .0327.3995zm-8.8136 2.054a.79.79 0 0 0-.3927-.6813L8.29 8.083l2.02-1.1682a.0757.0757 0 0 1 .071 0l4.8304 2.7913a4.4944 4.4944 0 0 1 1.6515 6.1359 4.4607 4.4607 0 0 1-2.342 1.9729v-.1656l.0047-5.5164zm-1.0268.5916l2.3948 1.3824-2.3948 1.3824-2.3948-1.3824 2.3948-1.3824z" />
      </svg>
    );
  }

  if (p.includes("cohere")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="7" cy="15" r="5" fill="#39594D" />
        <circle cx="15" cy="7" r="5" fill="#D1345B" />
        <circle cx="17" cy="16" r="4.5" fill="#F8A055" />
      </svg>
    );
  }

  if (p.includes("gemini") || p.includes("google")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path
          d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z"
          fill="url(#gemini-grad-mod)"
        />
        <defs>
          <linearGradient id="gemini-grad-mod" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
            <stop stopColor="#4285F4" />
            <stop offset="0.33" stopColor="#9B72CB" />
            <stop offset="0.66" stopColor="#D96570" />
            <stop offset="1" stopColor="#F4B400" />
          </linearGradient>
        </defs>
      </svg>
    );
  }

  if (p.includes("tongyi") || p.includes("qwen")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path
          d="M12 3L20 8V16L12 21L4 16V8L12 3Z"
          fill="#6366F1"
          stroke="#4F46E5"
          strokeWidth="1.5"
        />
        <path d="M12 3V21M4 8L20 16M4 16L20 8" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.6" />
      </svg>
    );
  }

  if (p.includes("ollama") || p.includes("local")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 16.93c-3.96-.48-7-3.86-7-7.93 0-.62.08-1.22.21-1.79L9 15v1c0 1.1.9 2 2 2v.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
      </svg>
    );
  }

  return <Cpu size={size} className={className} />;
}

// =============================================================================
// Available Providers Metadata Catalog
// =============================================================================
const AVAILABLE_PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    tags: ["LLM", "Embedding", "TTS", "ASR"],
    models: [
      { id: "gpt-4o-mini", name: "gpt-4o-mini", type: "LLM" },
      { id: "gpt-4o", name: "gpt-4o", type: "LLM" },
      { id: "gpt-4.1-mini", name: "gpt-4.1-mini", type: "LLM" },
      { id: "text-embedding-3-small", name: "text-embedding-3-small", type: "Embedding" },
      { id: "text-embedding-3-large", name: "text-embedding-3-large", type: "Embedding" },
      { id: "tts-1", name: "tts-1", type: "TTS" },
      { id: "whisper-1", name: "whisper-1", type: "ASR" },
    ],
  },
  {
    id: "gemini",
    name: "Gemini",
    tags: ["LLM", "Embedding", "VLM"],
    models: [
      { id: "gemini-1.5-flash", name: "gemini-1.5-flash", type: "LLM" },
      { id: "gemini-1.5-pro", name: "gemini-1.5-pro", type: "LLM" },
      { id: "gemini-2.0-flash", name: "gemini-2.0-flash", type: "LLM" },
      { id: "text-embedding-004", name: "text-embedding-004", type: "Embedding" },
      { id: "gemini-1.5-flash-vlm", name: "gemini-1.5-flash (Vision)", type: "VLM" },
    ],
  },
  {
    id: "tongyi",
    name: "Qwen (Tongyi-Qianwen)",
    tags: ["LLM", "Embedding", "Rerank", "TTS", "ASR", "VLM", "OCR"],
    models: [
      { id: "qwen-max", name: "qwen-max", type: "LLM" },
      { id: "qwen-plus", name: "qwen-plus", type: "LLM" },
      { id: "qwen-turbo", name: "qwen-turbo", type: "LLM" },
      { id: "text-embedding-v3", name: "text-embedding-v3", type: "Embedding" },
      { id: "gte-rerank-hybrid", name: "gte-rerank-hybrid", type: "Rerank" },
      { id: "qwen-vl-max", name: "qwen-vl-max", type: "VLM" },
      { id: "cosy-voice-v1", name: "cosy-voice-v1", type: "TTS" },
      { id: "sense-voice-v1", name: "sense-voice-v1", type: "ASR" },
    ],
  },
  {
    id: "cohere",
    name: "Cohere",
    tags: ["LLM", "Embedding", "Rerank", "ASR"],
    models: [
      { id: "command-r-plus", name: "command-r-plus", type: "LLM" },
      { id: "command-r", name: "command-r", type: "LLM" },
      { id: "embed-multilingual-v3.0", name: "embed-multilingual-v3.0", type: "Embedding" },
      { id: "embed-english-v3.0", name: "embed-english-v3.0", type: "Embedding" },
      { id: "rerank-multilingual-v3.0", name: "rerank-multilingual-v3.0", type: "Rerank" },
      { id: "rerank-english-v3.0", name: "rerank-english-v3.0", type: "Rerank" },
    ],
  },
  {
    id: "ollama",
    name: "Ollama / Local AI",
    tags: ["LLM", "Embedding", "Rerank"],
    models: [
      { id: "qwen2.5:7b", name: "qwen2.5:7b", type: "LLM" },
      { id: "llama3.2:3b", name: "llama3.2:3b", type: "LLM" },
      { id: "nomic-embed-text", name: "nomic-embed-text", type: "Embedding" },
      { id: "bge-m3", name: "bge-m3", type: "Embedding" },
      { id: "heuristic", name: "heuristic (Lexical + BM25)", type: "Rerank" },
    ],
  },
];

// Không seed dữ liệu mẫu: bản trước cài sẵn hai nhà cung cấp giả kèm API key giả
// ("sk-proj-••••89ab", tên "test"/"test111") và ghi thẳng vào localStorage, khiến
// người dùng tưởng hệ thống đã được cấu hình sẵn.
const INITIAL_ADDED_PROVIDERS = [];

const SLOTS = [
  { key: "LLM", label: "LLM", required: true, tooltip: "Mô hình ngôn ngữ sinh câu trả lời chính (GPT-4o, Claude, Gemini...)" },
  { key: "Embedding", label: "Embedding", required: false, tooltip: "Mô hình chuyển văn bản thành vector nhúng ngữ nghĩa (Cohere, OpenAI, BGE...)" },
  { key: "VLM", label: "VLM", required: false, tooltip: "Visual Language Model xử lý hình ảnh và tài liệu biểu đồ (GPT-4o Vision, Gemini Flash...)" },
  { key: "ASR", label: "ASR", required: false, tooltip: "Automatic Speech Recognition nhận dạng giọng nói sinh viên (Whisper...)" },
  { key: "Rerank", label: "Rerank", required: false, tooltip: "Mô hình tái xếp hạng độ liên quan văn bản (Cohere Rerank, Cross-Encoder...)" },
  { key: "TTS", label: "TTS", required: false, tooltip: "Text-to-Speech chuyển đổi câu trả lời thành giọng đọc" },
];

export default function ModelsView() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [pendingDeleteProvider, setPendingDeleteProvider] = useState(null);

  // Added providers list (saved to localStorage & backend)
  const [addedProviders, setAddedProviders] = useState(() => {
    try {
      const saved = localStorage.getItem("ptit_added_providers");
      if (saved) return JSON.parse(saved);
    } catch (e) {
      // ignore
    }
    return INITIAL_ADDED_PROVIDERS;
  });

  const [expandedProviderIds, setExpandedProviderIds] = useState({});

  // Trạng thái ban đầu là RỖNG; giá trị thật được đọc từ GET /api/config bên dưới.
  const [defaultModels, setDefaultModels] = useState({
    LLM: null,
    Embedding: null,
    VLM: null,
    ASR: null,
    Rerank: null,
    TTS: null,
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");

  const [activeDropdownSlot, setActiveDropdownSlot] = useState(null);
  const dropdownRef = useRef(null);

  const [configModalProvider, setConfigModalProvider] = useState(null);
  const [configForm, setConfigForm] = useState({
    instanceName: "",
    apiKey: "",
    baseUrl: "",
    selectedModelIds: [],
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // API key KHÔNG được ghi xuống localStorage: nó nằm nguyên văn trong ổ đĩa và
  // mọi script chạy trên trang đều đọc được. Chỉ lưu phần đã che cùng metadata.
  useEffect(() => {
    try {
      const safe = addedProviders.map(({ apiKey, ...rest }) => rest);
      localStorage.setItem("ptit_added_providers", JSON.stringify(safe));
    } catch (e) {
      // Storage bị chặn — cấu hình vẫn dùng được trong phiên hiện tại.
    }
  }, [addedProviders]);

  useEffect(() => {
    fetchBackendConfig();
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdownSlot(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function fetchBackendConfig() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config`);
      if (!res.ok) throw new Error("Không thể tải cấu hình từ máy chủ");
      const data = await res.json();

      if (data.llm) {
        if (data.llm.openai_model || data.llm.model) {
          const m = data.llm.openai_model || data.llm.model;
          const p = data.llm.provider || "openai";
          setDefaultModels((prev) => ({
            ...prev,
            LLM: {
              modelId: m,
              providerId: p,
              instanceName: "Cấu hình máy chủ",
            },
          }));
        }
      }

      if (data.embedding) {
        if (data.embedding.model) {
          setDefaultModels((prev) => ({
            ...prev,
            Embedding: {
              modelId: data.embedding.model,
              providerId: data.embedding.provider || "unknown",
              instanceName: "Cấu hình máy chủ",
            },
          }));
        }
      }

      if (data.reranker) {
        if (data.reranker.model) {
          setDefaultModels((prev) => ({
            ...prev,
            Rerank: {
              modelId: data.reranker.model,
              providerId: data.reranker.provider || "unknown",
              instanceName: "Cấu hình máy chủ",
            },
          }));
        }
      }
    } catch (err) {
      // Bản trước chỉ console.warn: giao diện hiện danh sách trống như thể máy chủ
      // chưa cấu hình gì, trong khi thực ra là không đọc được.
      setLoadError(
        err instanceof TypeError
          ? "Không kết nối được máy chủ. Chưa đọc được mô hình đang dùng."
          : err.message || "Không đọc được cấu hình mô hình từ máy chủ."
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleExpandProvider(id) {
    setExpandedProviderIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  }

  function confirmDeleteProvider() {
    if (!pendingDeleteProvider) return;
    const { id, instanceName } = pendingDeleteProvider;
    setAddedProviders((prev) => prev.filter((p) => p.id !== id));
    setPendingDeleteProvider(null);
    toast.success(`Đã xóa cấu hình “${instanceName}”.`);
  }

  function handleOpenConfigModal(provider) {
    const defaultBases = {
      openai: "https://api.openai.com/v1",
      tongyi: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      qwen: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      ollama: "http://localhost:11434/v1",
    };

    setConfigModalProvider(provider);
    setConfigForm({
      instanceName: `${provider.id}_${Math.floor(100 + Math.random() * 900)}`,
      apiKey: "",
      baseUrl: defaultBases[provider.id] || "",
      selectedModelIds: provider.models.map((m) => m.id),
    });
    setTestResult(null);
    setShowApiKey(false);
  }

  async function handleTestConnection() {
    if (!configModalProvider) return;
    setTestingConnection(true);
    setTestResult(null);
    try {
      const payload = {
        provider: configModalProvider.id,
        model: configForm.selectedModelIds[0] || null,
        api_key: configForm.apiKey || null,
        base_url: configForm.baseUrl || null,
      };

      const res = await fetch(`${API_BASE_URL}/config/test-llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({
        success: false,
        message: `Lỗi kết nối: ${err.message}`,
      });
    } finally {
      setTestingConnection(false);
    }
  }

  function handleSaveProvider() {
    if (!configModalProvider) return;
    const name = configForm.instanceName.trim() || configModalProvider.name;
    const maskedKey = configForm.apiKey
      ? `${configForm.apiKey.slice(0, 4)}••••••••${configForm.apiKey.slice(-4)}`
      : "••••••••";

    const newEntry = {
      id: `added-${configModalProvider.id}-${Date.now()}`,
      providerId: configModalProvider.id,
      providerName: configModalProvider.name,
      instanceName: name,
      apiKey: configForm.apiKey,
      apiKeyMasked: maskedKey,
      baseUrl: configForm.baseUrl,
      models: configModalProvider.models.filter((m) =>
        configForm.selectedModelIds.includes(m.id)
      ),
    };

    setAddedProviders((prev) => [newEntry, ...prev]);
    setConfigModalProvider(null);
    toast.success(`Đã thêm cấu hình thành công: "${name}"`);
  }

  async function handleSelectDefaultModel(slotKey, model, provider, instanceName) {
    const nextDefaults = {
      ...defaultModels,
      [slotKey]: {
        modelId: model.id,
        providerId: provider.id || provider.providerId,
        instanceName: instanceName || "default",
      },
    };
    setDefaultModels(nextDefaults);
    setActiveDropdownSlot(null);

    try {
      const payload = {};
      if (slotKey === "LLM") {
        payload.llm = {
          provider: provider.providerId || provider.id,
          openai_model: model.id,
          model: model.id,
        };
        if (provider.apiKey) payload.llm.api_key = provider.apiKey;
        if (provider.baseUrl) payload.llm.base_url = provider.baseUrl;
      } else if (slotKey === "Embedding") {
        payload.embedding = {
          provider: provider.providerId || provider.id,
          model: model.id,
        };
      } else if (slotKey === "Rerank") {
        payload.reranker = {
          enabled: true,
          provider: (provider.providerId || provider.id).includes("cohere") ? "cohere" : "cross-encoder",
          model: model.id,
        };
      }

      const res = await fetch(`${API_BASE_URL}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Máy chủ từ chối cập nhật.");

      toast.success(`Đã đặt ${model.name} làm mô hình ${slotKey} mặc định.`);
    } catch (e) {
      // Lựa chọn chỉ nằm trên giao diện nếu máy chủ không nhận — phải nói rõ,
      // nếu không người dùng tưởng đã đổi được mô hình.
      setDefaultModels(defaultModels);
      toast.error(
        `Không lưu được lựa chọn ${slotKey} lên máy chủ. ${
          e instanceof TypeError ? "Không kết nối được máy chủ." : e.message
        }`
      );
    }
  }

  function handleClearDefaultModel(slotKey, e) {
    e.stopPropagation();
    setDefaultModels((prev) => ({
      ...prev,
      [slotKey]: null,
    }));
    toast.success(`Đã hủy chọn mặc định cho ${slotKey}`);
  }

  const filteredProviders = useMemo(() => {
    return AVAILABLE_PROVIDERS.filter((provider) => {
      if (activeCategory !== "All") {
        if (!provider.tags.includes(activeCategory)) return false;
      }
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const matchName = provider.name.toLowerCase().includes(q);
      const matchTag = provider.tags.some((t) => t.toLowerCase().includes(q));
      const matchModel = provider.models.some((m) => m.name.toLowerCase().includes(q));
      return matchName || matchTag || matchModel;
    });
  }, [searchQuery, activeCategory]);

  const categoryCounts = useMemo(() => {
    const counts = { All: AVAILABLE_PROVIDERS.length };
    ["LLM", "Embedding", "Rerank", "TTS", "ASR", "VLM", "OCR"].forEach((cat) => {
      counts[cat] = AVAILABLE_PROVIDERS.filter((provider) => provider.tags.includes(cat)).length;
    });
    return counts;
  }, []);

  function getCandidateModelsForSlot(slotKey) {
    const list = [];
    addedProviders.forEach((ap) => {
      const matching = ap.models.filter((m) => m.type === slotKey || slotKey === "LLM");
      if (matching.length > 0) {
        list.push({
          providerId: ap.providerId,
          providerName: ap.providerName,
          instanceName: ap.instanceName,
          models: matching,
        });
      }
    });
    if (list.length === 0) {
      AVAILABLE_PROVIDERS.forEach((p) => {
        const matching = p.models.filter((m) => m.type === slotKey || (slotKey === "LLM" && m.type === "LLM"));
        if (matching.length > 0) {
          list.push({
            providerId: p.id,
            providerName: p.name,
            instanceName: "catalog",
            models: matching,
          });
        }
      });
    }
    return list;
  }

  if (loading) {
    return (
      <div className="model-mgmt-loading">
        <div className="model-mgmt-spinner" />
        <p>Đang tải danh sách mô hình...</p>
      </div>
    );
  }

  return (
    <div className="models-page-wrapper">
      {/* Header Bar */}
      <div className="settings-subtabs-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box red-gradient">
            <Cpu size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Quản lý Nhà cung cấp & Mô hình AI</h2>
            <p className="config-main-desc">
              Lựa chọn mô hình mặc định cho LLM, Embedding, Rerank, VLM, ASR, TTS và thêm các kết nối API Key mới.
            </p>
          </div>
        </div>
      </div>

      {loadError && (
        <div className="inline-alert is-warning" role="alert" style={{ margin: "0 24px 16px" }}>
          <AlertTriangle size={16} />
          <span>{loadError}</span>
        </div>
      )}

      <div className="model-mgmt-page">
        <div className="model-mgmt-layout">
          {/* LEFT COLUMN: Set Default Models & Added Models */}
          <div className="model-mgmt-left">
            {/* SECTION 1: SET DEFAULT MODELS */}
            <div className="mgmt-section-header">
              <h2 className="mgmt-title">Set default models</h2>
              <p className="mgmt-subtitle">Lựa chọn mô hình mặc định cho từng loại tác vụ AI</p>
            </div>

            <div className="default-models-card">
              {SLOTS.map((slot) => {
                const selected = defaultModels[slot.key];
                const isDropdownOpen = activeDropdownSlot === slot.key;

                return (
                  <div key={slot.key} className="default-model-row">
                    <div className="slot-label-col">
                      <span className="slot-name">
                        {slot.required && <span className="slot-required">*</span>}
                        {slot.label}
                      </span>
                      <span className="slot-info-icon" title={slot.tooltip}>
                        <Info size={13} />
                      </span>
                    </div>

                    <div className="slot-input-col" ref={isDropdownOpen ? dropdownRef : null}>
                      <div
                        className={`slot-select-box ${selected ? "has-value" : "is-empty"}`}
                        onClick={() => setActiveDropdownSlot(isDropdownOpen ? null : slot.key)}
                      >
                        {selected ? (
                          <div className="selected-model-pill">
                            <div className="selected-provider-icon">
                              <ProviderLogo providerId={selected.providerId} size={17} />
                            </div>
                            <span className="selected-model-name">{selected.modelId}</span>
                            {selected.instanceName && (
                              <span className="selected-instance-tag">{selected.instanceName}</span>
                            )}
                          </div>
                        ) : (
                          <span className="slot-placeholder">Select {slot.label} model...</span>
                        )}

                        <div className="slot-actions-right">
                          {selected && !slot.required ? (
                            <button
                              type="button"
                              className="btn-slot-clear"
                              onClick={(e) => handleClearDefaultModel(slot.key, e)}
                              title="Xóa lựa chọn"
                            >
                              <X size={15} />
                            </button>
                          ) : (
                            <ChevronDown size={16} className={`chevron-slot ${isDropdownOpen ? "open" : ""}`} />
                          )}
                        </div>
                      </div>

                      {isDropdownOpen && (
                        <div className="slot-dropdown-popover">
                          <div className="popover-header">
                            <span>Chọn {slot.label} Model</span>
                            <button
                              type="button"
                              className="popover-close"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveDropdownSlot(null);
                              }}
                            >
                              <X size={14} />
                            </button>
                          </div>

                          <div className="popover-list">
                            {getCandidateModelsForSlot(slot.key).map((group, gIdx) => (
                              <div key={gIdx} className="popover-group">
                                <div className="popover-group-title">
                                  <ProviderLogo providerId={group.providerId} size={14} />
                                  <span>{group.providerName}</span>
                                  {group.instanceName !== "catalog" && (
                                    <span className="popover-inst-tag">{group.instanceName}</span>
                                  )}
                                </div>
                                {group.models.map((m) => {
                                  const isCurrent =
                                    selected?.modelId === m.id &&
                                    selected?.providerId === group.providerId;
                                  return (
                                    <button
                                      key={m.id}
                                      type="button"
                                      className={`popover-item ${isCurrent ? "active" : ""}`}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleSelectDefaultModel(
                                          slot.key,
                                          m,
                                          group,
                                          group.instanceName
                                        );
                                      }}
                                    >
                                      <div className="popover-item-left">
                                        <ProviderLogo providerId={group.providerId} size={16} />
                                        <span className="popover-model-name">{m.name}</span>
                                        <span className="popover-type-badge">{m.type}</span>
                                      </div>
                                      {isCurrent && <Check size={15} className="popover-check" />}
                                    </button>
                                  );
                                })}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* SECTION 2: ADDED MODELS */}
            <div className="mgmt-section-header" style={{ marginTop: "32px" }}>
              <h2 className="mgmt-title">Added models</h2>
              <p className="mgmt-subtitle">Các nhà cung cấp đã được cấu hình và sẵn sàng phục vụ</p>
            </div>

            <div className="added-models-list">
              {addedProviders.length === 0 ? (
                <div className="empty-added-box">
                  <p>Chưa có nhà cung cấp nào được thêm. Nhấp vào danh sách bên phải để thêm cấu hình.</p>
                </div>
              ) : (
                addedProviders.map((provider) => {
                  const isExpanded = Boolean(expandedProviderIds[provider.id]);

                  return (
                    <div key={provider.id} className="added-provider-card">
                      <div className="added-card-header">
                        <div className="added-provider-info">
                          <div className="added-provider-icon">
                            <ProviderLogo providerId={provider.providerId} size={22} />
                          </div>
                          <span className="added-provider-title">{provider.providerName}</span>
                        </div>
                      </div>

                      <div className="added-card-row">
                        <div className="added-instance-name">
                          <span>{provider.instanceName}</span>
                        </div>

                        <div className="added-card-actions">
                          <button
                            type="button"
                            className="btn-view-models"
                            onClick={() => toggleExpandProvider(provider.id)}
                          >
                            <span>View models</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>

                          <button
                            type="button"
                            className="btn-delete-provider"
                            onClick={() => setPendingDeleteProvider(provider)}
                            title="Xóa cấu hình"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="added-models-expanded">
                          <div className="models-table-header">
                            <span>Tên mô hình</span>
                            <span>Loại năng lực</span>
                          </div>
                          <div className="models-table-body">
                            {provider.models.map((m) => (
                              <div key={m.id} className="expanded-model-item">
                                <div className="exp-model-left">
                                  <ProviderLogo providerId={provider.providerId} size={15} />
                                  <span className="exp-model-name">{m.name}</span>
                                </div>
                                <span className="exp-model-badge">{m.type}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: Available Models Catalog */}
          <div className="model-mgmt-right">
            <div className="mgmt-section-header">
              <h2 className="mgmt-title">Available models</h2>
              <p className="mgmt-subtitle">Khám phá và thêm kết nối nhà cung cấp AI mới</p>
            </div>

            <div className="available-search-box">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search provider or model..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery("")}
                >
                  <X size={14} />
                </button>
              )}
            </div>

            <div className="category-filter-bar">
              {["All", "LLM", "Embedding", "Rerank", "TTS", "ASR", "VLM", "OCR"].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`filter-chip ${activeCategory === cat ? "active" : ""}`}
                  onClick={() => setActiveCategory(cat)}
                >
                  <span>{cat}</span>
                  <span className="chip-count">{categoryCounts[cat] || 0}</span>
                </button>
              ))}
            </div>

            <div className="available-providers-list">
              {filteredProviders.map((provider) => (
                <div
                  key={provider.id}
                  className="available-provider-card"
                  onClick={() => handleOpenConfigModal(provider)}
                >
                  <div className="avail-card-top">
                    <div className="avail-card-brand">
                      <div className="avail-card-logo">
                        <ProviderLogo providerId={provider.id} size={22} />
                      </div>
                      <span className="avail-card-name">{provider.name}</span>
                      <ArrowUpRight size={16} className="external-arrow" />
                    </div>
                  </div>

                  <div className="avail-card-tags">
                    {provider.tags.map((tag) => (
                      <span key={tag} className="tag-pill">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* MODAL: Configure & Add Provider */}
      {configModalProvider && (
        <div className="modal-backdrop" onClick={() => setConfigModalProvider(null)}>
          <div className="config-provider-modal" onClick={(e) => e.stopPropagation()}>
            <div className="config-modal-header">
              <div className="modal-header-left">
                <div className="modal-provider-icon">
                  <ProviderLogo providerId={configModalProvider.id} size={24} />
                </div>
                <div>
                  <h3>Cấu hình {configModalProvider.name}</h3>
                  <p>Thiết lập API Key, Base URL và các mô hình hỗ trợ.</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setConfigModalProvider(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="config-modal-body">
              <div className="form-group">
                <label className="form-label">Tên cấu hình (Tag / Alias)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. test, test111, production"
                  value={configForm.instanceName}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, instanceName: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <Key size={14} /> Khóa API Key
                </label>
                <div className="input-password-wrapper">
                  <input
                    type={showApiKey ? "text" : "password"}
                    className="form-input"
                    placeholder="Nhập API Key..."
                    value={configForm.apiKey}
                    onChange={(e) =>
                      setConfigForm({ ...configForm, apiKey: e.target.value })
                    }
                  />
                  <button
                    type="button"
                    className="btn-toggle-eye"
                    onClick={() => setShowApiKey(!showApiKey)}
                    aria-label={showApiKey ? "Ẩn API key" : "Hiện API key"}
                    aria-pressed={showApiKey}
                  >
                    {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <p className="form-help">
                  Khóa chỉ được giữ trong phiên làm việc này và gửi tới máy chủ khi bạn chọn mô hình
                  mặc định. Trình duyệt không lưu khóa xuống ổ đĩa, nên sau khi tải lại trang bạn sẽ
                  cần nhập lại.
                </p>
              </div>

              <div className="form-group">
                <label className="form-label">Base URL (Tùy chọn)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="https://api.openai.com/v1 hoặc http://localhost:11434/v1"
                  value={configForm.baseUrl}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, baseUrl: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label className="form-label">Danh sách mô hình hỗ trợ</label>
                <div className="modal-models-selection">
                  {configModalProvider.models.map((m) => {
                    const isChecked = configForm.selectedModelIds.includes(m.id);
                    return (
                      <label key={m.id} className={`model-checkbox-pill ${isChecked ? "checked" : ""}`}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            const next = e.target.checked
                              ? [...configForm.selectedModelIds, m.id]
                              : configForm.selectedModelIds.filter((x) => x !== m.id);
                            setConfigForm({ ...configForm, selectedModelIds: next });
                          }}
                        />
                        <span className="m-pill-name">{m.name}</span>
                        <span className="m-pill-type">{m.type}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="modal-test-box">
                <button
                  type="button"
                  className="btn btn-secondary btn-test-modal"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                >
                  {testingConnection ? <div className="spinner-sm" /> : <Zap size={14} />}
                  <span>{testingConnection ? "Đang kiểm tra..." : "Kiểm tra kết nối"}</span>
                </button>

                {testResult && (
                  <div
                    className={`test-result-pill ${
                      testResult.success ? "success" : "error"
                    }`}
                  >
                    {testResult.success ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
                    <span>{testResult.message}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="config-modal-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setConfigModalProvider(null)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveProvider}
              >
                Lưu & Thêm nhà cung cấp
              </button>
            </div>
          </div>
        </div>
      )}

      <Modal
        open={Boolean(pendingDeleteProvider)}
        onClose={() => setPendingDeleteProvider(null)}
        title="Xóa cấu hình nhà cung cấp?"
        description={
          pendingDeleteProvider
            ? `Cấu hình “${pendingDeleteProvider.instanceName}” (${pendingDeleteProvider.providerName}) sẽ bị gỡ khỏi danh sách. Các mô hình mặc định đang trỏ tới nó sẽ cần chọn lại.`
            : ""
        }
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setPendingDeleteProvider(null)}>
              Hủy
            </button>
            <button type="button" className="danger-btn" onClick={confirmDeleteProvider}>
              <Trash2 size={15} />
              Xóa cấu hình
            </button>
          </>
        }
      />
    </div>
  );
}
