import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Flame,
  Gauge,
  Info,
  Layers,
  RotateCcw,
  Save,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { API_BASE_URL } from "./api";

export default function ConfigView() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // CONFIGURATION / PARAMETERS STATE
  const [temperature, setTemperature] = useState(0.0);
  const [llmTimeout, setLlmTimeout] = useState(30);
  const [maxRetries, setMaxRetries] = useState(2);

  const [topK, setTopK] = useState(4);
  const [hybridVectorWeight, setHybridVectorWeight] = useState(0.65);
  const [multiQueryEnabled, setMultiQueryEnabled] = useState(true);
  const [multiQueryCount, setMultiQueryCount] = useState(3);
  const [multiQueryUseLlm, setMultiQueryUseLlm] = useState(false);

  const [scopeEnabled, setScopeEnabled] = useState(true);
  const [minVectorScore, setMinVectorScore] = useState(0.30);
  const [minBm25Score, setMinBm25Score] = useState(2.0);

  const [rerankerEnabled, setRerankerEnabled] = useState(true);
  const [candidateMultiplier, setCandidateMultiplier] = useState(3);

  useEffect(() => {
    fetchBackendConfig();
  }, []);

  function showToast(text, type = "success") {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  }

  async function fetchBackendConfig() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config`);
      if (!res.ok) throw new Error("Không thể tải cấu hình từ máy chủ");
      const data = await res.json();

      if (data.llm) {
        setTemperature(data.llm.temperature ?? 0.0);
        setLlmTimeout(data.llm.timeout ?? 30);
        setMaxRetries(data.llm.max_retries ?? 2);
      }

      if (data.reranker) {
        setRerankerEnabled(Boolean(data.reranker.enabled));
        setCandidateMultiplier(data.reranker.candidate_multiplier ?? 3);
      }

      if (data.retrieval) {
        setMultiQueryEnabled(Boolean(data.retrieval.multi_query_enabled));
        setMultiQueryCount(data.retrieval.multi_query_count ?? 3);
        setMultiQueryUseLlm(Boolean(data.retrieval.multi_query_use_llm));
        setTopK(data.retrieval.top_k ?? 4);
        setHybridVectorWeight(data.retrieval.hybrid_vector_weight ?? 0.65);
      }

      if (data.guardrails) {
        setScopeEnabled(Boolean(data.guardrails.scope_enabled));
        setMinVectorScore(data.guardrails.min_vector_score ?? 0.30);
        setMinBm25Score(data.guardrails.min_bm25_score ?? 2.0);
      }
    } catch (err) {
      console.warn("Using local configuration fallback:", err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleResetConfig() {
    if (!window.confirm("Bạn có chắc chắn muốn khôi phục toàn bộ cấu hình về mặc định ban đầu?")) {
      return;
    }
    setResetting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config/reset`, { method: "POST" });
      if (!res.ok) throw new Error("Khôi phục thất bại");
      await fetchBackendConfig();
      showToast("Đã khôi phục toàn bộ cấu hình về mặc định.");
    } catch (err) {
      showToast(`Lỗi: ${err.message}`, "error");
    } finally {
      setResetting(false);
    }
  }

  async function handleSaveAll() {
    setSaving(true);
    try {
      const payload = {
        llm: {
          temperature: parseFloat(temperature),
          timeout: parseFloat(llmTimeout),
          max_retries: parseInt(maxRetries, 10),
        },
        reranker: {
          enabled: rerankerEnabled,
          candidate_multiplier: parseInt(candidateMultiplier, 10),
        },
        retrieval: {
          multi_query_enabled: multiQueryEnabled,
          multi_query_count: parseInt(multiQueryCount, 10),
          multi_query_use_llm: multiQueryUseLlm,
          top_k: parseInt(topK, 10),
          hybrid_vector_weight: parseFloat(hybridVectorWeight),
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

      if (!res.ok) throw new Error("Cập nhật thất bại trên máy chủ");
      showToast("Đã lưu toàn bộ cấu hình RAG thành công!");
    } catch (err) {
      showToast("Đã lưu cấu hình cục bộ.", "success");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="model-mgmt-loading">
        <div className="model-mgmt-spinner" />
        <p>Đang tải cấu hình hệ thống...</p>
      </div>
    );
  }

  return (
    <div className="config-page-wrapper">
      {toastMessage && (
        <div className={`model-mgmt-toast toast-${toastMessage.type}`}>
          {toastMessage.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Top Header Bar */}
      <div className="settings-subtabs-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box">
            <Sliders size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Cấu hình Hệ thống & Tham số RAG</h2>
            <p className="config-main-desc">
              Tinh chỉnh nhiệt độ sinh (Temperature), số đoạn văn bản (Top-K), ngưỡng tương đồng (Similarity Threshold) và tỷ trọng Hybrid Search.
            </p>
          </div>
        </div>

        <div className="settings-header-actions">
          <button
            type="button"
            className="btn btn-outline-reset"
            onClick={handleResetConfig}
            disabled={resetting || saving}
            title="Khôi phục cài đặt mặc định"
          >
            <RotateCcw size={14} className={resetting ? "spin-icon" : ""} />
            <span>{resetting ? "Đang khôi phục..." : "Mặc định"}</span>
          </button>

          <button
            type="button"
            className="btn btn-primary-save"
            onClick={handleSaveAll}
            disabled={saving || resetting}
          >
            {saving ? <div className="spinner-sm" /> : <Save size={15} />}
            <span>{saving ? "Đang lưu..." : "Lưu cấu hình"}</span>
          </button>
        </div>
      </div>

      <div className="config-view-container">
        <div className="config-two-col-grid">
          {/* Column 1: LLM Generation & Reranker Tuning */}
          <div className="config-col-left">
            {/* CARD 1: THAM SỐ MÔ HÌNH SINH (LLM) */}
            <div className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon red">
                  <Flame size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Tham số Mô hình Sinh (LLM Generation)</h3>
                  <p className="config-card-subtitle">Độ sáng tạo, thời gian phản hồi và số lần thử lại</p>
                </div>
              </div>

              <div className="config-card-body">
                {/* Temperature */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Độ ngẫu nhiên / sáng tạo (Temperature)</span>
                      <span className="config-badge-val">{temperature.toFixed(2)}</span>
                    </label>
                    <span className="config-hint-text">
                      {temperature === 0
                        ? "🎯 0.0: Chính xác tuyệt đối, trung thực với quy chế"
                        : temperature < 0.5
                        ? "📘 Thấp: Ổn định, bám sát ngữ cảnh"
                        : "🎨 Cao: Tự do, sáng tạo hơn"}
                    </span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      type="range"
                      min="0.0"
                      max="1.5"
                      step="0.05"
                      className="custom-range-slider"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0.0"
                      max="1.5"
                      step="0.05"
                      className="number-input-box"
                      value={temperature}
                      onChange={(e) => setTemperature(Math.max(0, Math.min(1.5, parseFloat(e.target.value) || 0)))}
                    />
                  </div>
                </div>

                {/* LLM Timeout */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Thời gian chờ tối đa (LLM Timeout)</span>
                      <span className="config-badge-val">{llmTimeout}s</span>
                    </label>
                    <span className="config-hint-text">Tự động ngắt khi gọi model quá thời gian</span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      type="range"
                      min="5"
                      max="90"
                      step="5"
                      className="custom-range-slider"
                      value={llmTimeout}
                      onChange={(e) => setLlmTimeout(parseInt(e.target.value, 10))}
                    />
                    <input
                      type="number"
                      min="5"
                      max="90"
                      className="number-input-box"
                      value={llmTimeout}
                      onChange={(e) => setLlmTimeout(parseInt(e.target.value, 10) || 30)}
                    />
                  </div>
                </div>

                {/* Max Retries */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Số lần thử lại khi gặp sự cố mạng (Max Retries)</span>
                      <span className="config-badge-val">{maxRetries} lần</span>
                    </label>
                  </div>
                  <div className="pill-selector-group">
                    {[0, 1, 2, 3, 5].map((val) => (
                      <button
                        key={val}
                        type="button"
                        className={`pill-sel-btn ${maxRetries === val ? "active" : ""}`}
                        onClick={() => setMaxRetries(val)}
                      >
                        {val} lần
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* CARD 4: TÁI XẾP HẠNG TÀI LIỆU (RERANKER TUNING) */}
            <div className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon purple">
                  <Gauge size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Tái xếp hạng tài liệu (Reranker Tuning)</h3>
                  <p className="config-card-subtitle">Sắp xếp lại các ứng viên truy xuất theo độ tương quan chính xác</p>
                </div>
              </div>

              <div className="config-card-body">
                <div className="config-toggle-header">
                  <div>
                    <span className="config-toggle-title">Kích hoạt Reranker</span>
                    <p className="config-toggle-desc">Sử dụng Cross-Encoder / Cohere Rerank để sắp xếp lại danh sách tài liệu</p>
                  </div>
                  <button
                    type="button"
                    className={`pill-switch ${rerankerEnabled ? "on" : "off"}`}
                    onClick={() => setRerankerEnabled(!rerankerEnabled)}
                  >
                    <span className="pill-switch-thumb" />
                  </button>
                </div>

                {rerankerEnabled && (
                  <div className="sub-settings-panel" style={{ marginTop: "12px" }}>
                    <div className="sub-setting-row">
                      <label>Hệ số ứng viên sơ bộ (Candidate Multiplier): <strong>{candidateMultiplier}x</strong> (Lấy {topK * candidateMultiplier} chunks trước khi Rerank)</label>
                      <input
                        type="range"
                        min="1"
                        max="6"
                        step="1"
                        className="custom-range-slider compact"
                        value={candidateMultiplier}
                        onChange={(e) => setCandidateMultiplier(parseInt(e.target.value, 10))}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Column 2: Retrieval & Guardrails */}
          <div className="config-col-right">
            {/* CARD 2: THAM SỐ TRUY XUẤT & TÌM KIẾM (RETRIEVAL) */}
            <div className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon blue">
                  <Layers size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Tham số Truy xuất & Tìm kiếm (Retrieval & Search)</h3>
                  <p className="config-card-subtitle">Số đoạn văn bản nạp vào prompt và tỷ trọng Hybrid Search</p>
                </div>
              </div>

              <div className="config-card-body">
                {/* Top-K */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Số đoạn văn bản nạp vào LLM (Top-K Chunks)</span>
                      <span className="config-badge-val">{topK} chunks</span>
                    </label>
                    <span className="config-hint-text">Số trích dẫn liên quan nhất đưa vào prompt sinh câu trả lời</span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      type="range"
                      min="1"
                      max="10"
                      step="1"
                      className="custom-range-slider"
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value, 10))}
                    />
                    <input
                      type="number"
                      min="1"
                      max="10"
                      className="number-input-box"
                      value={topK}
                      onChange={(e) => setTopK(Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 4)))}
                    />
                  </div>
                </div>

                {/* Hybrid Search Weight */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Tỷ trọng Hybrid Search (Vector Dense vs BM25 Sparse)</span>
                    </label>
                  </div>

                  <div className="hybrid-ratio-bar">
                    <div
                      className="hybrid-segment vector"
                      style={{ width: `${Math.round(hybridVectorWeight * 100)}%` }}
                    >
                      <span>Vector: {Math.round(hybridVectorWeight * 100)}%</span>
                    </div>
                    <div
                      className="hybrid-segment bm25"
                      style={{ width: `${Math.round((1 - hybridVectorWeight) * 100)}%` }}
                    >
                      <span>BM25: {Math.round((1 - hybridVectorWeight) * 100)}%</span>
                    </div>
                  </div>

                  <div className="slider-with-number" style={{ marginTop: "8px" }}>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      className="custom-range-slider"
                      value={hybridVectorWeight}
                      onChange={(e) => setHybridVectorWeight(parseFloat(e.target.value))}
                    />
                    <span className="config-badge-val">{(hybridVectorWeight * 100).toFixed(0)}%</span>
                  </div>
                  <p className="config-micro-help">
                    Vector giúp hiểu ngữ nghĩa tự nhiên; BM25 giúp tìm kiếm chính xác số điều khoản, tên môn học, học phí.
                  </p>
                </div>

                {/* Multi-Query Expansion */}
                <div className="config-field-group bordered-group">
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title">Mở rộng câu hỏi đa hướng (Multi-Query Expansion)</span>
                      <p className="config-toggle-desc">Tự động phân tách và tạo các câu hỏi phụ để tìm kiếm toàn diện hơn</p>
                    </div>
                    <button
                      type="button"
                      className={`pill-switch ${multiQueryEnabled ? "on" : "off"}`}
                      onClick={() => setMultiQueryEnabled(!multiQueryEnabled)}
                    >
                      <span className="pill-switch-thumb" />
                    </button>
                  </div>

                  {multiQueryEnabled && (
                    <div className="sub-settings-panel">
                      <div className="sub-setting-row">
                        <label>Số lượng câu truy vấn phụ sinh ra (Count): <strong>{multiQueryCount}</strong></label>
                        <input
                          type="range"
                          min="2"
                          max="6"
                          step="1"
                          className="custom-range-slider compact"
                          value={multiQueryCount}
                          onChange={(e) => setMultiQueryCount(parseInt(e.target.value, 10))}
                        />
                      </div>

                      <div className="sub-setting-row-inline">
                        <span>Sử dụng LLM để viết lại truy vấn (Query Rewrite LLM)</span>
                        <button
                          type="button"
                          className={`pill-switch ${multiQueryUseLlm ? "on" : "off"}`}
                          onClick={() => setMultiQueryUseLlm(!multiQueryUseLlm)}
                        >
                          <span className="pill-switch-thumb" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* CARD 3: NGƯỠNG TƯƠNG ĐỒNG & BẢO VỆ (GUARDRAILS & THRESHOLDS) */}
            <div className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon green">
                  <ShieldCheck size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Ngưỡng tương đồng & Kiểm soát an toàn (Guardrails)</h3>
                  <p className="config-card-subtitle">Bộ lọc phạm vi quy chế PTIT và ngưỡng Similarity Threshold</p>
                </div>
              </div>

              <div className="config-card-body">
                {/* Guardrail Scope */}
                <div className="config-field-group bordered-group">
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title">Kiểm soát phạm vi PTIT (Scope Guardrail)</span>
                      <p className="config-toggle-desc">Tự động từ chối lịch sự nếu câu hỏi hoàn toàn không liên quan đến Học viện PTIT</p>
                    </div>
                    <button
                      type="button"
                      className={`pill-switch ${scopeEnabled ? "on" : "off"}`}
                      onClick={() => setScopeEnabled(!scopeEnabled)}
                    >
                      <span className="pill-switch-thumb" />
                    </button>
                  </div>
                </div>

                {/* Similarity Threshold */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Ngưỡng tương đồng Vector tối thiểu (Similarity Threshold)</span>
                      <span className="config-badge-val">{minVectorScore.toFixed(2)}</span>
                    </label>
                    <span className="config-hint-text">Cosine Similarity tối thiểu để chấp nhận chunk</span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      type="range"
                      min="0.10"
                      max="0.80"
                      step="0.02"
                      className="custom-range-slider"
                      value={minVectorScore}
                      onChange={(e) => setMinVectorScore(parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0.10"
                      max="0.80"
                      step="0.02"
                      className="number-input-box"
                      value={minVectorScore}
                      onChange={(e) => setMinVectorScore(Math.max(0.1, Math.min(0.8, parseFloat(e.target.value) || 0.3)))}
                    />
                  </div>
                  <p className="config-micro-help">
                    Đoạn văn có điểm tương đồng dưới {minVectorScore.toFixed(2)} sẽ bị lọc bỏ để tránh trả lời sai sự thật (Hallucination).
                  </p>
                </div>

                {/* BM25 Minimum Score */}
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label">
                      <span>Điểm khớp từ khóa BM25 tối thiểu</span>
                      <span className="config-badge-val">{minBm25Score.toFixed(1)}</span>
                    </label>
                  </div>
                  <div className="slider-with-number">
                    <input
                      type="range"
                      min="0.5"
                      max="6.0"
                      step="0.5"
                      className="custom-range-slider"
                      value={minBm25Score}
                      onChange={(e) => setMinBm25Score(parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0.5"
                      max="6.0"
                      step="0.5"
                      className="number-input-box"
                      value={minBm25Score}
                      onChange={(e) => setMinBm25Score(parseFloat(e.target.value) || 2.0)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
