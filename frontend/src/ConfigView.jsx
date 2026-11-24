import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Info, Loader2, RotateCcw, Undo2 } from "lucide-react";
import { configApi, describeError, errorMessage, queryKeys } from "./api";
import {
  CONFIG_FIELDS,
  DEFAULTS,
  buildConfigPayload,
  calibratedFromConfig,
  formatConfigValue,
  isFieldChanged,
  listConfigChanges,
  listDirtySections,
  mergeConfigDraft,
  valuesFromConfig,
} from "./lib/configDraft";
import { RERANKER_PROVIDER_LABELS, isApiReranker, rerankScoreApplies, shortModelName } from "./settings/pipelineSummary";
import Modal from "./components/Modal";
import SaveBar from "./components/SaveBar";
import { useToast } from "./components/Toast";

// Mặc định cũ của RETRIEVAL_MIN_VECTOR_SCORE: máy chủ coi như chưa đặt (confidence.py).
const LEGACY_VECTOR_DEFAULT = 0.3;
const NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu.";

/** Ô số ngưỡng: chuỗi rỗng/dở dang (khi đang gõ) bỏ qua; bỏ ghi đè đi qua link riêng. */
function parseThreshold(raw, min, max) {
  const value = parseFloat(raw);
  return Number.isNaN(value) ? undefined : Math.max(min, Math.min(max, value));
}

/**
 * Form "Hệ thống trả lời" chia theo bước pipeline: Truy xuất → Xếp hạng lại →
 * Ngưỡng tin cậy → Sinh câu trả lời. Chỉ bước `activeSection` hiển thị; các bước
 * khác vẫn mounted (ẩn) nên bản nháp và thanh lưu là chung cho cả form.
 *
 * `lead` (dải bước) render trong vùng cuộn, phía trên form.
 */
