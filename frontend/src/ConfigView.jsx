import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Flame,
  Gauge,
  Layers,
  Loader2,
  RotateCcw,
  Save,
  ShieldCheck,
  Undo2,
} from "lucide-react";
import { configApi, describeError, errorMessage, queryKeys } from "./api";
import { mergeConfigDraft } from "./lib/configDraft";
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

// Nhãn ngắn của từng trường, dùng cho thanh lưu ("Đã sửa: Top-K, Temperature").
const FIELD_LABELS = {
  temperature: "Temperature",
  llmTimeout: "Thời gian chờ",
  maxRetries: "Số lần thử lại",
  topK: "Top-K",
  hybridVectorWeight: "Tỷ trọng tìm kiếm lai",
  multiQueryEnabled: "Mở rộng câu hỏi",
  multiQueryCount: "Số truy vấn phụ",
  multiQueryUseLlm: "Viết lại bằng LLM",
  scopeEnabled: "Kiểm soát phạm vi",
  minVectorScore: "Ngưỡng vector",
  minBm25Score: "Ngưỡng BM25",
  rerankerEnabled: "Reranker",
  candidateMultiplier: "Hệ số ứng viên",
};

// Các nhóm đi theo đúng thứ tự xử lý của pipeline RAG.
const SECTIONS = [
  {
    id: "retrieval",
    title: "Truy xuất & tìm kiếm",
    description: "Lấy các đoạn tài liệu liên quan tới câu hỏi bằng tìm kiếm lai Vector + BM25.",
    icon: Layers,
    tone: "blue",
    fields: ["topK", "hybridVectorWeight", "multiQueryEnabled", "multiQueryCount", "multiQueryUseLlm"],
  },
  {
    id: "reranker",
    title: "Tái xếp hạng (Reranker)",
    description: "Chấm lại độ liên quan của các đoạn ứng viên trước khi đưa vào mô hình.",
    icon: Gauge,
    tone: "purple",
    fields: ["rerankerEnabled", "candidateMultiplier"],
  },
  {
    id: "guardrails",
    title: "Ngưỡng & kiểm soát an toàn",
    description: "Loại đoạn kém liên quan và từ chối câu hỏi ngoài phạm vi Học viện.",
    icon: ShieldCheck,
    tone: "green",
    fields: ["scopeEnabled", "minVectorScore", "minBm25Score"],
  },
  {
    id: "llm",
    title: "Mô hình sinh câu trả lời",
    description: "Độ sáng tạo, thời gian chờ và số lần thử lại khi gọi LLM.",
    icon: Flame,
    tone: "red",
    fields: ["temperature", "llmTimeout", "maxRetries"],
  },
];

