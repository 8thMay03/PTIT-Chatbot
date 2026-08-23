import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Cpu,
  Eye,
  EyeOff,
  Flame,
  Key,
  Layers,
  RotateCcw,
  Save,
  Scale,
  ShieldCheck,
  Sliders,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";
import { API_BASE_URL } from "./api";

const PRESETS = [
  {
    id: "fast",
    name: "Tốc độ cao",
    icon: Zap,
    description: "Gemini 1.5 Flash · Tắt Multi-Query & Reranker · TTFT cực nhanh",
    config: {
      llm: { provider: "gemini", gemini_model: "gemini-1.5-flash", temperature: 0.1 },
      retrieval: { multi_query_enabled: false, top_k: 3, hybrid_vector_weight: 0.7 },
      reranker: { enabled: false },
      guardrails: { scope_enabled: true },
    },
  },
  {
    id: "balanced",
    name: "Cân bằng (Mặc định)",
    icon: Scale,
    description: "GPT-4o-mini / Gemini · Multi-Query (Rule-based) · Heuristic Reranker",
    config: {
      llm: { provider: "openai", openai_model: "gpt-4o-mini", temperature: 0.0 },
      retrieval: {
        multi_query_enabled: true,
        multi_query_use_llm: false,
        multi_query_count: 3,
        top_k: 4,
        hybrid_vector_weight: 0.65,
      },
      reranker: { enabled: true, provider: "heuristic", candidate_multiplier: 3 },
      guardrails: { scope_enabled: true },
    },
  },
  {
    id: "accuracy",
    name: "Chính xác cao",
    icon: Target,
    description: "GPT-4o · LLM Multi-Query · Cross-Encoder Reranking sâu",
    config: {
      llm: { provider: "openai", openai_model: "gpt-4o", temperature: 0.0 },
      retrieval: {
        multi_query_enabled: true,
        multi_query_use_llm: true,
        multi_query_count: 4,
        top_k: 5,
        hybrid_vector_weight: 0.6,
      },
      reranker: {
        enabled: true,
        provider: "cross-encoder",
        model: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        candidate_multiplier: 4,
      },
      guardrails: { scope_enabled: true },
    },
  },
];

