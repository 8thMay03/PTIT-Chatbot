import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Flame,
  Gauge,
  Layers,
  Loader2,
  RotateCcw,
  Save,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import Modal from "./components/Modal";
import { useToast } from "./components/Toast";

const DEFAULTS = {
  temperature: 0.0,
  llmTimeout: 30,
  maxRetries: 2,
  topK: 4,
  hybridVectorWeight: 0.65,
  multiQueryEnabled: true,
  multiQueryCount: 3,
  multiQueryUseLlm: false,
  scopeEnabled: true,
  minVectorScore: 0.3,
  minBm25Score: 2.0,
  rerankerEnabled: true,
  candidateMultiplier: 3,
};

export default function ConfigView() {
  const toast = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [loadError, setLoadError] = useState("");

  const [values, setValues] = useState(DEFAULTS);
  // Ảnh chụp giá trị lần đọc gần nhất từ máy chủ, dùng để biết có thay đổi chưa lưu.
  const savedSnapshot = useRef(DEFAULTS);

  const set = useCallback((key, value) => {
    setValues((current) => ({ ...current, [key]: value }));
  }, []);

  const isDirty = useMemo(
    () => JSON.stringify(values) !== JSON.stringify(savedSnapshot.current),
    [values]
  );

  const fetchBackendConfig = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const res = await fetch(`${API_BASE_URL}/config`);
      if (!res.ok) throw new Error("Máy chủ trả về lỗi khi đọc cấu hình.");
      const data = await res.json();

      const next = {
        temperature: data.llm?.temperature ?? DEFAULTS.temperature,
        llmTimeout: data.llm?.timeout ?? DEFAULTS.llmTimeout,
        maxRetries: data.llm?.max_retries ?? DEFAULTS.maxRetries,
        topK: data.retrieval?.top_k ?? DEFAULTS.topK,
        hybridVectorWeight: data.retrieval?.hybrid_vector_weight ?? DEFAULTS.hybridVectorWeight,
        multiQueryEnabled: Boolean(data.retrieval?.multi_query_enabled),
        multiQueryCount: data.retrieval?.multi_query_count ?? DEFAULTS.multiQueryCount,
        multiQueryUseLlm: Boolean(data.retrieval?.multi_query_use_llm),
        scopeEnabled: Boolean(data.guardrails?.scope_enabled),
        minVectorScore: data.guardrails?.min_vector_score ?? DEFAULTS.minVectorScore,
        minBm25Score: data.guardrails?.min_bm25_score ?? DEFAULTS.minBm25Score,
        rerankerEnabled: Boolean(data.reranker?.enabled),
        candidateMultiplier: data.reranker?.candidate_multiplier ?? DEFAULTS.candidateMultiplier,
      };

      setValues(next);
      savedSnapshot.current = next;
    } catch (err) {
      // Bản trước chỉ console.warn rồi hiện giá trị mặc định như thể đó là cấu
      // hình thật của hệ thống — người dùng không có cách nào biết là đã lỗi.
      setLoadError(
        err instanceof TypeError
          ? "Không kết nối được máy chủ. Các giá trị bên dưới là mặc định của giao diện, KHÔNG phải cấu hình đang chạy."
          : `${err.message} Các giá trị bên dưới là mặc định của giao diện, KHÔNG phải cấu hình đang chạy.`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBackendConfig();
  }, [fetchBackendConfig]);

  // Cảnh báo khi rời trang mà còn thay đổi chưa lưu
  useEffect(() => {
    if (!isDirty) return undefined;
    function onBeforeUnload(event) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);

  async function handleResetConfig() {
    setResetting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/config/reset`, { method: "POST" });
      if (!res.ok) throw new Error("Máy chủ từ chối yêu cầu khôi phục.");
      await fetchBackendConfig();
      toast.success("Đã khôi phục toàn bộ cấu hình về mặc định.");
      setResetOpen(false);
    } catch (err) {
      toast.error(
        err instanceof TypeError
          ? "Không kết nối được máy chủ. Cấu hình chưa được khôi phục."
          : err.message || "Khôi phục cấu hình thất bại."
      );
    } finally {
      setResetting(false);
    }
  }

  async function handleSaveAll() {
    setSaving(true);
    try {
      const payload = {
        llm: {
          temperature: Number(values.temperature),
          timeout: Number(values.llmTimeout),
          max_retries: Number(values.maxRetries),
        },
        reranker: {
          enabled: values.rerankerEnabled,
          candidate_multiplier: Number(values.candidateMultiplier),
        },
        retrieval: {
          multi_query_enabled: values.multiQueryEnabled,
          multi_query_count: Number(values.multiQueryCount),
          multi_query_use_llm: values.multiQueryUseLlm,
          top_k: Number(values.topK),
          hybrid_vector_weight: Number(values.hybridVectorWeight),
        },
        guardrails: {
          scope_enabled: values.scopeEnabled,
          min_vector_score: Number(values.minVectorScore),
          min_bm25_score: Number(values.minBm25Score),
        },
      };

      const res = await fetch(`${API_BASE_URL}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail || "Máy chủ từ chối cập nhật cấu hình.");
      }

      savedSnapshot.current = values;
      setLoadError("");
      toast.success("Đã lưu cấu hình RAG lên máy chủ.");
    } catch (err) {
      // Bản trước bắt lỗi rồi hiện toast MÀU XANH "Đã lưu cấu hình cục bộ",
      // trong khi không hề có cơ chế lưu cục bộ nào — cấu hình đã mất trắng.
      toast.error(
        err instanceof TypeError
          ? "Không kết nối được máy chủ. Cấu hình CHƯA được lưu."
          : `${err.message} Cấu hình CHƯA được lưu.`
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="model-mgmt-loading" aria-busy="true">
        <div className="model-mgmt-spinner" />
        <p>Đang tải cấu hình hệ thống...</p>
      </div>
    );
  }

  const { temperature, llmTimeout, maxRetries, topK, hybridVectorWeight } = values;

  return (
    <div className="config-page-wrapper">
      <div className="settings-subtabs-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box">
            <Sliders size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Cấu hình hệ thống &amp; tham số RAG</h2>
            <p className="config-main-desc">
              Tinh chỉnh độ ngẫu nhiên, số đoạn nạp vào LLM, ngưỡng tương đồng và tỷ trọng tìm kiếm lai.
            </p>
          </div>
        </div>

        <div className="settings-header-actions">
          {isDirty && (
            <span className="unsaved-badge" role="status">
              Có thay đổi chưa lưu
            </span>
          )}

          <button
            type="button"
            className="btn btn-outline-reset"
            onClick={() => setResetOpen(true)}
            disabled={resetting || saving}
          >
            <RotateCcw size={14} />
            <span>Mặc định</span>
          </button>

          <button
            type="button"
            className="btn btn-primary-save"
            onClick={handleSaveAll}
            disabled={saving || resetting || !isDirty}
          >
            {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
            <span>{saving ? "Đang lưu..." : "Lưu cấu hình"}</span>
          </button>
        </div>
      </div>

      {loadError && (
        <div className="inline-alert is-warning" role="alert" style={{ margin: "0 24px 16px" }}>
          <AlertTriangle size={16} />
          <span>{loadError}</span>
        </div>
      )}

      <div className="config-view-container">
        <div className="config-two-col-grid">
          {/* -------------------- Cột trái -------------------- */}
          <div className="config-col-left">
            <section className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon red">
                  <Flame size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Tham số mô hình sinh (LLM)</h3>
                  <p className="config-card-subtitle">Độ sáng tạo, thời gian chờ và số lần thử lại</p>
                </div>
              </div>

              <div className="config-card-body">
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-temperature">
                      <span>Độ ngẫu nhiên (Temperature)</span>
                      <span className="config-badge-val">{Number(temperature).toFixed(2)}</span>
                    </label>
                    <span className="config-hint-text">
                      {temperature === 0
                        ? "Chính xác tuyệt đối, bám sát quy chế"
                        : temperature < 0.5
                        ? "Thấp: ổn định, bám sát ngữ cảnh"
                        : "Cao: tự do và sáng tạo hơn"}
                    </span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      id="cfg-temperature"
                      type="range"
                      min="0"
                      max="1.5"
                      step="0.05"
                      className="custom-range-slider"
                      value={temperature}
                      onChange={(e) => set("temperature", parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0"
                      max="1.5"
                      step="0.05"
                      className="number-input-box"
                      aria-label="Giá trị Temperature"
                      value={temperature}
                      onChange={(e) =>
                        set("temperature", Math.max(0, Math.min(1.5, parseFloat(e.target.value) || 0)))
                      }
                    />
                  </div>
                </div>

                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-timeout">
                      <span>Thời gian chờ tối đa</span>
                      <span className="config-badge-val">{llmTimeout}s</span>
                    </label>
                    <span className="config-hint-text">Tự ngắt khi gọi mô hình quá lâu</span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      id="cfg-timeout"
                      type="range"
                      min="5"
                      max="90"
                      step="5"
                      className="custom-range-slider"
                      value={llmTimeout}
                      onChange={(e) => set("llmTimeout", parseInt(e.target.value, 10))}
                    />
                    <input
                      type="number"
                      min="5"
                      max="90"
                      className="number-input-box"
                      aria-label="Thời gian chờ tối đa, tính bằng giây"
                      value={llmTimeout}
                      onChange={(e) => set("llmTimeout", parseInt(e.target.value, 10) || 30)}
                    />
                  </div>
                </div>

                <fieldset className="config-field-group">
                  <legend className="config-field-label">
                    <span>Số lần thử lại khi lỗi mạng</span>
                    <span className="config-badge-val">{maxRetries} lần</span>
                  </legend>
                  <div className="pill-selector-group">
                    {[0, 1, 2, 3, 5].map((val) => (
                      <button
                        key={val}
                        type="button"
                        className={`pill-sel-btn ${maxRetries === val ? "active" : ""}`}
                        aria-pressed={maxRetries === val}
                        onClick={() => set("maxRetries", val)}
                      >
                        {val} lần
                      </button>
                    ))}
                  </div>
                </fieldset>
              </div>
            </section>

            <section className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon purple">
                  <Gauge size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Tái xếp hạng tài liệu (Reranker)</h3>
                  <p className="config-card-subtitle">
                    Sắp xếp lại các đoạn ứng viên theo độ liên quan chính xác hơn
                  </p>
                </div>
              </div>

              <div className="config-card-body">
                <div className="config-toggle-header">
                  <div>
                    <span className="config-toggle-title" id="cfg-reranker-label">
                      Kích hoạt Reranker
                    </span>
                    <p className="config-toggle-desc">
                      Dùng Cross-Encoder hoặc Cohere Rerank để xếp lại danh sách đoạn
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={values.rerankerEnabled}
                    aria-labelledby="cfg-reranker-label"
                    className={`pill-switch ${values.rerankerEnabled ? "on" : "off"}`}
                    onClick={() => set("rerankerEnabled", !values.rerankerEnabled)}
                  >
                    <span className="pill-switch-thumb" />
                  </button>
                </div>

                {values.rerankerEnabled && (
                  <div className="sub-settings-panel" style={{ marginTop: 12 }}>
                    <div className="sub-setting-row">
                      <label htmlFor="cfg-candidate">
                        Hệ số ứng viên sơ bộ: <strong>{values.candidateMultiplier}×</strong> (lấy{" "}
                        {topK * values.candidateMultiplier} đoạn trước khi xếp lại)
                      </label>
                      <input
                        id="cfg-candidate"
                        type="range"
                        min="1"
                        max="6"
                        step="1"
                        className="custom-range-slider compact"
                        value={values.candidateMultiplier}
                        onChange={(e) => set("candidateMultiplier", parseInt(e.target.value, 10))}
                      />
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* -------------------- Cột phải -------------------- */}
          <div className="config-col-right">
            <section className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon blue">
                  <Layers size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Truy xuất &amp; tìm kiếm</h3>
                  <p className="config-card-subtitle">Số đoạn nạp vào prompt và tỷ trọng tìm kiếm lai</p>
                </div>
              </div>

              <div className="config-card-body">
                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-topk">
                      <span>Số đoạn nạp vào LLM (Top-K)</span>
                      <span className="config-badge-val">{topK} đoạn</span>
                    </label>
                    <span className="config-hint-text">
                      Số trích dẫn liên quan nhất đưa vào prompt sinh câu trả lời
                    </span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      id="cfg-topk"
                      type="range"
                      min="1"
                      max="10"
                      step="1"
                      className="custom-range-slider"
                      value={topK}
                      onChange={(e) => set("topK", parseInt(e.target.value, 10))}
                    />
                    <input
                      type="number"
                      min="1"
                      max="10"
                      className="number-input-box"
                      aria-label="Số đoạn nạp vào LLM"
                      value={topK}
                      onChange={(e) =>
                        set("topK", Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 4)))
                      }
                    />
                  </div>
                </div>

                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-hybrid">
                      <span>Tỷ trọng tìm kiếm lai (Vector so với BM25)</span>
                      <span className="config-badge-val">{Math.round(hybridVectorWeight * 100)}%</span>
                    </label>
                  </div>

                  <div className="hybrid-ratio-bar" aria-hidden="true">
                    <div className="hybrid-segment vector" style={{ width: `${Math.round(hybridVectorWeight * 100)}%` }}>
                      <span>Vector {Math.round(hybridVectorWeight * 100)}%</span>
                    </div>
                    <div
                      className="hybrid-segment bm25"
                      style={{ width: `${Math.round((1 - hybridVectorWeight) * 100)}%` }}
                    >
                      <span>BM25 {Math.round((1 - hybridVectorWeight) * 100)}%</span>
                    </div>
                  </div>

                  <div className="slider-with-number" style={{ marginTop: 8 }}>
                    <input
                      id="cfg-hybrid"
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      className="custom-range-slider"
                      value={hybridVectorWeight}
                      onChange={(e) => set("hybridVectorWeight", parseFloat(e.target.value))}
                    />
                  </div>
                  <p className="config-micro-help">
                    Vector giúp hiểu ngữ nghĩa tự nhiên; BM25 giúp tìm chính xác số điều khoản, tên môn học, mức học phí.
                  </p>
                </div>

                <div className="config-field-group bordered-group">
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-mq-label">
                        Mở rộng câu hỏi đa hướng
                      </span>
                      <p className="config-toggle-desc">
                        Tự sinh thêm các câu hỏi phụ để tìm kiếm toàn diện hơn
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={values.multiQueryEnabled}
                      aria-labelledby="cfg-mq-label"
                      className={`pill-switch ${values.multiQueryEnabled ? "on" : "off"}`}
                      onClick={() => set("multiQueryEnabled", !values.multiQueryEnabled)}
                    >
                      <span className="pill-switch-thumb" />
                    </button>
                  </div>

                  {values.multiQueryEnabled && (
                    <div className="sub-settings-panel">
                      <div className="sub-setting-row">
                        <label htmlFor="cfg-mq-count">
                          Số truy vấn phụ sinh ra: <strong>{values.multiQueryCount}</strong>
                        </label>
                        <input
                          id="cfg-mq-count"
                          type="range"
                          min="2"
                          max="6"
                          step="1"
                          className="custom-range-slider compact"
                          value={values.multiQueryCount}
                          onChange={(e) => set("multiQueryCount", parseInt(e.target.value, 10))}
                        />
                      </div>

                      <div className="sub-setting-row-inline">
                        <span id="cfg-mq-llm-label">Dùng LLM để viết lại truy vấn</span>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={values.multiQueryUseLlm}
                          aria-labelledby="cfg-mq-llm-label"
                          className={`pill-switch ${values.multiQueryUseLlm ? "on" : "off"}`}
                          onClick={() => set("multiQueryUseLlm", !values.multiQueryUseLlm)}
                        >
                          <span className="pill-switch-thumb" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="config-panel-card">
              <div className="config-card-header">
                <div className="config-card-icon green">
                  <ShieldCheck size={17} />
                </div>
                <div>
                  <h3 className="config-card-title">Ngưỡng tương đồng &amp; kiểm soát an toàn</h3>
                  <p className="config-card-subtitle">Bộ lọc phạm vi quy chế PTIT và ngưỡng chấp nhận đoạn</p>
                </div>
              </div>

              <div className="config-card-body">
                <div className="config-field-group bordered-group">
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-scope-label">
                        Kiểm soát phạm vi PTIT
                      </span>
                      <p className="config-toggle-desc">
                        Từ chối lịch sự khi câu hỏi không liên quan đến Học viện
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={values.scopeEnabled}
                      aria-labelledby="cfg-scope-label"
                      className={`pill-switch ${values.scopeEnabled ? "on" : "off"}`}
                      onClick={() => set("scopeEnabled", !values.scopeEnabled)}
                    >
                      <span className="pill-switch-thumb" />
                    </button>
                  </div>
                </div>

                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-minvec">
                      <span>Ngưỡng tương đồng vector tối thiểu</span>
                      <span className="config-badge-val">{Number(values.minVectorScore).toFixed(2)}</span>
                    </label>
                    <span className="config-hint-text">Cosine similarity tối thiểu để chấp nhận một đoạn</span>
                  </div>
                  <div className="slider-with-number">
                    <input
                      id="cfg-minvec"
                      type="range"
                      min="0.1"
                      max="0.8"
                      step="0.02"
                      className="custom-range-slider"
                      value={values.minVectorScore}
                      onChange={(e) => set("minVectorScore", parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0.1"
                      max="0.8"
                      step="0.02"
                      className="number-input-box"
                      aria-label="Ngưỡng tương đồng vector tối thiểu"
                      value={values.minVectorScore}
                      onChange={(e) =>
                        set("minVectorScore", Math.max(0.1, Math.min(0.8, parseFloat(e.target.value) || 0.3)))
                      }
                    />
                  </div>
                  <p className="config-micro-help">
                    Đoạn có điểm dưới {Number(values.minVectorScore).toFixed(2)} sẽ bị loại để tránh trả lời sai sự thật.
                  </p>
                </div>

                <div className="config-field-group">
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-minbm25">
                      <span>Điểm khớp từ khóa BM25 tối thiểu</span>
                      <span className="config-badge-val">{Number(values.minBm25Score).toFixed(1)}</span>
                    </label>
                  </div>
                  <div className="slider-with-number">
                    <input
                      id="cfg-minbm25"
                      type="range"
                      min="0.5"
                      max="6"
                      step="0.5"
                      className="custom-range-slider"
                      value={values.minBm25Score}
                      onChange={(e) => set("minBm25Score", parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0.5"
                      max="6"
                      step="0.5"
                      className="number-input-box"
                      aria-label="Điểm khớp từ khóa BM25 tối thiểu"
                      value={values.minBm25Score}
                      onChange={(e) => set("minBm25Score", parseFloat(e.target.value) || 2.0)}
                    />
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>

      <Modal
        open={resetOpen}
        onClose={() => !resetting && setResetOpen(false)}
        title="Khôi phục cấu hình mặc định?"
        description="Toàn bộ tham số RAG trên máy chủ sẽ trở về giá trị ban đầu. Thao tác này không thể hoàn tác."
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setResetOpen(false)} disabled={resetting}>
              Hủy
            </button>
            <button type="button" className="danger-btn" onClick={handleResetConfig} disabled={resetting}>
              {resetting ? <Loader2 size={15} className="spin" /> : <RotateCcw size={15} />}
              Khôi phục
            </button>
          </>
        }
      />
    </div>
  );
}