function valuesFromConfig(data) {
  return {
    temperature: data?.llm?.temperature ?? DEFAULTS.temperature,
    llmTimeout: data?.llm?.timeout ?? DEFAULTS.llmTimeout,
    maxRetries: data?.llm?.max_retries ?? DEFAULTS.maxRetries,
    topK: data?.retrieval?.top_k ?? DEFAULTS.topK,
    hybridVectorWeight:
      data?.retrieval?.hybrid_vector_weight ?? DEFAULTS.hybridVectorWeight,
    multiQueryEnabled: Boolean(data?.retrieval?.multi_query_enabled),
    multiQueryCount:
      data?.retrieval?.multi_query_count ?? DEFAULTS.multiQueryCount,
    multiQueryUseLlm: Boolean(data?.retrieval?.multi_query_use_llm),
    scopeEnabled: Boolean(data?.guardrails?.scope_enabled),
    minVectorScore:
      data?.guardrails?.min_vector_score ?? DEFAULTS.minVectorScore,
    minBm25Score: data?.guardrails?.min_bm25_score ?? DEFAULTS.minBm25Score,
    rerankerEnabled: Boolean(data?.reranker?.enabled),
    candidateMultiplier:
      data?.reranker?.candidate_multiplier ?? DEFAULTS.candidateMultiplier,
  };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function temperatureHint(value) {
  if (value === 0) return "Chính xác tuyệt đối, bám sát quy chế";
  if (value < 0.5) return "Thấp: ổn định, bám sát ngữ cảnh";
  return "Cao: tự do và sáng tạo hơn";
}

/** Ô số đi kèm thanh trượt: cho gõ tự do, chỉ nhận giá trị hợp lệ, kẹp về khoảng khi rời ô. */
function NumberBox({ value, min, max, step, unit, label, disabled, onChange }) {
  const [text, setText] = useState(String(value));

  useEffect(() => {
    // Đồng bộ khi giá trị đổi từ thanh trượt/máy chủ; giữ nguyên chuỗi đang gõ dở như "0."
    if (Number(text) !== value || text === "") setText(String(value));
  }, [value]);

  function commit() {
    const parsed = parseFloat(text);
    const next = Number.isFinite(parsed) ? clamp(parsed, min, max) : value;
    setText(String(next));
    if (next !== value) onChange(next);
  }

  return (
    <div className={`cfg-number ${disabled ? "is-disabled" : ""}`}>
      <input
        type="number"
        inputMode="decimal"
        min={min}
        max={max}
        step={step}
        aria-label={label}
        disabled={disabled}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          const parsed = parseFloat(e.target.value);
          if (Number.isFinite(parsed) && parsed >= min && parsed <= max) onChange(parsed);
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
        }}
      />
      {unit && <span className="cfg-number-unit">{unit}</span>}
    </div>
  );
}

/** Thanh trượt có nhãn min/max và ô nhập số (tuỳ chọn). */
function SliderControl({
  id,
  value,
  min,
  max,
  step,
  onChange,
  disabled,
  numberLabel,
  unit,
  formatBound = (v) => v,
  integer = false,
}) {
  const percent = ((value - min) / (max - min)) * 100;
  return (
    <div className="cfg-slider">
      <div className="cfg-slider-track">
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          style={{ "--cfg-fill": `${clamp(percent, 0, 100)}%` }}
          onChange={(e) =>
            onChange(integer ? parseInt(e.target.value, 10) : parseFloat(e.target.value))
          }
        />
        <div className="cfg-slider-bounds" aria-hidden="true">
          <span>{formatBound(min)}</span>
          <span>{formatBound(max)}</span>
        </div>
      </div>
      {numberLabel && (
        <NumberBox
          value={value}
          min={min}
          max={max}
          step={step}
          unit={unit}
          label={numberLabel}
          disabled={disabled}
          onChange={onChange}
        />
      )}
    </div>
  );
}

function Switch({ checked, onChange, labelledBy, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      disabled={disabled}
      className={`pill-switch cfg-switch ${checked ? "on" : "off"}`}
      onClick={() => onChange(!checked)}
    >
      <span className="pill-switch-thumb" />
    </button>
  );
}

/**
 * Một dòng cài đặt: cột trái là nhãn + giải thích, cột phải là điều khiển.
 * Khi giá trị khác bản đã lưu thì hiện chấm "Đã sửa" và nút hoàn tác riêng trường đó.
 */
function SettingRow({
  labelId,
  htmlFor,
  label,
  description,
  value,
  dirty,
  onRevert,
  nested = false,
  disabled = false,
  inline = false,
  children,
}) {
  const LabelTag = htmlFor ? "label" : "span";
  return (
    <div
      className={`cfg-row ${inline ? "is-inline" : ""} ${nested ? "is-nested" : ""} ${
        disabled ? "is-disabled" : ""
      } ${dirty ? "is-dirty" : ""}`}
    >
      <div className="cfg-row-info">
        <div className="cfg-row-title">
          <LabelTag id={labelId} htmlFor={htmlFor} className="cfg-row-label">
            {label}
          </LabelTag>
          {value !== undefined && <span className="cfg-value-chip">{value}</span>}
          {dirty && (
            <button
              type="button"
              className="cfg-revert-btn"
              onClick={onRevert}
              title="Hoàn tác về giá trị đã lưu"
              aria-label={`Hoàn tác ${label} về giá trị đã lưu`}
            >
              <span className="cfg-dirty-dot" aria-hidden="true" />
              <span>Đã sửa</span>
              <Undo2 size={12} aria-hidden="true" />
            </button>
          )}
        </div>
        {description && <p className="cfg-row-desc">{description}</p>}
      </div>
      <div className="cfg-row-control">{children}</div>
    </div>
  );
}