export default function SettingsView() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [showApiKey, setShowApiKey] = useState(false);

  // Form State
  const [llmProvider, setLlmProvider] = useState("openai");
  const [temperature, setTemperature] = useState(0.0);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [hasApiKey, setHasApiKey] = useState(false);

  // OpenAI
  const [openaiModel, setOpenaiModel] = useState("gpt-4o-mini");
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState("");

  // Gemini
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-flash");

  // Azure
  const [azureEndpoint, setAzureEndpoint] = useState("");
  const [azureDeployment, setAzureDeployment] = useState("");
  const [azureApiVersion, setAzureApiVersion] = useState("2024-02-15-preview");

  // OpenAI Compatible
  const [compatBaseUrl, setCompatBaseUrl] = useState("http://localhost:11434/v1");
  const [compatModel, setCompatModel] = useState("qwen3:8b");

  // Retrieval & Multi-Query
  const [multiQueryEnabled, setMultiQueryEnabled] = useState(true);
  const [multiQueryUseLlm, setMultiQueryUseLlm] = useState(false);
  const [multiQueryCount, setMultiQueryCount] = useState(3);
  const [queryRewriteUseLlm, setQueryRewriteUseLlm] = useState(false);
  const [topK, setTopK] = useState(4);
  const [hybridVectorWeight, setHybridVectorWeight] = useState(0.65);

  // Reranker
  const [rerankerEnabled, setRerankerEnabled] = useState(true);
  const [rerankerProvider, setRerankerProvider] = useState("heuristic");
  const [rerankerModel, setRerankerModel] = useState("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1");
  const [candidateMultiplier, setCandidateMultiplier] = useState(3);

  // Guardrails
  const [scopeEnabled, setScopeEnabled] = useState(true);
  const [minVectorScore, setMinVectorScore] = useState(0.3);
  const [minBm25Score, setMinBm25Score] = useState(2.0);

  // Load config on mount
  useEffect(() => {
    fetchConfig();
  }, []);

  function showToast(text, type = "success") {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  }

  async function fetchConfig() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config`);
      if (!res.ok) throw new Error("Không thể tải cấu hình");
      const data = await res.json();
      applyConfigToState(data);
    } catch (err) {
      showToast("Lỗi khi tải cấu hình từ máy chủ.", "error");
    } finally {
      setLoading(false);
    }
  }

  function applyConfigToState(data) {
    if (data.llm) {
      setLlmProvider(data.llm.provider || "openai");
      setTemperature(data.llm.temperature ?? 0.0);
      setHasApiKey(Boolean(data.llm.has_api_key));
      if (data.llm.openai_model) setOpenaiModel(data.llm.openai_model);
      if (data.llm.openai_base_url) setOpenaiBaseUrl(data.llm.openai_base_url);
      if (data.llm.gemini_model) setGeminiModel(data.llm.gemini_model);
      if (data.llm.azure_openai_endpoint) setAzureEndpoint(data.llm.azure_openai_endpoint);
      if (data.llm.azure_openai_deployment_name) setAzureDeployment(data.llm.azure_openai_deployment_name);
      if (data.llm.azure_openai_api_version) setAzureApiVersion(data.llm.azure_openai_api_version);
      if (data.llm.openai_compatible_base_url) setCompatBaseUrl(data.llm.openai_compatible_base_url);
      if (data.llm.openai_compatible_model) setCompatModel(data.llm.openai_compatible_model);
    }

    if (data.retrieval) {
      setMultiQueryEnabled(Boolean(data.retrieval.multi_query_enabled));
      setMultiQueryUseLlm(Boolean(data.retrieval.multi_query_use_llm));
      setMultiQueryCount(data.retrieval.multi_query_count ?? 3);
      setQueryRewriteUseLlm(Boolean(data.retrieval.query_rewrite_use_llm));
      setTopK(data.retrieval.top_k ?? 4);
      setHybridVectorWeight(data.retrieval.hybrid_vector_weight ?? 0.65);
    }

    if (data.reranker) {
      setRerankerEnabled(Boolean(data.reranker.enabled));
      setRerankerProvider(data.reranker.provider || "heuristic");
      if (data.reranker.model) setRerankerModel(data.reranker.model);
      setCandidateMultiplier(data.reranker.candidate_multiplier ?? 3);
    }

    if (data.guardrails) {
      setScopeEnabled(Boolean(data.guardrails.scope_enabled));
      setMinVectorScore(data.guardrails.min_vector_score ?? 0.3);
      setMinBm25Score(data.guardrails.min_bm25_score ?? 2.0);
    }
  }

  function applyPreset(preset) {
    const p = preset.config;
    if (p.llm) {
      if (p.llm.provider) setLlmProvider(p.llm.provider);
      if (p.llm.openai_model) setOpenaiModel(p.llm.openai_model);
      if (p.llm.gemini_model) setGeminiModel(p.llm.gemini_model);
      if (p.llm.temperature !== undefined) setTemperature(p.llm.temperature);
    }
    if (p.retrieval) {
      if (p.retrieval.multi_query_enabled !== undefined) setMultiQueryEnabled(p.retrieval.multi_query_enabled);
      if (p.retrieval.multi_query_use_llm !== undefined) setMultiQueryUseLlm(p.retrieval.multi_query_use_llm);
      if (p.retrieval.multi_query_count !== undefined) setMultiQueryCount(p.retrieval.multi_query_count);
      if (p.retrieval.top_k !== undefined) setTopK(p.retrieval.top_k);
      if (p.retrieval.hybrid_vector_weight !== undefined) setHybridVectorWeight(p.retrieval.hybrid_vector_weight);
    }
    if (p.reranker) {
      if (p.reranker.enabled !== undefined) setRerankerEnabled(p.reranker.enabled);
      if (p.reranker.provider) setRerankerProvider(p.reranker.provider);
      if (p.reranker.model) setRerankerModel(p.reranker.model);
      if (p.reranker.candidate_multiplier) setCandidateMultiplier(p.reranker.candidate_multiplier);
    }
    if (p.guardrails) {
      if (p.guardrails.scope_enabled !== undefined) setScopeEnabled(p.guardrails.scope_enabled);
    }
    showToast(`Đã áp dụng cấu hình mẫu: "${preset.name}". Nhấn "Lưu cấu hình" để áp dụng.`);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const payload = {
        llm: {
          provider: llmProvider,
          temperature: parseFloat(temperature),
          openai_model: openaiModel,
          openai_base_url: openaiBaseUrl || null,
          gemini_model: geminiModel,
          azure_openai_endpoint: azureEndpoint || null,
          azure_openai_deployment_name: azureDeployment || null,
          azure_openai_api_version: azureApiVersion || null,
          openai_compatible_base_url: compatBaseUrl || null,
          openai_compatible_model: compatModel || null,
          ...(apiKeyInput ? { api_key: apiKeyInput } : {}),
        },
        retrieval: {
          multi_query_enabled: multiQueryEnabled,
          multi_query_use_llm: multiQueryUseLlm,
          multi_query_count: parseInt(multiQueryCount, 10),
          query_rewrite_use_llm: queryRewriteUseLlm,
          top_k: parseInt(topK, 10),
          hybrid_vector_weight: parseFloat(hybridVectorWeight),
        },
        reranker: {
          enabled: rerankerEnabled,
          provider: rerankerProvider,
          model: rerankerModel,
          candidate_multiplier: parseInt(candidateMultiplier, 10),
        },
        guardrails: {
          scope_enabled: scopeEnabled,
          min_vector_score: parseFloat(minVectorScore),
          min_bm25_score: parseFloat(minBm25Score),
        },
      };

      const res = await fetch(`${API_BASE_URL}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Cập nhật thất bại");
      const updated = await res.json();
      applyConfigToState(updated);
      setApiKeyInput("");
      showToast("Cập nhật cấu hình RAG thành công!");
    } catch (err) {
      showToast("Lỗi khi lưu cấu hình.", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!window.confirm("Bạn có chắc chắn muốn khôi phục cài đặt gốc theo file .env?")) {
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config/reset`, { method: "POST" });
      if (!res.ok) throw new Error("Khôi phục thất bại");
      const resetData = await res.json();
      applyConfigToState(resetData);
      setApiKeyInput("");
      setTestResult(null);
      showToast("Đã khôi phục cài đặt gốc thành công!");
    } catch (err) {
      showToast("Lỗi khi khôi phục cài đặt gốc.", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleTestLLM() {
    setTesting(true);
    setTestResult(null);
    try {
      let activeModel = openaiModel;
      let activeBaseUrl = openaiBaseUrl;
      if (llmProvider === "gemini") {
        activeModel = geminiModel;
        activeBaseUrl = null;
      } else if (llmProvider === "azure") {
        activeModel = azureDeployment;
        activeBaseUrl = azureEndpoint;
      } else if (llmProvider === "openai_compatible") {
        activeModel = compatModel;
        activeBaseUrl = compatBaseUrl;
      }

      const payload = {
        provider: llmProvider,
        model: activeModel,
        api_key: apiKeyInput || null,
        base_url: activeBaseUrl || null,
        endpoint: azureEndpoint || null,
        deployment_name: azureDeployment || null,
        api_version: azureApiVersion || null,
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
        message: `Lỗi kết nối máy chủ: ${err.message}`,
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="settings-loading">
        <div className="settings-spinner" />
        <p>Đang tải cấu hình hệ thống...</p>
      </div>
    );
  }

  return (
    <div className="settings-container">
      {/* Toast Alert */}
      {toastMessage && (
        <div className={`settings-toast toast-${toastMessage.type}`}>
          {toastMessage.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header & Presets */}
      <div className="settings-header">
        <div>
          <h2>Cấu hình RAG & Mô hình AI</h2>
          <p className="settings-subtitle">
            Tùy biến linh hoạt nhà cung cấp LLM, chiến lược Reranker, Multi-Query và các ngưỡng lọc an toàn.
          </p>
        </div>

        <div className="presets-bar">
          <span className="presets-label">
            <Sparkles size={14} /> Cấu hình nhanh:
          </span>
          <div className="presets-group">
            {PRESETS.map((preset) => {
              const Icon = preset.icon;
              return (
                <button
                  key={preset.id}
                  type="button"
                  className="preset-btn"
                  onClick={() => applyPreset(preset)}
                  title={preset.description}
                >
                  <Icon size={14} />
                  <span>{preset.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="settings-grid">
        {/* CARD 1: LLM PROVIDER */}
        <section className="settings-card">
          <div className="card-header">
            <div className="card-icon card-icon-red">
              <Bot size={20} />
            </div>
            <div>
              <h3>Mô hình Ngôn ngữ (LLM Provider)</h3>
              <p>Chọn dịch vụ LLM sinh câu trả lời và điều chỉnh tham số sáng tạo.</p>
            </div>
          </div>

          <div className="card-body">
            <div className="form-group">
              <label className="form-label">Nhà cung cấp (Provider)</label>
              <div className="provider-selector">
                {[
                  { id: "openai", label: "OpenAI", desc: "GPT-4o, GPT-4o-mini" },
                  { id: "gemini", label: "Google Gemini", desc: "Gemini 1.5 Flash/Pro" },
                  { id: "azure", label: "Azure OpenAI", desc: "Enterprise Azure" },
                  { id: "openai_compatible", label: "Local / Ollama", desc: "vLLM, Ollama, LM Studio" },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`provider-tab ${llmProvider === item.id ? "active" : ""}`}
                    onClick={() => {
                      setLlmProvider(item.id);
                      setTestResult(null);
                    }}
                  >
                    <strong>{item.label}</strong>
                    <span>{item.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Provider specific inputs */}
            {llmProvider === "openai" && (
              <div className="provider-fields">
                <div className="form-group">
                  <label className="form-label">Tên Model OpenAI</label>
                  <select
                    className="form-select"
                    value={openaiModel}
                    onChange={(e) => setOpenaiModel(e.target.value)}
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini (Nhanh & Tối ưu chi phí)</option>
                    <option value="gpt-4o">gpt-4o (Thông minh & Toàn diện nhất)</option>
                    <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Base URL (Tùy chọn)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="https://api.openai.com/v1"
                    value={openaiBaseUrl}
                    onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                  />
                </div>
              </div>
            )}

            {llmProvider === "gemini" && (
              <div className="provider-fields">
                <div className="form-group">
                  <label className="form-label">Tên Model Google Gemini</label>
                  <select
                    className="form-select"
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                  >
                    <option value="gemini-1.5-flash">gemini-1.5-flash (Cực nhanh & Miễn phí tốt)</option>
                    <option value="gemini-1.5-pro">gemini-1.5-pro (Suy luận sâu)</option>
                    <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                  </select>
                </div>
              </div>
            )}

            {llmProvider === "azure" && (
              <div className="provider-fields">
                <div className="form-group">
                  <label className="form-label">Azure Endpoint URL</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="https://your-resource.openai.azure.com/"
                    value={azureEndpoint}
                    onChange={(e) => setAzureEndpoint(e.target.value)}
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Deployment Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="gpt-4-deployment"
                      value={azureDeployment}
                      onChange={(e) => setAzureDeployment(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">API Version</label>
                    <input
                      type="text"
                      className="form-input"
                      value={azureApiVersion}
                      onChange={(e) => setAzureApiVersion(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

            {llmProvider === "openai_compatible" && (
              <div className="provider-fields">
                <div className="form-group">
                  <label className="form-label">Base URL (Ollama / vLLM Server)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="http://localhost:11434/v1"
                    value={compatBaseUrl}
                    onChange={(e) => setCompatBaseUrl(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Tên Model Local</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="qwen3:8b, llama3:8b, mistral..."
                    value={compatModel}
                    onChange={(e) => setCompatModel(e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* API Key Input */}
            <div className="form-group">
              <div className="form-label-row">
                <label className="form-label">
                  <Key size={14} /> Khóa API Key
                </label>
                {hasApiKey && (
                  <span className="badge badge-success">
                    <CheckCircle2 size={12} /> Đã có sẵn trên Server
                  </span>
                )}
              </div>
              <div className="input-password-wrapper">
                <input
                  type={showApiKey ? "text" : "password"}
                  className="form-input"
                  placeholder={hasApiKey ? "Nhập nếu muốn đổi khóa API mới..." : "Nhập API Key..."}
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                />
                <button
                  type="button"
                  className="btn-toggle-eye"
                  onClick={() => setShowApiKey(!showApiKey)}
                  title={showApiKey ? "Ẩn khóa" : "Hiện khóa"}
                >
                  {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Temperature Slider */}
            <div className="form-group">
              <div className="form-label-row">
                <label className="form-label">
                  <Flame size={14} /> Độ ngẫu nhiên (Temperature): <strong>{temperature}</strong>
                </label>
                <span className="form-hint">
                  {temperature === 0 ? "Chính xác, nghiêm ngặt" : temperature < 0.5 ? "Cân bằng" : "Sáng tạo hơn"}
                </span>
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

            {/* Test Connection Button & Result */}
            <div className="test-connection-box">
              <button
                type="button"
                className="btn btn-secondary btn-test"
                onClick={handleTestLLM}
                disabled={testing}
              >
                {testing ? <div className="spinner-sm" /> : <Zap size={15} />}
                <span>{testing ? "Đang kiểm tra kết nối..." : "Kiểm tra kết nối LLM"}</span>
              </button>

              {testResult && (
                <div className={`test-result-alert ${testResult.success ? "alert-success" : "alert-error"}`}>
                  {testResult.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <div>
                    <strong>{testResult.message}</strong>
                    {testResult.latency_ms && (
                      <span className="latency-tag">Độ trễ: {testResult.latency_ms} ms</span>
                    )}
                    {testResult.sample_output && (
                      <p className="sample-out">Phản hồi: "{testResult.sample_output}"</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* CARD 2: RETRIEVAL & MULTI-QUERY */}
        <section className="settings-card">
          <div className="card-header">
            <div className="card-icon card-icon-blue">
              <Layers size={20} />
            </div>
            <div>
              <h3>Truy xuất & Đa truy vấn (Multi-Query)</h3>
              <p>Mở rộng câu hỏi của sinh viên để bao phủ đầy đủ quy chế học vụ.</p>
            </div>
          </div>

          <div className="card-body">
            {/* Multi Query Toggle */}
            <div className="toggle-row">
              <div>
                <strong>Bật Multi-Query Expansion</strong>
                <p>Tự động sinh các biến thể câu hỏi khác nhau để tìm kiếm toàn diện.</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={multiQueryEnabled}
                  onChange={(e) => setMultiQueryEnabled(e.target.checked)}
                />
                <span className="slider round" />
              </label>
            </div>

            {multiQueryEnabled && (
              <div className="sub-settings-panel">
                <div className="form-group">
                  <label className="form-label">Phương thức sinh Multi-Query</label>
                  <div className="radio-group">
                    <label className={`radio-pill ${!multiQueryUseLlm ? "active" : ""}`}>
                      <input
                        type="radio"
                        name="mq_mode"
                        checked={!multiQueryUseLlm}
                        onChange={() => setMultiQueryUseLlm(false)}
                      />
                      <span>Từ điển & Quy tắc (Heuristic - 0ms)</span>
                    </label>
                    <label className={`radio-pill ${multiQueryUseLlm ? "active" : ""}`}>
                      <input
                        type="radio"
                        name="mq_mode"
                        checked={multiQueryUseLlm}
                        onChange={() => setMultiQueryUseLlm(true)}
                      />
                      <span>Dùng LLM Prompting (Sâu sắc hơn)</span>
                    </label>
                  </div>
                </div>

                <div className="form-group">
                  <div className="form-label-row">
                    <label className="form-label">
                      Số lượng truy vấn sinh thêm: <strong>{multiQueryCount}</strong>
                    </label>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    className="form-range"
                    value={multiQueryCount}
                    onChange={(e) => setMultiQueryCount(parseInt(e.target.value, 10))}
                  />
                </div>
              </div>
            )}

            {/* Contextual Query Rewriting */}
            <div className="toggle-row" style={{ marginTop: "12px" }}>
              <div>
                <strong>Query Rewriting theo ngữ cảnh</strong>
                <p>Viết lại câu hỏi dựa vào lịch sử trao đổi trước đó.</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={queryRewriteUseLlm}
                  onChange={(e) => setQueryRewriteUseLlm(e.target.checked)}
                />
                <span className="slider round" />
              </label>
            </div>

            {/* Top K */}
            <div className="form-group" style={{ marginTop: "16px" }}>
              <div className="form-label-row">
                <label className="form-label">
                  Số đoạn văn bản nạp vào LLM (Top-K): <strong>{topK}</strong>
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

            {/* Hybrid Vector Weight */}
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
              <div className="range-labels">
                <span>Ưu tiên từ khóa (BM25)</span>
                <span>Ưu tiên ngữ nghĩa (Vector)</span>
              </div>
            </div>
          </div>
        </section>

        {/* CARD 3: RERANKER */}
        <section className="settings-card">
          <div className="card-header">
            <div className="card-icon card-icon-amber">
              <Cpu size={20} />
            </div>
            <div>
              <h3>Bộ Tái sắp xếp (Reranker Strategy)</h3>
              <p>Chấm điểm lại các ứng viên context để đưa văn bản liên quan nhất lên đầu.</p>
            </div>
          </div>

          <div className="card-body">
            {/* Reranker Toggle */}
            <div className="toggle-row">
              <div>
                <strong>Bật Reranking Context</strong>
                <p>Tái xếp hạng danh sách chunk trước khi gửi tới LLM.</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={rerankerEnabled}
                  onChange={(e) => setRerankerEnabled(e.target.checked)}
                />
                <span className="slider round" />
              </label>
            </div>

            {rerankerEnabled && (
              <div className="sub-settings-panel">
                <div className="form-group">
                  <label className="form-label">Thuật toán Reranker</label>
                  <select
                    className="form-select"
                    value={rerankerProvider}
                    onChange={(e) => setRerankerProvider(e.target.value)}
                  >
                    <option value="heuristic">Heuristic (Trọng số Vector + BM25 + Term Coverage - Siêu tốc)</option>
                    <option value="cross-encoder">Cross-Encoder (Transformer Deep Learning - Chính xác tuyệt đối)</option>
                  </select>
                </div>

                {rerankerProvider === "cross-encoder" && (
                  <div className="form-group">
                    <label className="form-label">Cross-Encoder Model Name</label>
                    <input
                      type="text"
                      className="form-input"
                      value={rerankerModel}
                      onChange={(e) => setRerankerModel(e.target.value)}
                      placeholder="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
                    />
                  </div>
                )}

                <div className="form-group">
                  <div className="form-label-row">
                    <label className="form-label">
                      Hệ số nhân ứng viên trước Rerank: <strong>{candidateMultiplier}x</strong> (Lấy {candidateMultiplier * topK} chunks)
                    </label>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="6"
                    step="1"
                    className="form-range"
                    value={candidateMultiplier}
                    onChange={(e) => setCandidateMultiplier(parseInt(e.target.value, 10))}
                  />
                </div>
              </div>
            )}
          </div>
        </section>

        {/* CARD 4: GUARDRAILS & CONFIDENCE */}
        <section className="settings-card">
          <div className="card-header">
            <div className="card-icon card-icon-green">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h3>Bảo vệ & Ngưỡng tin cậy (Guardrails)</h3>
              <p>Lọc câu hỏi ngoài phạm vi và chặn hallucination khi thiếu dữ liệu.</p>
            </div>
          </div>

          <div className="card-body">
            {/* Scope Guardrail */}
            <div className="toggle-row">
              <div>
                <strong>PTIT Scope Guardrail</strong>
                <p>Từ chối tự động các câu hỏi ngoài lề (y tế, pháp lý, thời sự, giải trí...).</p>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={scopeEnabled}
                  onChange={(e) => setScopeEnabled(e.target.checked)}
                />
                <span className="slider round" />
              </label>
            </div>

            {/* Confidence Thresholds */}
            <div className="form-group" style={{ marginTop: "16px" }}>
              <div className="form-label-row">
                <label className="form-label">
                  Điểm sàn Vector tối thiểu: <strong>{minVectorScore}</strong>
                </label>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                className="form-range"
                value={minVectorScore}
                onChange={(e) => setMinVectorScore(parseFloat(e.target.value))}
              />
            </div>

            <div className="form-group">
              <div className="form-label-row">
                <label className="form-label">
                  Điểm sàn BM25 tối thiểu: <strong>{minBm25Score}</strong>
                </label>
              </div>
              <input
                type="range"
                min="0.5"
                max="5.0"
                step="0.25"
                className="form-range"
                value={minBm25Score}
                onChange={(e) => setMinBm25Score(parseFloat(e.target.value))}
              />
            </div>
          </div>
        </section>
      </div>

      {/* Action Footer Bar */}
      <div className="settings-action-bar">
        <button
          type="button"
          className="btn btn-outline"
          onClick={handleReset}
          disabled={saving}
        >
          <RotateCcw size={16} />
          <span>Khôi phục mặc định (.env)</span>
        </button>

        <button
          type="button"
          className="btn btn-primary btn-save"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? <div className="spinner-sm" /> : <Save size={16} />}
          <span>{saving ? "Đang lưu..." : "Lưu cấu hình"}</span>
        </button>
      </div>
    </div>
  );
}