export default function ConfigView({ activeSection = "retrieval", lead = null, onDraftState }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const scrollRef = useRef(null);

  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  const [values, setValues] = useState(DEFAULTS);
  // Ảnh chụp giá trị lần đọc gần nhất từ máy chủ, dùng để biết có thay đổi chưa lưu.
  const [savedSnapshot, setSavedSnapshot] = useState(DEFAULTS);
  const [hydrated, setHydrated] = useState(false);
  const previousServerRef = useRef(null);

  const configQuery = useQuery({
    queryKey: queryKeys.config,
    queryFn: ({ signal }) => configApi.get({ signal }),
  });
  const serverValues = useMemo(
    () => (configQuery.data ? valuesFromConfig(configQuery.data) : null),
    [configQuery.data]
  );
  const calibrated = useMemo(() => calibratedFromConfig(configQuery.data), [configQuery.data]);
  const loading = configQuery.isPending || (!hydrated && !configQuery.error);
  const configError = configQuery.error
    ? describeError(configQuery.error, {
        fallbackTitle: "Không đọc được cấu hình",
        fallbackDetail: "Máy chủ trả về lỗi khi đọc cấu hình.",
      })
    : null;

  // Cache `/config` dùng chung với mục Mô hình: nhận giá trị mới nhưng giữ lại
  // đúng những trường người dùng đang sửa dở ở form này.
  useEffect(() => {
    if (!serverValues) return;
    const previous = previousServerRef.current;

    setValues((current) => {
      if (!previous) return serverValues;
      return mergeConfigDraft(current, previous, serverValues);
    });
    previousServerRef.current = serverValues;
    setSavedSnapshot(serverValues);
    setHydrated(true);
  }, [serverValues]);

  /** Sau khi máy chủ trả cấu hình mới, đồng bộ form ngay cả khi cache không đổi tham chiếu. */
  const applyServerConfig = useCallback((config) => {
    const nextValues = valuesFromConfig(config);
    previousServerRef.current = nextValues;
    setValues(nextValues);
    setSavedSnapshot(nextValues);
    setHydrated(true);
  }, []);

  const set = useCallback((key, value) => {
    setValues((current) => ({ ...current, [key]: value }));
  }, []);

  /**
   * Ngưỡng ghi đè: kéo về đúng giá trị hiệu chỉnh khi đang không ghi đè thì giữ `null`,
   * để không biến một lần chạm thanh trượt thành thay đổi.
   */
  const setThreshold = useCallback(
    (key, value) => {
      if (value === undefined) return;
      const calibratedValue = calibrated[CONFIG_FIELDS[key].calibratedKey];
      const keepCalibrated =
        savedSnapshot[key] === null &&
        value !== null &&
        calibratedValue !== null &&
        Math.abs(value - calibratedValue) < 1e-9;
      set(key, keepCalibrated ? null : value);
    },
    [calibrated, savedSnapshot, set]
  );

  const changes = useMemo(
    () => listConfigChanges(values, savedSnapshot, calibrated),
    [values, savedSnapshot, calibrated]
  );
  const dirtySections = useMemo(
    () => listDirtySections(values, savedSnapshot),
    [values, savedSnapshot]
  );
  const isDirty = changes.length > 0;

  // Danh mục Settings dùng chấm "có thay đổi" và bảng thử dùng bản nháp ngưỡng.
  useEffect(() => {
    onDraftState?.({
      values,
      saved: savedSnapshot,
      calibrated,
      config: configQuery.data ?? null,
      changedKeys: changes.map((change) => change.key),
      dirtySections,
    });
  }, [values, savedSnapshot, calibrated, configQuery.data, changes, dirtySections, onDraftState]);

  // Đổi bước: đưa vùng cuộn về đầu để thấy dải bước và đầu form của bước mới.
  useEffect(() => {
    if (loading) return;
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [activeSection, loading]);

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
      const next = await configApi.reset();
      applyServerConfig(next);
      queryClient.setQueryData(queryKeys.config, next);
      await queryClient.invalidateQueries({ queryKey: queryKeys.config });
      toast.success("Đã khôi phục toàn bộ cấu hình về mặc định.");
      setResetOpen(false);
    } catch (err) {
      toast.error(
        `${errorMessage(err, "Khôi phục cấu hình thất bại.")} Cấu hình chưa được khôi phục.`
      );
    } finally {
      setResetting(false);
    }
  }

  async function handleSaveAll() {
    setSaving(true);
    try {
      // Chỉ gửi trường đã đổi: trường không gửi máy chủ giữ nguyên (PUT nhận payload một phần).
      const next = await configApi.update(buildConfigPayload(values, savedSnapshot));
      applyServerConfig(next);
      queryClient.setQueryData(queryKeys.config, next);
      await queryClient.invalidateQueries({ queryKey: queryKeys.config });
      toast.success("Đã lưu cấu hình RAG lên máy chủ.");
    } catch (err) {
      // Bản trước bắt lỗi rồi hiện toast MÀU XANH "Đã lưu cấu hình cục bộ",
      // trong khi không hề có cơ chế lưu cục bộ nào — cấu hình đã mất trắng.
      toast.error(
        `${errorMessage(err, "Máy chủ từ chối cập nhật cấu hình.")} Cấu hình CHƯA được lưu.`
      );
    } finally {
      setSaving(false);
    }
  }

  const discardChanges = useCallback(() => setValues(savedSnapshot), [savedSnapshot]);

  if (loading) {
    return (
      <div className="model-mgmt-loading" aria-busy="true">
        <div className="model-mgmt-spinner" />
        <p>Đang tải cấu hình hệ thống...</p>
      </div>
    );
  }

  const { temperature, llmTimeout, maxRetries, topK, hybridVectorWeight } = values;

  const changedClass = (key) => (isFieldChanged(values, savedSnapshot, key) ? " is-changed" : "");
  /** "trước: <giá trị>" và nút trả riêng trường về giá trị đã lưu. */
  const changeMark = (key) => {
    if (!isFieldChanged(values, savedSnapshot, key)) return null;
    const was = formatConfigValue(key, savedSnapshot[key], calibrated);
    const label = `Trả "${CONFIG_FIELDS[key].label}" về giá trị đã lưu (${was})`;
    return (
      <span className="config-change-mark">
        <span className="config-was">trước: {was}</span>
        <button
          type="button"
          className="config-revert"
          aria-label={label}
          title={label}
          onClick={() => set(key, savedSnapshot[key])}
        >
          <Undo2 size={13} aria-hidden="true" />
        </button>
      </span>
    );
  };

  const embeddingModel = configQuery.data?.embedding?.model;
  const llmModel = configQuery.data?.llm?.model;
  const rerankerProvider = configQuery.data?.reranker?.provider;
  const rerankerModel = configQuery.data?.reranker?.model;
  const rerankApplies = values.rerankerEnabled && rerankScoreApplies(rerankerProvider);
  // Reranker qua API: điểm liên quan thường trong [0, 1], không phải logit như Cross-Encoder.
  const rerankIsApi = isApiReranker(rerankerProvider);
  const rerankerModelLabel =
    rerankerProvider === "heuristic" ? "Heuristic" : shortModelName(rerankerModel);

  const vectorOverride = values.minVectorScore;
  const vectorShown = vectorOverride ?? calibrated.vector;
  const rerankOverride = values.minRerankScore;
  const rerankShown = rerankOverride ?? calibrated.rerank;

  /** Huy hiệu nguồn ngưỡng + link bỏ ghi đè, dùng chung cho ngưỡng cosine và rerank. */
  const thresholdSource = (override, calibratedValue, modelName) => {
    if (override !== null) return <span className="config-status-badge is-override">Ghi đè</span>;
    if (calibratedValue === null) return null;
    return <span className="config-status-badge is-calibrated">Đã hiệu chỉnh cho {modelName}</span>;
  };
  const clearOverrideLink = (key, override, calibratedValue) => {
    if (override === null) return null;
    return (
      <button type="button" className="config-link-btn" onClick={() => set(key, null)}>
        {calibratedValue !== null
          ? `Dùng giá trị hiệu chỉnh (${Number(calibratedValue).toFixed(2)})`
          : "Bỏ ghi đè (mô hình chưa hiệu chỉnh nên tín hiệu này sẽ bị bỏ qua)"}
      </button>
    );
  };
  const uncalibratedWarning = (override, calibratedValue, modelName) =>
    override === null && calibratedValue === null ? (
      <div className="inline-alert is-warning config-gate-warning" role="note">
        <AlertTriangle size={15} aria-hidden="true" />
        <span>
          Chưa hiệu chỉnh cho {modelName}: chatbot đang bỏ qua tín hiệu này. Nhập ngưỡng để bật lại.
        </span>
      </div>
    ) : null;

  return (
    <div className="config-page-wrapper">
      <div className="config-view-container" ref={scrollRef}>
        {lead}
        {configError && (
          <div className="inline-alert is-warning config-error-alert" role="alert">
            <AlertTriangle size={16} />
            <span>
              {configError.title}. {configError.detail}
              {!configQuery.data &&
                " Các giá trị bên dưới là mặc định của giao diện, KHÔNG phải cấu hình đang chạy."}
            </span>
          </div>
        )}

        <div className="config-form-column">
          {/* -------------------- Truy xuất -------------------- */}
          <section
            className="config-section"
            id="settings-section-retrieval"
            data-settings-section="retrieval"
            aria-labelledby="settings-section-retrieval-title"
            hidden={activeSection !== "retrieval"}
          >
            <header className="config-section-head">
              <h2 className="config-section-title" id="settings-section-retrieval-title">
                Truy xuất
              </h2>
              <p className="config-section-desc">Cách tìm các đoạn tài liệu liên quan tới câu hỏi.</p>
            </header>
            <div className="config-panel-card">
              <div className="config-card-body">
                <div className={`config-field-group${changedClass("topK")}`}>
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-topk">
                      <span>Số đoạn nạp vào LLM (Top-K)</span>
                      <span className="config-badge-val">{topK} đoạn</span>
                    </label>
                    {changeMark("topK")}
                  </div>
                  <span className="config-hint-text">
                    Nhiều đoạn hơn giúp đủ ngữ cảnh nhưng tăng độ trễ và chi phí. Mặc định 4.
                  </span>
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
                      step="1"
                      className="number-input-box"
                      aria-label="Số đoạn nạp vào LLM"
                      value={topK}
                      onChange={(e) =>
                        set("topK", Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 4)))
                      }
                    />
                  </div>
                </div>

                <div className={`config-field-group${changedClass("hybridVectorWeight")}`}>
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-hybrid">
                      <span>Tỷ trọng tìm kiếm lai (Vector so với BM25)</span>
                      <span className="config-badge-val">{Math.round(hybridVectorWeight * 100)}%</span>
                    </label>
                    {changeMark("hybridVectorWeight")}
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
                    Vector giúp hiểu ngữ nghĩa tự nhiên; BM25 giúp tìm chính xác số điều khoản, tên môn học, mức học phí. Mặc định 65%.
                  </p>
                </div>

                <div className={`config-field-group bordered-group${changedClass("multiQueryEnabled")}`}>
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-mq-label">
                        Mở rộng câu hỏi đa hướng
                      </span>
                      <p className="config-toggle-desc">
                        Tự sinh thêm các câu hỏi phụ để tìm kiếm toàn diện hơn
                      </p>
                      {changeMark("multiQueryEnabled")}
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
                      <div className={`sub-setting-row${changedClass("multiQueryCount")}`}>
                        <div className="config-label-row">
                          <label htmlFor="cfg-mq-count">
                            Số truy vấn phụ sinh ra: <strong>{values.multiQueryCount}</strong>
                          </label>
                          {changeMark("multiQueryCount")}
                        </div>
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

                      <div className={`sub-setting-row-inline${changedClass("multiQueryUseLlm")}`}>
                        <div>
                          <span id="cfg-mq-llm-label">Dùng LLM để sinh truy vấn phụ</span>
                          {changeMark("multiQueryUseLlm")}
                        </div>
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

                <div className={`config-field-group bordered-group${changedClass("queryRewriteUseLlm")}`}>
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-rewrite-label">
                        Viết lại câu hỏi bằng LLM
                      </span>
                      <p className="config-toggle-desc">
                        Dùng mô hình ngôn ngữ để viết lại câu hỏi trước khi tìm kiếm. Tắt để tiết kiệm chi phí.
                      </p>
                      {changeMark("queryRewriteUseLlm")}
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={values.queryRewriteUseLlm}
                      aria-labelledby="cfg-rewrite-label"
                      className={`pill-switch ${values.queryRewriteUseLlm ? "on" : "off"}`}
                      onClick={() => set("queryRewriteUseLlm", !values.queryRewriteUseLlm)}
                    >
                      <span className="pill-switch-thumb" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* -------------------- Xếp hạng lại -------------------- */}
          <section
            className="config-section"
            id="settings-section-reranker"
            data-settings-section="reranker"
            aria-labelledby="settings-section-reranker-title"
            hidden={activeSection !== "reranker"}
          >
            <header className="config-section-head">
              <h2 className="config-section-title" id="settings-section-reranker-title">
                Xếp hạng lại
              </h2>
              <p className="config-section-desc">
                Sắp xếp lại các đoạn ứng viên theo độ liên quan trước khi đưa vào mô hình.
              </p>
            </header>
            <div className="config-panel-card">
              <div className="config-card-body">
                <div className={`config-field-group${changedClass("rerankerEnabled")}`}>
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-reranker-label">
                        Bật xếp hạng lại
                      </span>
                      <p className="config-toggle-desc">
                        Dùng mô hình xếp hạng đang chọn để xếp lại danh sách đoạn
                      </p>
                      {changeMark("rerankerEnabled")}
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
                </div>

                <p className="config-model-line">
                  Mô hình: <strong>{rerankerModelLabel}</strong>
                  <span aria-hidden="true">—</span>
                  <a className="config-model-link" href="#settings/models-reranker">
                    Đổi mô hình →
                  </a>
                </p>

                {values.rerankerEnabled && (
                  <div className="sub-settings-panel">
                    <div className={`sub-setting-row${changedClass("candidateMultiplier")}`}>
                      <div className="config-label-row">
                        <label htmlFor="cfg-candidate">
                          Hệ số ứng viên sơ bộ: <strong>{values.candidateMultiplier}×</strong> (lấy{" "}
                          {topK * values.candidateMultiplier} đoạn trước khi xếp lại)
                        </label>
                        {changeMark("candidateMultiplier")}
                      </div>
                      <input
                        id="cfg-candidate"
                        type="range"
                        min="1"
                        max="8"
                        step="1"
                        className="custom-range-slider compact"
                        value={values.candidateMultiplier}
                        onChange={(e) => set("candidateMultiplier", parseInt(e.target.value, 10))}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* -------------------- Ngưỡng tin cậy -------------------- */}
          <section
            className="config-section"
            id="settings-section-gate"
            data-settings-section="gate"
            aria-labelledby="settings-section-gate-title"
            hidden={activeSection !== "gate"}
          >
            <header className="config-section-head">
              <h2 className="config-section-title" id="settings-section-gate-title">
                Ngưỡng tin cậy
              </h2>
              <p className="config-section-desc">
                Quyết định khi nào chatbot từ chối vì không đủ căn cứ.
              </p>
            </header>
            <div className="config-panel-card">
              <div className="config-card-body">
                <div className="config-gate-callout">
                  <Info size={15} aria-hidden="true" />
                  <p>
                    Chatbot so <strong>đoạn khớp nhất</strong> với từng ngưỡng dưới đây. Trượt bất kỳ ngưỡng nào thì
                    trả lời <strong>“{NO_CONTEXT_ANSWER}”</strong> và không gọi mô hình. Dùng nút{" "}
                    <strong>Thử với câu hỏi</strong> ở đầu trang để xem ảnh hưởng trước khi lưu.
                  </p>
                </div>

                <div className={`config-field-group${changedClass("minBm25NormScore")}`}>
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-minbm25norm">
                      <span>Độ khớp từ khóa tối thiểu</span>
                      <span className="config-badge-val">{Number(values.minBm25NormScore).toFixed(2)}</span>
                    </label>
                    {changeMark("minBm25NormScore")}
                  </div>
                  <span className="config-hint-text">
                    Điểm BM25 chuẩn hoá của đoạn khớp nhất, thang 0–1. Cao hơn thì từ chối nhiều hơn. Mặc định 0.25.
                  </span>
                  <div className="slider-with-number">
                    <input
                      id="cfg-minbm25norm"
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      className="custom-range-slider"
                      value={values.minBm25NormScore}
                      onChange={(e) => set("minBm25NormScore", parseFloat(e.target.value))}
                    />
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      className="number-input-box"
                      aria-label="Độ khớp từ khóa tối thiểu"
                      value={values.minBm25NormScore}
                      onChange={(e) =>
                        set("minBm25NormScore", Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))
                      }
                    />
                  </div>
                </div>

                <div className={`config-field-group${changedClass("minVectorScore")}`} data-testid="gate-vector">
                  <div className="config-label-row">
                    <span className="config-field-label">
                      <label htmlFor="cfg-minvec-number">Độ tương đồng ngữ nghĩa tối thiểu</label>
                      {thresholdSource(vectorOverride, calibrated.vector, shortModelName(embeddingModel))}
                    </span>
                    {changeMark("minVectorScore")}
                  </div>
                  <span className="config-hint-text">
                    Cosine giữa câu hỏi và đoạn khớp nhất, theo mô hình nhúng {shortModelName(embeddingModel)}.
                  </span>
                  {uncalibratedWarning(vectorOverride, calibrated.vector, shortModelName(embeddingModel))}
                  <div className="slider-with-number">
                    {vectorShown !== null && (
                      <input
                        id="cfg-minvec"
                        type="range"
                        min="0.1"
                        max="0.8"
                        step="0.01"
                        className="custom-range-slider"
                        aria-label="Thanh trượt độ tương đồng ngữ nghĩa tối thiểu"
                        value={vectorShown}
                        onChange={(e) => setThreshold("minVectorScore", parseFloat(e.target.value))}
                      />
                    )}
                    <input
                      id="cfg-minvec-number"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      className="number-input-box"
                      placeholder="—"
                      value={vectorShown ?? ""}
                      onChange={(e) => setThreshold("minVectorScore", parseThreshold(e.target.value, 0, 1))}
                    />
                  </div>
                  {clearOverrideLink("minVectorScore", vectorOverride, calibrated.vector)}
                  {vectorOverride !== null && Math.abs(vectorOverride - LEGACY_VECTOR_DEFAULT) < 1e-9 && (
                    <p className="config-micro-help">
                      0.30 là mặc định cũ chưa hiệu chỉnh; máy chủ bỏ qua giá trị này và giữ ngưỡng hiện tại.
                    </p>
                  )}
                </div>

                {rerankApplies ? (
                  <div className={`config-field-group${changedClass("minRerankScore")}`} data-testid="gate-rerank">
                    <div className="config-label-row">
                      <span className="config-field-label">
                        <label htmlFor="cfg-minrerank-number">Điểm xếp hạng lại tối thiểu</label>
                        {thresholdSource(rerankOverride, calibrated.rerank, shortModelName(rerankerModel))}
                      </span>
                      {changeMark("minRerankScore")}
                    </div>
                    <span className="config-hint-text">
                      {rerankIsApi
                        ? `Điểm liên quan (0–1) do ${RERANKER_PROVIDER_LABELS[rerankerProvider]} trả về cho đoạn khớp nhất. Chưa có giá trị hiệu chỉnh: nhập ngưỡng để dùng tín hiệu này.`
                        : "Điểm Cross-Encoder (logit) của đoạn khớp nhất sau khi xếp hạng lại."}
                    </span>
                    {uncalibratedWarning(rerankOverride, calibrated.rerank, shortModelName(rerankerModel))}
                    <div className="slider-with-number">
                      {rerankShown !== null && (
                        <input
                          id="cfg-minrerank"
                          type="range"
                          min={rerankIsApi ? "0" : "-10"}
                          max={rerankIsApi ? "1" : "10"}
                          step={rerankIsApi ? "0.01" : "0.05"}
                          className="custom-range-slider"
                          aria-label="Thanh trượt điểm xếp hạng lại tối thiểu"
                          value={rerankShown}
                          onChange={(e) => setThreshold("minRerankScore", parseFloat(e.target.value))}
                        />
                      )}
                      <input
                        id="cfg-minrerank-number"
                        type="number"
                        min="-20"
                        max="20"
                        step="0.05"
                        className="number-input-box"
                        placeholder="—"
                        value={rerankShown ?? ""}
                        onChange={(e) => setThreshold("minRerankScore", parseThreshold(e.target.value, -20, 20))}
                      />
                    </div>
                    {clearOverrideLink("minRerankScore", rerankOverride, calibrated.rerank)}
                  </div>
                ) : (
                  <p className="config-gate-na" data-testid="gate-rerank-na">
                    <span>Điểm xếp hạng lại tối thiểu:</span>{" "}
                    {values.rerankerEnabled
                      ? `không áp dụng với ${RERANKER_PROVIDER_LABELS[rerankerProvider] ?? rerankerProvider ?? "reranker hiện tại"}, chỉ dùng khi xếp hạng bằng Cross-Encoder hoặc dịch vụ rerank qua API.`
                      : "không áp dụng khi tắt xếp hạng lại."}
                  </p>
                )}

                <div className={`config-field-group bordered-group${changedClass("scopeEnabled")}`}>
                  <div className="config-toggle-header">
                    <div>
                      <span className="config-toggle-title" id="cfg-scope-label">
                        Chặn yêu cầu không an toàn
                      </span>
                      <p className="config-toggle-desc">
                        Từ chối câu chèn lệnh, yêu cầu viết code, sáng tác hoặc làm bài tập
                      </p>
                      {changeMark("scopeEnabled")}
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
              </div>
            </div>
          </section>

          {/* -------------------- Sinh câu trả lời -------------------- */}
          <section
            className="config-section"
            id="settings-section-generation"
            data-settings-section="generation"
            aria-labelledby="settings-section-generation-title"
            hidden={activeSection !== "generation"}
          >
            <header className="config-section-head">
              <h2 className="config-section-title" id="settings-section-generation-title">
                Sinh câu trả lời
              </h2>
              <p className="config-section-desc">
                Độ ngẫu nhiên, thời gian chờ và số lần thử lại của mô hình ngôn ngữ.
              </p>
            </header>
            <div className="config-panel-card">
              <div className="config-card-body">
                <p className="config-model-line">
                  Mô hình: <strong>{shortModelName(llmModel)}</strong>
                  <span aria-hidden="true">—</span>
                  <a className="config-model-link" href="#settings/models-llm">
                    Đổi mô hình →
                  </a>
                </p>

                <div className={`config-field-group${changedClass("temperature")}`}>
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-temperature">
                      <span>Độ ngẫu nhiên (Temperature)</span>
                      <span className="config-badge-val">{Number(temperature).toFixed(2)}</span>
                    </label>
                    {changeMark("temperature")}
                  </div>
                  <span className="config-hint-text">
                    {temperature === 0
                      ? "0: bám sát quy chế, phù hợp hỏi đáp quy định. Mặc định 0."
                      : temperature < 0.5
                      ? "Thấp: ổn định, bám sát ngữ cảnh. Mặc định 0."
                      : "Cao: diễn đạt tự do hơn nhưng dễ lệch khỏi tài liệu. Mặc định 0."}
                  </span>
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

                <div className={`config-field-group${changedClass("llmTimeout")}`}>
                  <div className="config-label-row">
                    <label className="config-field-label" htmlFor="cfg-timeout">
                      <span>Thời gian chờ tối đa</span>
                      <span className="config-badge-val">{llmTimeout}s</span>
                    </label>
                    {changeMark("llmTimeout")}
                  </div>
                  <span className="config-hint-text">Tự ngắt khi gọi mô hình quá lâu. Mặc định 30 giây.</span>
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
                      step="5"
                      className="number-input-box"
                      aria-label="Thời gian chờ tối đa, tính bằng giây"
                      value={llmTimeout}
                      onChange={(e) => set("llmTimeout", parseInt(e.target.value, 10) || 30)}
                    />
                  </div>
                </div>

                <fieldset className={`config-field-group${changedClass("maxRetries")}`}>
                  <legend className="config-label-row">
                    <span className="config-field-label">
                      <span>Số lần thử lại khi lỗi mạng</span>
                      <span className="config-badge-val">{maxRetries} lần</span>
                    </span>
                    {changeMark("maxRetries")}
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
            </div>
          </section>

          <section className="config-danger-zone" aria-labelledby="cfg-danger-title">
            <div>
              <h3 id="cfg-danger-title">Vùng nguy hiểm</h3>
              <p>
                Khôi phục mặc định xoá toàn bộ cấu hình RAG đã lưu trên máy chủ, đưa mọi tham số về giá trị ban đầu.
                Không thể hoàn tác.
              </p>
            </div>
            <button
              type="button"
              className="config-danger-btn"
              onClick={() => setResetOpen(true)}
              disabled={resetting || saving}
            >
              <RotateCcw size={14} />
              <span>Khôi phục mặc định…</span>
            </button>
          </section>
        </div>
      </div>

      <SaveBar
        changes={changes}
        onDiscard={discardChanges}
        onSave={handleSaveAll}
        saving={saving}
        disabled={resetting}
      />

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
