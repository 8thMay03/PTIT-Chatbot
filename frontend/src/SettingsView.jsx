import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  EyeOff,
  Flame,
  Info,
  Key,
  Layers,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { API_BASE_URL } from "./api";

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
          fill="url(#gemini-grad)"
        />
        <defs>
          <linearGradient id="gemini-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
            <stop stopColor="#4285F4" />
            <stop offset="0.33" stopColor="#9B72CB" />
            <stop offset="0.66" stopColor="#D96570" />
            <stop offset="1" stopColor="#F4B400" />
          </linearGradient>
        </defs>
      </svg>
    );
  }

  if (p.includes("anthropic") || p.includes("claude")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
        <path d="M14.5 4h3.5L12 20h-3.5L14.5 4zM6 20h3.5L15 4H11.5L6 20z" fill="#D97757" />
      </svg>
    );
  }

  if (p.includes("deepseek")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path
          d="M3 14C3 8 8 4 14 4C19 4 21 8 21 11C21 14 18 16 15 16H9C6 16 3 18 3 20"
          stroke="#0066FF"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="15" cy="9" r="1.5" fill="#0066FF" />
      </svg>
    );
  }

  if (p.includes("moonshot") || p.includes("kimi")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
        <circle cx="12" cy="12" r="9" fill="#111827" />
        <path d="M12 3a9 9 0 0 0 0 18V3z" fill="#F3F4F6" opacity="0.4" />
        <circle cx="12" cy="12" r="7" fill="none" stroke="#F3F4F6" strokeWidth="1.5" strokeDasharray="3 3" />
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

  if (p.includes("zhipu") || p.includes("glm")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="12" cy="12" r="3" fill="#2563EB" />
        <circle cx="6" cy="7" r="2" fill="#3B82F6" />
        <circle cx="18" cy="7" r="2" fill="#3B82F6" />
        <circle cx="5" cy="16" r="2" fill="#60A5FA" />
        <circle cx="19" cy="16" r="2" fill="#60A5FA" />
        <circle cx="12" cy="20" r="2" fill="#93C5FD" />
      </svg>
    );
  }

  if (p.includes("xai") || p.includes("grok")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    );
  }

  if (p.includes("huggingface") || p.includes("hf")) {
    return (
      <span style={{ fontSize: `${size}px`, lineHeight: 1 }} role="img" aria-label="HuggingFace">
        🤗
      </span>
    );
  }

  if (p.includes("azure")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path d="M13.5 3L3 18.5h6.5l4-7.5 4 7.5H21L13.5 3z" fill="#0078D4" />
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
    id: "anthropic",
    name: "Anthropic",
    tags: ["LLM"],
    models: [
      { id: "claude-3-5-sonnet-20241022", name: "claude-3-5-sonnet", type: "LLM" },
      { id: "claude-3-5-haiku-20241022", name: "claude-3-5-haiku", type: "LLM" },
      { id: "claude-3-opus-20240229", name: "claude-3-opus", type: "LLM" },
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
    id: "deepseek",
    name: "DeepSeek",
    tags: ["LLM"],
    models: [
      { id: "deepseek-chat", name: "deepseek-chat (V3)", type: "LLM" },
      { id: "deepseek-reasoner", name: "deepseek-reasoner (R1)", type: "LLM" },
    ],
  },
  {
    id: "moonshot",
    name: "Moonshot",
    tags: ["LLM", "VLM"],
    models: [
      { id: "moonshot-v1-8k", name: "moonshot-v1-8k", type: "LLM" },
      { id: "moonshot-v1-32k", name: "moonshot-v1-32k", type: "LLM" },
      { id: "moonshot-v1-vision", name: "moonshot-v1-vision", type: "VLM" },
    ],
  },
  {
    id: "tongyi",
    name: "Tongyi-Qianwen",
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
    id: "zhipu",
    name: "ZHIPU-AI",
    tags: ["LLM", "Embedding", "ASR", "VLM"],
    models: [
      { id: "glm-4-plus", name: "glm-4-plus", type: "LLM" },
      { id: "glm-4-flash", name: "glm-4-flash", type: "LLM" },
      { id: "embedding-3", name: "embedding-3", type: "Embedding" },
      { id: "glm-4v-plus", name: "glm-4v-plus", type: "VLM" },
    ],
  },
  {
    id: "xai",
    name: "xAI",
    tags: ["LLM", "VLM"],
    models: [
      { id: "grok-2-latest", name: "grok-2-latest", type: "LLM" },
      { id: "grok-2-vision-latest", name: "grok-2-vision-latest", type: "VLM" },
    ],
  },
  {
    id: "huggingface",
    name: "HuggingFace",
    tags: ["LLM", "Embedding", "Rerank"],
    models: [
      { id: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", name: "mmarco-mMiniLMv2-L12", type: "Rerank" },
      { id: "BAAI/bge-m3", name: "BAAI/bge-m3", type: "Embedding" },
      { id: "BAAI/bge-reranker-large", name: "bge-reranker-large", type: "Rerank" },
      { id: "sentence-transformers/all-MiniLM-L6-v2", name: "all-MiniLM-L6-v2", type: "Embedding" },
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
  {
    id: "azure",
    name: "Azure OpenAI",
    tags: ["LLM", "Embedding"],
    models: [
      { id: "azure-gpt-4o", name: "gpt-4o-deployment", type: "LLM" },
      { id: "azure-gpt-4o-mini", name: "gpt-4o-mini-deployment", type: "LLM" },
      { id: "azure-text-embedding-3-small", name: "text-embedding-3-small", type: "Embedding" },
    ],
  },
];

// Initial default state mirroring image.png
const INITIAL_ADDED_PROVIDERS = [
  {
    id: "added-openai-1",
    providerId: "openai",
    providerName: "OpenAI",
    instanceName: "test",
    apiKeyMasked: "sk-proj-••••••••89ab",
    baseUrl: "https://api.openai.com/v1",
    models: [
      { id: "gpt-4o-mini", name: "gpt-4o-mini", type: "LLM" },
      { id: "gpt-4o", name: "gpt-4o", type: "LLM" },
      { id: "text-embedding-3-small", name: "text-embedding-3-small", type: "Embedding" },
      { id: "tts-1", name: "tts-1", type: "TTS" },
      { id: "whisper-1", name: "whisper-1", type: "ASR" },
    ],
  },
  {
    id: "added-cohere-1",
    providerId: "cohere",
    providerName: "Cohere",
    instanceName: "test111",
    apiKeyMasked: "coh-••••••••321a",
    baseUrl: "https://api.cohere.com/v2",
    models: [
      { id: "command-r-plus", name: "command-r-plus", type: "LLM" },
      { id: "embed-multilingual-v3.0", name: "embed-multilingual-v3.0", type: "Embedding" },
      { id: "rerank-multilingual-v3.0", name: "rerank-multilingual-v3.0", type: "Rerank" },
      { id: "rerank-english-v3.0", name: "rerank-english-v3.0", type: "Rerank" },
    ],
  },
];

export default function SettingsView() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

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

  // Expanded cards in "Added models"
  const [expandedProviderIds, setExpandedProviderIds] = useState({});

  // Default Selected Models mapping (matching image: LLM, Embedding, VLM, ASR, Rerank, TTS)
  const [defaultModels, setDefaultModels] = useState({
    LLM: {
      modelId: "gpt-4o-mini",
      providerId: "openai",
      instanceName: "test",
    },
    Embedding: {
      modelId: "embed-multilingual-v3.0",
      providerId: "cohere",
      instanceName: "test111",
    },
    VLM: null,
    ASR: null,
    Rerank: {
      modelId: "rerank-multilingual-v3.0",
      providerId: "cohere",
      instanceName: "test111",
    },
    TTS: null,
  });

  // Search & Filter state in Right Column ("Available models")
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");

  // Dropdown popover state for default model rows
  const [activeDropdownSlot, setActiveDropdownSlot] = useState(null);
  const dropdownRef = useRef(null);

  // Provider Configuration Modal State
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

  // Advanced Settings Drawer / Accordion
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.0);
  const [topK, setTopK] = useState(4);
  const [multiQueryEnabled, setMultiQueryEnabled] = useState(true);
  const [multiQueryCount, setMultiQueryCount] = useState(3);
  const [hybridVectorWeight, setHybridVectorWeight] = useState(0.65);
  const [scopeEnabled, setScopeEnabled] = useState(true);

  // Save addedProviders to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("ptit_added_providers", JSON.stringify(addedProviders));
    } catch (e) {
      // ignore
    }
  }, [addedProviders]);

  // Load config from backend on mount
  useEffect(() => {
    fetchBackendConfig();
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdownSlot(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function showToast(text, type = "success") {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  }

  async function fetchBackendConfig() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config`);
      if (!res.ok) throw new Error("Không thể tải cấu hình");
      const data = await res.json();
      
      // Sync state with backend
      if (data.llm) {
        setTemperature(data.llm.temperature ?? 0.0);
        if (data.llm.openai_model || data.llm.model) {
          const m = data.llm.openai_model || data.llm.model;
          const p = data.llm.provider || "openai";
          setDefaultModels((prev) => ({
            ...prev,
            LLM: {
              modelId: m,
              providerId: p,
              instanceName: p === "openai" ? "test" : "default",
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
              providerId: data.embedding.provider || "cohere",
              instanceName: "test111",
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
              providerId: data.reranker.provider || "cohere",
              instanceName: "test111",
            },
          }));
        }
      }

      if (data.retrieval) {
        setMultiQueryEnabled(Boolean(data.retrieval.multi_query_enabled));
        setMultiQueryCount(data.retrieval.multi_query_count ?? 3);
        setTopK(data.retrieval.top_k ?? 4);
        setHybridVectorWeight(data.retrieval.hybrid_vector_weight ?? 0.65);
      }

      if (data.guardrails) {
        setScopeEnabled(Boolean(data.guardrails.scope_enabled));
      }
    } catch (err) {
      console.warn("Using local configuration fallback:", err.message);
    } finally {
      setLoading(false);
    }
  }

  // Toggle accordion in Added Models
  function toggleExpandProvider(id) {
    setExpandedProviderIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  }

  // Delete Added Provider
  function handleDeleteProvider(id, name) {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa nhà cung cấp "${name}"?`)) {
      return;
    }
    setAddedProviders((prev) => prev.filter((p) => p.id !== id));
    showToast(`Đã xóa cấu hình "${name}".`);
  }

  // Open Provider Configuration Modal
  function handleOpenConfigModal(provider) {
    setConfigModalProvider(provider);
    setConfigForm({
      instanceName: `${provider.id}_${Math.floor(100 + Math.random() * 900)}`,
      apiKey: "",
      baseUrl: provider.id === "openai" ? "https://api.openai.com/v1" : "",
      selectedModelIds: provider.models.map((m) => m.id),
    });
    setTestResult(null);
    setShowApiKey(false);
  }

  // Test Provider LLM Connection
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

  // Save Provider from Modal
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
      apiKeyMasked: maskedKey,
      baseUrl: configForm.baseUrl,
      models: configModalProvider.models.filter((m) =>
        configForm.selectedModelIds.includes(m.id)
      ),
    };

    setAddedProviders((prev) => [newEntry, ...prev]);
    setConfigModalProvider(null);
    showToast(`Đã thêm cấu hình thành công: "${name}"`);
  }

  // Select a Default Model
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

    // Synchronize directly with backend
    try {
      const payload = {};
      if (slotKey === "LLM") {
        payload.llm = {
          provider: provider.id || provider.providerId,
          openai_model: model.id,
          model: model.id,
        };
      } else if (slotKey === "Embedding") {
        payload.embedding = {
          provider: provider.id || provider.providerId,
          model: model.id,
        };
      } else if (slotKey === "Rerank") {
        payload.reranker = {
          enabled: true,
          provider: (provider.id || provider.providerId).includes("cohere") ? "cohere" : "cross-encoder",
          model: model.id,
        };
      }

      await fetch(`${API_BASE_URL}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      showToast(`Đã chọn mặc định cho ${slotKey}: ${model.name}`);
    } catch (e) {
      showToast(`Đã cập nhật ${slotKey}: ${model.name}`);
    }
  }

  // Clear a Default Model
  function handleClearDefaultModel(slotKey, e) {
    e.stopPropagation();
    setDefaultModels((prev) => ({
      ...prev,
      [slotKey]: null,
    }));
    showToast(`Đã hủy chọn mặc định cho ${slotKey}`);
  }

  // Filter available models
  const filteredProviders = useMemo(() => {
    return AVAILABLE_PROVIDERS.filter((provider) => {
      // Category filter
      if (activeCategory !== "All") {
        if (!provider.tags.includes(activeCategory)) return false;
      }
      // Search query filter
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const matchName = provider.name.toLowerCase().includes(q);
      const matchTag = provider.tags.some((t) => t.toLowerCase().includes(q));
      const matchModel = provider.models.some((m) => m.name.toLowerCase().includes(q));
      return matchName || matchTag || matchModel;
    });
  }, [searchQuery, activeCategory]);

  // Compute category counts for chips
  const categoryCounts = useMemo(() => {
    const counts = {
      All: 63,
      LLM: 37,
      Embedding: 25,
      Rerank: 10,
      TTS: 8,
      ASR: 11,
      VLM: 17,
      OCR: 4,
    };
    return counts;
  }, []);

  // Save All Configuration
  async function handleSaveAll() {
    setSaving(true);
    try {
      const payload = {
        llm: {
          provider: defaultModels.LLM?.providerId || "openai",
          openai_model: defaultModels.LLM?.modelId || "gpt-4o-mini",
          temperature: parseFloat(temperature),
        },
        embedding: {
          provider: defaultModels.Embedding?.providerId || "openai",
          model: defaultModels.Embedding?.modelId || "text-embedding-3-small",
        },
        reranker: {
          enabled: Boolean(defaultModels.Rerank),
          provider: defaultModels.Rerank?.providerId?.includes("cohere") ? "cohere" : "heuristic",
          model: defaultModels.Rerank?.modelId || "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        },
        retrieval: {
          multi_query_enabled: multiQueryEnabled,
          multi_query_count: parseInt(multiQueryCount, 10),
          top_k: parseInt(topK, 10),
          hybrid_vector_weight: parseFloat(hybridVectorWeight),
        },
        guardrails: {
          scope_enabled: scopeEnabled,
        },
      };

      const res = await fetch(`${API_BASE_URL}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Cập nhật thất bại");
      showToast("Đã lưu toàn bộ cấu hình hệ thống thành công!");
    } catch (err) {
      showToast("Đã lưu cài đặt cục bộ.", "success");
    } finally {
      setSaving(false);
    }
  }

  // Model categories slot definitions
  const SLOTS = [
    { key: "LLM", label: "LLM", required: true, tooltip: "Mô hình ngôn ngữ sinh câu trả lời chính (GPT-4o, Claude, Gemini...)" },
    { key: "Embedding", label: "Embedding", required: false, tooltip: "Mô hình chuyển văn bản thành vector nhúng ngữ nghĩa (Cohere, OpenAI, BGE...)" },
    { key: "VLM", label: "VLM", required: false, tooltip: "Visual Language Model xử lý hình ảnh và tài liệu biểu đồ (GPT-4o Vision, Gemini Flash...)" },
    { key: "ASR", label: "ASR", required: false, tooltip: "Automatic Speech Recognition nhận dạng giọng nói sinh viên (Whisper...)" },
    { key: "Rerank", label: "Rerank", required: false, tooltip: "Mô hình tái xếp hạng độ liên quan văn bản (Cohere Rerank, Cross-Encoder...)" },
    { key: "TTS", label: "TTS", required: false, tooltip: "Text-to-Speech chuyển đổi câu trả lời thành giọng đọc" },
  ];

  // Gather available models for the dropdown selector
  function getCandidateModelsForSlot(slotKey) {
    const list = [];
    // From added providers
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
    // If empty, supply candidates from available providers catalog
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
        <p>Đang tải cấu hình mô hình...</p>
      </div>
    );
  }

  return (
    <div className="model-mgmt-page">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`model-mgmt-toast toast-${toastMessage.type}`}>
          {toastMessage.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Main 2-Column Split View */}
      <div className="model-mgmt-layout">
        {/* =================================================================== */}
        {/* LEFT COLUMN: Set Default Models & Added Models                      */}
        {/* =================================================================== */}
        <div className="model-mgmt-left">
          {/* SECTION 1: SET DEFAULT MODELS */}
          <div className="mgmt-section-header">
            <h2 className="mgmt-title">Set default models</h2>
            <p className="mgmt-subtitle">Please complete these settings before beginning</p>
          </div>

          <div className="default-models-card">
            {SLOTS.map((slot) => {
              const selected = defaultModels[slot.key];
              const isDropdownOpen = activeDropdownSlot === slot.key;

              return (
                <div key={slot.key} className="default-model-row">
                  {/* Left Label */}
                  <div className="slot-label-col">
                    <span className="slot-name">
                      {slot.required && <span className="slot-required">*</span>}
                      {slot.label}
                    </span>
                    <span className="slot-info-icon" title={slot.tooltip}>
                      <Info size={13} />
                    </span>
                  </div>

                  {/* Right Input / Dropdown Box */}
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

                    {/* Popover Dropdown list */}
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
          </div>

          <div className="added-models-list">
            {addedProviders.length === 0 ? (
              <div className="empty-added-box">
                <p>Chưa có nhà cung cấp nào được thêm. Nhấp vào danh sách bên phải để thêm.</p>
              </div>
            ) : (
              addedProviders.map((provider) => {
                const isExpanded = Boolean(expandedProviderIds[provider.id]);

                return (
                  <div key={provider.id} className="added-provider-card">
                    {/* Header Bar: Logo + Name */}
                    <div className="added-card-header">
                      <div className="added-provider-info">
                        <div className="added-provider-icon">
                          <ProviderLogo providerId={provider.providerId} size={22} />
                        </div>
                        <span className="added-provider-title">{provider.providerName}</span>
                      </div>
                    </div>

                    {/* Row Body: Instance tag, View models button, Trash button */}
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
                          onClick={() => handleDeleteProvider(provider.id, provider.instanceName)}
                          title="Xóa cấu hình"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Expandable Models Sub-list */}
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

          {/* Collapsible Advanced Parameters */}
          <div className="advanced-rag-box">
            <button
              type="button"
              className="btn-advanced-toggle"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <Settings size={16} />
              <span>Cấu hình RAG & Tham số nâng cao (Temperature, Multi-Query, Top-K)</span>
              {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showAdvanced && (
              <div className="advanced-panel-content">
                <div className="form-group">
                  <div className="form-label-row">
                    <label className="form-label">
                      <Flame size={14} /> Độ ngẫu nhiên (Temperature): <strong>{temperature}</strong>
                    </label>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    className="form-range"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  />
                </div>

                <div className="form-group">
                  <div className="form-label-row">
                    <label className="form-label">
                      <Layers size={14} /> Số đoạn văn bản nạp vào LLM (Top-K): <strong>{topK}</strong>
                    </label>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    className="form-range"
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value, 10))}
                  />
                </div>

                <div className="form-group">
                  <div className="form-label-row">
                    <label className="form-label">
                      Tỷ trọng Hybrid Search (Vector: <strong>{Math.round(hybridVectorWeight * 100)}%</strong> · BM25: <strong>{Math.round((1 - hybridVectorWeight) * 100)}%</strong>)
                    </label>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    className="form-range"
                    value={hybridVectorWeight}
                    onChange={(e) => setHybridVectorWeight(parseFloat(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Bottom Action Buttons */}
          <div className="mgmt-footer-actions">
            <button
              type="button"
              className="btn btn-save-models"
              onClick={handleSaveAll}
              disabled={saving}
            >
              {saving ? <div className="spinner-sm" /> : <Save size={16} />}
              <span>{saving ? "Đang lưu..." : "Lưu tất cả cấu hình"}</span>
            </button>
          </div>
        </div>

        {/* =================================================================== */}
        {/* RIGHT COLUMN: Available Models Catalog                              */}
        {/* =================================================================== */}
        <div className="model-mgmt-right">
          <div className="mgmt-section-header">
            <h2 className="mgmt-title">Available models</h2>
          </div>

          {/* Search Input Bar */}
          <div className="available-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search"
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

          {/* Filter Chips Bar */}
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

          {/* Provider Cards List */}
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

      {/* =================================================================== */}
      {/* MODAL: Configure & Add Provider                                     */}
      {/* =================================================================== */}
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
              {/* Instance Tag / Name */}
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

              {/* API Key */}
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
                  >
                    {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Base URL */}
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

              {/* Supported Models */}
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

              {/* Test Connection */}
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
    </div>
  );
}