export default function ConfigView() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [activeSection, setActiveSection] = useState(SECTIONS[0].id);

  const [values, setValues] = useState(DEFAULTS);
  // Ảnh chụp giá trị lần đọc gần nhất từ máy chủ, dùng để biết có thay đổi chưa lưu.
  const [savedSnapshot, setSavedSnapshot] = useState(DEFAULTS);
  const [hydrated, setHydrated] = useState(false);
  const previousServerRef = useRef(null);
  const rootRef = useRef(null);
  const scrollRef = useRef(null);
  const sectionRefs = useRef({});

  const configQuery = useQuery({
    queryKey: queryKeys.config,
    queryFn: ({ signal }) => configApi.get({ signal }),
  });
  const serverValues = useMemo(
    () => (configQuery.data ? valuesFromConfig(configQuery.data) : null),
    [configQuery.data]
  );
  const loading = configQuery.isPending || (!hydrated && !configQuery.error);
  const configError = configQuery.error
    ? describeError(configQuery.error, {
        fallbackTitle: "Không đọc được cấu hình",
        fallbackDetail: "Máy chủ trả về lỗi khi đọc cấu hình.",
      })
    : null;

  // Cache `/config` dùng chung với tab Mô hình: nhận giá trị mới nhưng giữ lại
  // đúng những trường người dùng đang sửa dở ở tab này.
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

  const revert = useCallback(
    (key) => setValues((current) => ({ ...current, [key]: savedSnapshot[key] })),
    [savedSnapshot]
  );

  const dirtyKeys = useMemo(
    () => Object.keys(values).filter((key) => values[key] !== savedSnapshot[key]),
    [values, savedSnapshot]
  );
  const isDirty = dirtyKeys.length > 0;
  const isDirtyField = (key) => dirtyKeys.includes(key);

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

  // Đánh dấu mục đang xem trong mục lục khi cuộn.
  useEffect(() => {
    const root = scrollRef.current;
    if (!root || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveSection(visible[0].target.dataset.section);
      },
      { root, rootMargin: "0px 0px -60% 0px", threshold: 0 }
    );
    Object.values(sectionRefs.current).forEach((node) => node && observer.observe(node));
    return () => observer.disconnect();
  }, [loading]);

  function scrollToSection(id) {
    setActiveSection(id);
    sectionRefs.current[id]?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

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

      const next = await configApi.update(payload);
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

  // Ctrl/Cmd+S lưu nhanh, chỉ khi màn này đang hiển thị (tab khác vẫn mount nhưng bị ẩn).
  const saveRef = useRef(handleSaveAll);
  saveRef.current = handleSaveAll;
  const canSave = isDirty && !saving && !resetting;
  useEffect(() => {
    function onKeyDown(event) {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") return;
      const root = rootRef.current;
      if (!root || root.closest("[hidden]") || !canSave) return;
      event.preventDefault();
      saveRef.current();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [canSave]);

  if (loading) {
    return (
      <div className="model-mgmt-loading" aria-busy="true">
        <div className="model-mgmt-spinner" />
        <p>Đang tải cấu hình hệ thống...</p>
      </div>
    );
  }

  const { temperature, llmTimeout, maxRetries, topK, hybridVectorWeight } = values;
  const vectorPercent = Math.round(hybridVectorWeight * 100);
  const bm25Percent = 100 - vectorPercent;

  const summaries = {
    retrieval: `Top-K ${topK} · Vector ${vectorPercent}%`,
    reranker: values.rerankerEnabled ? `Bật · ${values.candidateMultiplier}× ứng viên` : "Đang tắt",
    guardrails: `${values.scopeEnabled ? "Lọc phạm vi" : "Không lọc"} · ≥ ${Number(
      values.minVectorScore
    ).toFixed(2)}`,
    llm: `Temp ${Number(temperature).toFixed(2)} · ${llmTimeout}s`,
  };

  const sectionHeader = (section, index) => {
    const Icon = section.icon;
    const sectionDirty = section.fields.filter(isDirtyField).length;
    return (
      <div className="cfg-section-header">
        <div className={`cfg-section-icon tone-${section.tone}`}>
          <Icon size={18} />
        </div>
        <div className="cfg-section-heading">
          <span className="cfg-section-step">Bước {index + 1}</span>
          <h3 id={`cfg-section-${section.id}-title`}>{section.title}</h3>
          <p>{section.description}</p>
        </div>
        {sectionDirty > 0 && (
          <span className="cfg-section-dirty">{sectionDirty} thay đổi</span>
        )}
      </div>
    );
  };

  const sectionProps = (section) => ({
    ref: (node) => {
      sectionRefs.current[section.id] = node;
    },
    id: `cfg-section-${section.id}`,
    "data-section": section.id,
    className: "cfg-section",
    "aria-labelledby": `cfg-section-${section.id}-title`,
  });

  return (
    <div className="config-page-wrapper cfg-page" ref={rootRef}>
      <div className="cfg-topbar">
        <div className="cfg-topbar-copy">
          <h2 className="cfg-title">Cấu hình RAG</h2>
          <p className="cfg-subtitle">
            Các tham số được sắp theo luồng xử lý: truy xuất → xếp hạng lại → lọc → sinh câu trả lời.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline-reset"
          onClick={() => setResetOpen(true)}
          disabled={resetting || saving}
        >
          <RotateCcw size={14} />
          <span>Khôi phục mặc định</span>
        </button>
      </div>

      {configError && (
        <div className="inline-alert is-warning cfg-alert" role="alert">
          <AlertTriangle size={16} />
          <span>
            {configError.title}. {configError.detail}
            {!configQuery.data &&
              " Các giá trị bên dưới là mặc định của giao diện, KHÔNG phải cấu hình đang chạy."}
          </span>
        </div>
      )}

      <div className="config-view-container cfg-scroll" ref={scrollRef}>
        <div className="cfg-layout">
          <nav className="cfg-toc" aria-label="Các nhóm cấu hình">
            <ol>
              {SECTIONS.map((section, index) => {
                const Icon = section.icon;
                const sectionDirty = section.fields.some(isDirtyField);
                return (
                  <li key={section.id}>
                    <button
                      type="button"
                      className={`cfg-toc-item ${activeSection === section.id ? "active" : ""}`}
                      aria-current={activeSection === section.id ? "true" : undefined}
                      onClick={() => scrollToSection(section.id)}
                    >
                      <span className={`cfg-toc-icon tone-${section.tone}`}>
                        <Icon size={15} />
                      </span>
                      <span className="cfg-toc-copy">
                        <span className="cfg-toc-title">
                          <span className="cfg-toc-index">{index + 1}.</span> {section.title}
                        </span>
                        <span className="cfg-toc-summary">{summaries[section.id]}</span>
                      </span>
                      {sectionDirty && (
                        <span className="cfg-dirty-dot" title="Có thay đổi chưa lưu" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          <div className="cfg-sections">
            {/* ---------------- 1. Truy xuất ---------------- */}
            <section {...sectionProps(SECTIONS[0])}>
              {sectionHeader(SECTIONS[0], 0)}
              <div className="cfg-section-body">
                <SettingRow
                  htmlFor="cfg-topk"
                  label="Số đoạn nạp vào LLM (Top-K)"
                  description="Số trích dẫn liên quan nhất được đưa vào prompt sinh câu trả lời. Nhiều hơn = đủ ngữ cảnh hơn nhưng chậm và dễ nhiễu."
                  dirty={isDirtyField("topK")}
                  onRevert={() => revert("topK")}
                >
                  <SliderControl
                    id="cfg-topk"
                    min={1}
                    max={10}
                    step={1}
                    integer
                    value={topK}
                    onChange={(v) => set("topK", v)}
                    numberLabel="Số đoạn nạp vào LLM"
                    unit="đoạn"
                  />
                </SettingRow>

                <SettingRow
                  htmlFor="cfg-hybrid"
                  label="Tỷ trọng tìm kiếm lai"
                  description="Vector hiểu ngữ nghĩa tự nhiên; BM25 khớp chính xác số điều khoản, tên môn học, mức học phí."
                  dirty={isDirtyField("hybridVectorWeight")}
                  onRevert={() => revert("hybridVectorWeight")}
                >
                  <div className="cfg-hybrid">
                    <div className="cfg-hybrid-legend" aria-hidden="true">
                      <span className="is-vector">
                        <i /> Vector <strong>{vectorPercent}%</strong>
                      </span>
                      <span className="is-bm25">
                        BM25 <strong>{bm25Percent}%</strong> <i />
                      </span>
                    </div>
                    <input
                      id="cfg-hybrid"
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      className="cfg-hybrid-range"
                      aria-valuetext={`Vector ${vectorPercent}%, BM25 ${bm25Percent}%`}
                      style={{ "--cfg-fill": `${vectorPercent}%` }}
                      value={hybridVectorWeight}
                      onChange={(e) => set("hybridVectorWeight", parseFloat(e.target.value))}
                    />
                    <div className="cfg-slider-bounds" aria-hidden="true">
                      <span>Thiên từ khoá</span>
                      <span>Thiên ngữ nghĩa</span>
                    </div>
                  </div>
                </SettingRow>

                <SettingRow
                  inline
                  labelId="cfg-mq-label"
                  label="Mở rộng câu hỏi đa hướng"
                  description="Tự sinh thêm các câu hỏi phụ để tìm kiếm toàn diện hơn."
                  dirty={isDirtyField("multiQueryEnabled")}
                  onRevert={() => revert("multiQueryEnabled")}
                >
                  <Switch
                    checked={values.multiQueryEnabled}
                    labelledBy="cfg-mq-label"
                    onChange={(v) => set("multiQueryEnabled", v)}
                  />
                </SettingRow>

                <SettingRow
                  nested
                  disabled={!values.multiQueryEnabled}
                  htmlFor="cfg-mq-count"
                  label="Số truy vấn phụ sinh ra"
                  description={
                    values.multiQueryEnabled
                      ? "Mỗi truy vấn phụ là một lượt tìm kiếm riêng."
                      : "Bật “Mở rộng câu hỏi đa hướng” để chỉnh."
                  }
                  dirty={isDirtyField("multiQueryCount")}
                  onRevert={() => revert("multiQueryCount")}
                >
                  <SliderControl
                    id="cfg-mq-count"
                    min={2}
                    max={6}
                    step={1}
                    integer
                    disabled={!values.multiQueryEnabled}
                    value={values.multiQueryCount}
                    onChange={(v) => set("multiQueryCount", v)}
                    numberLabel="Số truy vấn phụ sinh ra"
                    unit="câu"
                  />
                </SettingRow>

                <SettingRow
                  nested
                  inline
                  disabled={!values.multiQueryEnabled}
                  labelId="cfg-mq-llm-label"
                  label="Dùng LLM để viết lại truy vấn"
                  description="Chất lượng câu hỏi phụ tốt hơn nhưng tốn thêm một lượt gọi mô hình."
                  dirty={isDirtyField("multiQueryUseLlm")}
                  onRevert={() => revert("multiQueryUseLlm")}
                >
                  <Switch
                    checked={values.multiQueryUseLlm}
                    labelledBy="cfg-mq-llm-label"
                    disabled={!values.multiQueryEnabled}
                    onChange={(v) => set("multiQueryUseLlm", v)}
                  />
                </SettingRow>
              </div>
            </section>

            {/* ---------------- 2. Reranker ---------------- */}
            <section {...sectionProps(SECTIONS[1])}>
              {sectionHeader(SECTIONS[1], 1)}
              <div className="cfg-section-body">
                <SettingRow
                  inline
                  labelId="cfg-reranker-label"
                  label="Kích hoạt Reranker"
                  description="Dùng Cross-Encoder hoặc Cohere Rerank để xếp lại danh sách đoạn (chọn mô hình ở tab Mô hình)."
                  dirty={isDirtyField("rerankerEnabled")}
                  onRevert={() => revert("rerankerEnabled")}
                >
                  <Switch
                    checked={values.rerankerEnabled}
                    labelledBy="cfg-reranker-label"
                    onChange={(v) => set("rerankerEnabled", v)}
                  />
                </SettingRow>

                <SettingRow
                  nested
                  disabled={!values.rerankerEnabled}
                  htmlFor="cfg-candidate"
                  label="Hệ số ứng viên sơ bộ"
                  description={
                    values.rerankerEnabled
                      ? `Lấy ${topK * values.candidateMultiplier} đoạn (${topK} × ${values.candidateMultiplier}) trước khi xếp lại và giữ ${topK} đoạn tốt nhất.`
                      : "Bật Reranker để chỉnh."
                  }
                  dirty={isDirtyField("candidateMultiplier")}
                  onRevert={() => revert("candidateMultiplier")}
                >
                  <SliderControl
                    id="cfg-candidate"
                    min={1}
                    max={6}
                    step={1}
                    integer
                    disabled={!values.rerankerEnabled}
                    value={values.candidateMultiplier}
                    onChange={(v) => set("candidateMultiplier", v)}
                    numberLabel="Hệ số ứng viên sơ bộ"
                    unit="×"
                    formatBound={(v) => `${v}×`}
                  />
                </SettingRow>
              </div>
            </section>

            {/* ---------------- 3. Ngưỡng & an toàn ---------------- */}
            <section {...sectionProps(SECTIONS[2])}>
              {sectionHeader(SECTIONS[2], 2)}
              <div className="cfg-section-body">
                <SettingRow
                  inline
                  labelId="cfg-scope-label"
                  label="Kiểm soát phạm vi PTIT"
                  description="Từ chối lịch sự khi câu hỏi không liên quan đến Học viện."
                  dirty={isDirtyField("scopeEnabled")}
                  onRevert={() => revert("scopeEnabled")}
                >
                  <Switch
                    checked={values.scopeEnabled}
                    labelledBy="cfg-scope-label"
                    onChange={(v) => set("scopeEnabled", v)}
                  />
                </SettingRow>

                <SettingRow
                  htmlFor="cfg-minvec"
                  label="Ngưỡng tương đồng vector tối thiểu"
                  description={`Cosine similarity tối thiểu; đoạn dưới ${Number(
                    values.minVectorScore
                  ).toFixed(2)} bị loại để tránh trả lời sai sự thật.`}
                  dirty={isDirtyField("minVectorScore")}
                  onRevert={() => revert("minVectorScore")}
                >
                  <SliderControl
                    id="cfg-minvec"
                    min={0.1}
                    max={0.8}
                    step={0.02}
                    value={values.minVectorScore}
                    onChange={(v) => set("minVectorScore", v)}
                    numberLabel="Ngưỡng tương đồng vector tối thiểu"
                  />
                </SettingRow>

                <SettingRow
                  htmlFor="cfg-minbm25"
                  label="Điểm khớp từ khoá BM25 tối thiểu"
                  description="Đoạn có điểm BM25 thấp hơn ngưỡng không được coi là khớp từ khoá."
                  dirty={isDirtyField("minBm25Score")}
                  onRevert={() => revert("minBm25Score")}
                >
                  <SliderControl
                    id="cfg-minbm25"
                    min={0.5}
                    max={6}
                    step={0.5}
                    value={values.minBm25Score}
                    onChange={(v) => set("minBm25Score", v)}
                    numberLabel="Điểm khớp từ khóa BM25 tối thiểu"
                  />
                </SettingRow>
              </div>
            </section>

            {/* ---------------- 4. Mô hình sinh ---------------- */}
            <section {...sectionProps(SECTIONS[3])}>
              {sectionHeader(SECTIONS[3], 3)}
              <div className="cfg-section-body">
                <SettingRow
                  htmlFor="cfg-temperature"
                  label="Độ ngẫu nhiên (Temperature)"
                  description={temperatureHint(temperature)}
                  dirty={isDirtyField("temperature")}
                  onRevert={() => revert("temperature")}
                >
                  <SliderControl
                    id="cfg-temperature"
                    min={0}
                    max={1.5}
                    step={0.05}
                    value={temperature}
                    onChange={(v) => set("temperature", v)}
                    numberLabel="Giá trị Temperature"
                  />
                </SettingRow>

                <SettingRow
                  htmlFor="cfg-timeout"
                  label="Thời gian chờ tối đa"
                  description="Tự ngắt khi gọi mô hình quá lâu."
                  dirty={isDirtyField("llmTimeout")}
                  onRevert={() => revert("llmTimeout")}
                >
                  <SliderControl
                    id="cfg-timeout"
                    min={5}
                    max={90}
                    step={5}
                    integer
                    value={llmTimeout}
                    onChange={(v) => set("llmTimeout", v)}
                    numberLabel="Thời gian chờ tối đa, tính bằng giây"
                    unit="giây"
                    formatBound={(v) => `${v}s`}
                  />
                </SettingRow>

                <SettingRow
                  labelId="cfg-retries-label"
                  label="Số lần thử lại khi lỗi mạng"
                  description="Gọi lại mô hình khi gặp lỗi tạm thời trước khi báo lỗi cho người dùng."
                  dirty={isDirtyField("maxRetries")}
                  onRevert={() => revert("maxRetries")}
                >
                  <div className="cfg-segmented" role="group" aria-labelledby="cfg-retries-label">
                    {[0, 1, 2, 3, 5].map((val) => (
                      <button
                        key={val}
                        type="button"
                        className={maxRetries === val ? "active" : ""}
                        aria-pressed={maxRetries === val}
                        onClick={() => set("maxRetries", val)}
                      >
                        {val === 0 ? "Không" : `${val} lần`}
                      </button>
                    ))}
                  </div>
                </SettingRow>
              </div>
            </section>
          </div>
        </div>
      </div>

      <div className={`cfg-savebar ${isDirty ? "is-dirty" : ""}`}>
        <div className="cfg-savebar-status" aria-live="polite">
          {isDirty ? (
            <>
              <span className="unsaved-badge" role="status">
                {dirtyKeys.length} thay đổi chưa lưu
              </span>
              <span className="cfg-savebar-fields">
                {dirtyKeys.map((key) => FIELD_LABELS[key]).join(", ")}
              </span>
            </>
          ) : (
            <span className="cfg-savebar-saved">
              <Check size={14} aria-hidden="true" />
              Cấu hình đang dùng đã được lưu trên máy chủ
            </span>
          )}
        </div>
        <div className="cfg-savebar-actions">
          {isDirty && (
            <button
              type="button"
              className="ghost-btn cfg-discard-btn"
              onClick={() => setValues(savedSnapshot)}
              disabled={saving || resetting}
            >
              <Undo2 size={14} />
              <span>Huỷ thay đổi</span>
            </button>
          )}
          <button
            type="button"
            className="btn btn-primary-save"
            onClick={handleSaveAll}
            disabled={!canSave}
            title="Lưu (Ctrl+S)"
          >
            {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
            <span>{saving ? "Đang lưu..." : "Lưu cấu hình"}</span>
          </button>
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
