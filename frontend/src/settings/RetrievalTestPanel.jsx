import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical, Loader2, X } from "lucide-react";
import {
  datasetsApi,
  describeError,
  isAbortError,
  queryKeys,
  retrievalApi,
} from "../api";
import {
  GATE_SIGNALS,
  decideGate,
  thresholdsFromRetrievalResult,
} from "../lib/gateDecision";

/**
 * Bảng "Thử với câu hỏi": chạy `/retrieval/test` trên cấu hình đã lưu rồi so điểm
 * trả về với ngưỡng nháp tại chỗ. Chỉ chạy khi bấm nút: pipeline tốn embedding và
 * có thể gọi LLM khi bật viết lại câu hỏi.
 */

const RUN_HISTORY_LIMIT = 5;
const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

// Đổi tỷ trọng/mở rộng câu hỏi/reranker đổi danh sách đoạn nên phải lưu rồi chạy lại.
// Top-K không nằm đây vì API `/retrieval/test` nhận `top_k` của bản nháp.
const NEEDS_SAVED_RUN_KEYS = new Set([
  "hybridVectorWeight",
  "multiQueryEnabled",
  "multiQueryCount",
  "multiQueryUseLlm",
  "queryRewriteUseLlm",
  "rerankerEnabled",
  "candidateMultiplier",
  "scopeEnabled",
]);

const REASON_COPY = {
  passed: "Mọi tín hiệu đang dùng đều đạt ngưỡng nên chatbot sẽ gọi mô hình trả lời.",
  passed_uncalibrated_model:
    "Các tín hiệu đang dùng đều đạt ngưỡng; mô hình nhúng chưa hiệu chỉnh nên bỏ qua tín hiệu ngữ nghĩa.",
  no_context: "Không tìm thấy đoạn tài liệu nào phù hợp nên chatbot sẽ từ chối.",
  below_bm25_norm: "Độ khớp từ khóa của đoạn tốt nhất thấp hơn ngưỡng nên chatbot sẽ từ chối.",
  below_vector: "Độ tương đồng ngữ nghĩa của đoạn tốt nhất thấp hơn ngưỡng nên chatbot sẽ từ chối.",
  below_rerank: "Điểm xếp hạng lại của đoạn tốt nhất thấp hơn ngưỡng nên chatbot sẽ từ chối.",
};

function sameThreshold(a, b) {
  if (a === null || a === undefined || b === null || b === undefined) {
    return (a ?? null) === (b ?? null);
  }
  return Math.abs(Number(a) - Number(b)) < 1e-9;
}

/**
 * Ngưỡng hiệu lực của bản nháp: ghi đè nếu có, ngược lại dùng bảng hiệu chỉnh.
 * Reranker chỉ áp dụng khi bản nháp đang bật và provider là Cross-Encoder.
 */
export function draftGateThresholds(config, draft) {
  const guardrails = config?.guardrails ?? {};
  // Backend cũ không trả `calibrated_*`: khi nguồn là "calibrated" thì chính trường
  // hiệu lực là giá trị bảng hiệu chỉnh.
  const calibratedVector =
    guardrails.calibrated_min_vector_score ??
    (guardrails.vector_threshold_source === "calibrated" ? guardrails.min_vector_score : null) ??
    null;
  const calibratedRerank =
    guardrails.calibrated_min_rerank_score ??
    (guardrails.rerank_threshold_source === "calibrated" ? guardrails.min_rerank_score : null) ??
    null;
  const vectorOverride = draft?.minVectorScore ?? null;
  const rerankOverride = draft?.minRerankScore ?? null;
  const rerankerApplies =
    Boolean(draft?.rerankerEnabled) && config?.reranker?.provider === "cross-encoder";

  let vectorSource = "uncalibrated";
  if (vectorOverride !== null) vectorSource = "override";
  else if (calibratedVector !== null) vectorSource = "calibrated";

  let rerankSource = "not_applicable";
  if (rerankerApplies) {
    if (rerankOverride !== null) rerankSource = "override";
    else if (calibratedRerank !== null) rerankSource = "calibrated";
    else rerankSource = "uncalibrated";
  }

  return {
    min_bm25_norm_score: Number(
      draft?.minBm25NormScore ?? guardrails.min_bm25_norm_score ?? 0.25
    ),
    min_vector_score: vectorOverride ?? calibratedVector,
    min_rerank_score: rerankerApplies ? rerankOverride ?? calibratedRerank : null,
    vector_source: vectorSource,
    rerank_source: rerankSource,
  };
}

export function gateThresholdsDiffer(saved, draft) {
  return GATE_SIGNALS.some(
    (signal) => !sameThreshold(saved?.[signal.thresholdField], draft?.[signal.thresholdField])
  );
}

function formatScore(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function formatClock(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function verdictText(strong) {
  return strong ? "Sẽ trả lời" : "Sẽ từ chối";
}

function chunkLocator(context) {
  const parts = [];
  if (context.legal_article) parts.push(String(context.legal_article));
  if (Array.isArray(context.legal_clauses) && context.legal_clauses.length > 0) {
    parts.push(`Khoản ${context.legal_clauses.join(", ")}`);
  }
  if (Array.isArray(context.legal_points) && context.legal_points.length > 0) {
    parts.push(`Điểm ${context.legal_points.join(", ")}`);
  }
  if (parts.length === 0) {
    if (context.section_path) parts.push(String(context.section_path));
    else if (context.heading) parts.push(String(context.heading));
  }
  return parts.join(" · ");
}

function SignalRow({ signal, value, savedThreshold, draftThreshold }) {
  const [scaleMin, scaleMax] = signal.scale;
  const position = (raw) =>
    Math.max(0, Math.min(100, ((Number(raw) - scaleMin) / (scaleMax - scaleMin)) * 100));
  const applies = savedThreshold !== null && savedThreshold !== undefined;
  const draftApplies = draftThreshold !== null && draftThreshold !== undefined;
  const passed = applies && value !== null && value !== undefined && value >= Number(savedThreshold);

  let status;
  if (!applies) status = <span className="retrieval-signal-status is-muted">không áp dụng</span>;
  else if (value === null || value === undefined) {
    status = <span className="retrieval-signal-status is-bad">thiếu tín hiệu</span>;
  } else {
    status = (
      <span className={`retrieval-signal-status ${passed ? "is-ok" : "is-bad"}`}>
        {passed ? "≥" : "<"} {formatScore(savedThreshold)}
      </span>
    );
  }

  return (
    <div className="retrieval-signal" data-signal={signal.key}>
      <span className="retrieval-signal-label">{signal.label}</span>
      <span className="retrieval-signal-value">{formatScore(value)}</span>
      {status}
      {applies && value !== null && value !== undefined && (
        <span className="retrieval-signal-bar" aria-hidden="true">
          <span className="retrieval-signal-fill" style={{ width: `${position(value)}%` }} />
          <span className="retrieval-signal-tick" style={{ left: `${position(savedThreshold)}%` }} />
          {draftApplies && !sameThreshold(savedThreshold, draftThreshold) && (
            <span
              className="retrieval-signal-tick is-draft"
              style={{ left: `${position(draftThreshold)}%` }}
              title={`Ngưỡng nháp ${formatScore(draftThreshold)}`}
            />
          )}
        </span>
      )}
    </div>
  );
}

export default function RetrievalTestPanel({
  hidden = false,
  open = false,
  onClose,
  config = null,
  draft = null,
  changedKeys = [],
}) {
  const [question, setQuestion] = useState("");
  const [datasetChoice, setDatasetChoice] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const controllerRef = useRef(null);
  const panelRef = useRef(null);
  const previousFocusRef = useRef(null);

  const datasetsQuery = useQuery({
    queryKey: queryKeys.datasetList,
    queryFn: ({ signal }) => datasetsApi.list({ signal }),
    // Panel vẫn mounted khi đang xem mục khác (giữ 5 lần chạy), nhưng chỉ tải
    // danh sách dataset khi thực sự mở nhóm "Hệ thống trả lời".
    enabled: !hidden,
  });
  const datasets = datasetsQuery.data?.datasets ?? [];

  // Huỷ request đang chạy khi rời màn.
  useEffect(() => () => controllerRef.current?.abort(), []);

  // Drawer (<1280px): Esc đóng, Tab xoay vòng trong panel, trả focus về nút mở.
  useEffect(() => {
    if (!open) return undefined;
    previousFocusRef.current = document.activeElement;
    const node = panelRef.current;
    const focusables = () =>
      Array.from(node?.querySelectorAll(FOCUSABLE) ?? []).filter(
        (item) => item.offsetParent !== null || item === document.activeElement
      );
    (focusables()[0] ?? node)?.focus?.();

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose?.();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        node?.focus?.();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      const target = previousFocusRef.current;
      if (target && document.contains(target)) target.focus?.();
    };
  }, [open, onClose]);

  const currentRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null,
    [runs, selectedRunId]
  );
  const result = currentRun?.result ?? null;
  const confidence = result?.retrieval_debug?.confidence ?? null;
  const savedThresholds = thresholdsFromRetrievalResult(result);
  const reason = confidence?.reason ?? null;
  const strong = reason ? String(reason).startsWith("passed") : Boolean(result?.strong_context);

  const draftThresholds = useMemo(
    () => (config && draft ? draftGateThresholds(config, draft) : null),
    [config, draft]
  );
  const draftDiffers =
    Boolean(result && draftThresholds) &&
    gateThresholdsDiffer(savedThresholds, draftThresholds);
  const draftDecision =
    draftDiffers && result
      ? decideGate(result.contexts ?? [], draftThresholds)
      : null;

  const needsSavedRun = changedKeys.some((key) => NEEDS_SAVED_RUN_KEYS.has(key));
  const subQueries = useMemo(() => {
    const all = result?.retrieval_debug?.retrieval_queries ?? [];
    const rewritten = result?.retrieval_debug?.rewritten_query;
    return all.filter((query) => query && query !== rewritten);
  }, [result]);

  async function runTest() {
    const query = question.trim();
    if (!query) {
      setError({ title: "Chưa có câu hỏi", detail: "Nhập câu hỏi trước khi chạy thử." });
      return;
    }

    // Chạy lại khi đang chạy: huỷ request cũ, kết quả cũ không ghi đè kết quả mới.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setRunning(true);
    setError(null);
    try {
      const payload = await retrievalApi.test(
        {
          query,
          topK: draft?.topK,
          datasetIds: datasetChoice ? [datasetChoice] : undefined,
        },
        { signal: controller.signal }
      );
      if (controller.signal.aborted) return;
      const entry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        question: query,
        at: new Date(),
        result: payload,
      };
      setRuns((previous) => [entry, ...previous].slice(0, RUN_HISTORY_LIMIT));
      setSelectedRunId(entry.id);
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) return;
      setError(
        describeError(err, {
          fallbackTitle: "Không chạy được thử truy xuất",
          fallbackDetail: "Máy chủ trả về lỗi khi chạy thử truy xuất.",
        })
      );
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setRunning(false);
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    runTest();
  }

  return (
    <>
      {open && (
        <button
          type="button"
          className="retrieval-test-scrim"
          aria-label="Đóng bảng thử với câu hỏi"
          onClick={onClose}
        />
      )}
      <aside
        ref={panelRef}
        className="retrieval-test-panel"
        data-open={open ? "true" : "false"}
        aria-label="Thử với câu hỏi"
        aria-hidden={hidden || undefined}
        hidden={hidden}
        role={open ? "dialog" : undefined}
        aria-modal={open ? "true" : undefined}
        tabIndex={-1}
      >
        <header className="retrieval-test-head">
          <div>
            <h2 className="retrieval-test-title">Thử với câu hỏi</h2>
            <p className="retrieval-test-sub">
              Xem chatbot sẽ tìm được gì và có trả lời hay không.
            </p>
          </div>
          <button
            type="button"
            className="retrieval-test-close"
            aria-label="Đóng bảng thử"
            onClick={onClose}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </header>

        <form className="retrieval-test-form" onSubmit={handleSubmit}>
          <label className="retrieval-test-label" htmlFor="retrieval-test-query">
            Câu hỏi
          </label>
          <textarea
            id="retrieval-test-query"
            className="retrieval-test-input"
            rows={2}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ví dụ: Điều kiện xét học bổng khuyến khích học tập là gì?"
          />
          <div className="retrieval-test-actions">
            <label className="retrieval-test-dataset">
              <span className="sr-only">Dataset</span>
              <select
                className="retrieval-test-select"
                value={datasetChoice}
                onChange={(event) => setDatasetChoice(event.target.value)}
                disabled={running}
                aria-label="Chọn dataset để thử"
              >
                <option value="">Tất cả dataset</option>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              className="btn-primary-save"
              title={running ? "Bấm để huỷ lần đang chạy và chạy lại" : undefined}
              aria-label={running ? "Chạy lại (huỷ lần đang chạy)" : "Chạy thử"}
            >
              {running ? <Loader2 size={15} className="spin" /> : <FlaskConical size={15} />}
              {running ? "Đang chạy..." : "Chạy thử"}
            </button>
          </div>
        </form>

        {error && (
          <div className="inline-alert is-error retrieval-test-error" role="alert">
            <strong>{error.title}.</strong> {error.detail}
          </div>
        )}

        {!result && !error && (
          <p className="retrieval-test-note">
            Chạy trên cấu hình đã lưu. Kết quả giữ tối đa {RUN_HISTORY_LIMIT} lần chạy trong phiên
            này để so trước/sau.
          </p>
        )}

        {result && (
          <div className="retrieval-test-results">
            <section className="retrieval-verdict" aria-label="Kết luận">
              <div className="retrieval-verdict-head">
                <span>
                  Cấu hình đã lưu:{" "}
                  <strong className={strong ? "is-ok" : "is-bad"}>
                    {strong ? "✓" : "✕"} {verdictText(strong)}
                  </strong>
                </span>
                {draftDecision && (
                  <span>
                    Bản nháp:{" "}
                    <strong className={draftDecision.strong ? "is-ok" : "is-bad"}>
                      {draftDecision.strong ? "✓" : "✕"} {verdictText(draftDecision.strong)}
                    </strong>
                  </span>
                )}
              </div>
              <p className="retrieval-verdict-reason">
                {REASON_COPY[reason] ?? (reason ? `Lý do từ máy chủ: ${reason}` : "Máy chủ không trả lý do.")}
              </p>
              {draftDecision && draftDecision.reason !== reason && (
                <p className="retrieval-verdict-reason is-draft">
                  Bản nháp: {REASON_COPY[draftDecision.reason] ?? draftDecision.reason}
                </p>
              )}
              <div className="retrieval-signals">
                {GATE_SIGNALS.map((signal) => (
                  <SignalRow
                    key={signal.key}
                    signal={signal}
                    value={confidence?.signals?.[signal.key] ?? null}
                    savedThreshold={savedThresholds?.[signal.thresholdField] ?? null}
                    draftThreshold={draftThresholds?.[signal.thresholdField] ?? null}
                  />
                ))}
              </div>
            </section>

            {needsSavedRun && (
              <p className="inline-alert is-warning retrieval-test-note" role="note">
                Bản nháp đổi tỷ trọng, mở rộng câu hỏi hoặc xếp hạng lại. Cần lưu rồi chạy lại để
                thấy ảnh hưởng.
              </p>
            )}

            <section className="retrieval-queries" aria-label="Truy vấn">
              <h3>Câu hỏi viết lại</h3>
              <code>{result.retrieval_debug?.rewritten_query || "—"}</code>
              {subQueries.length > 0 && (
                <>
                  <h3>Truy vấn phụ</h3>
                  <ul>
                    {subQueries.map((query) => (
                      <li key={query}>{query}</li>
                    ))}
                  </ul>
                </>
              )}
            </section>

            <section className="retrieval-chunks" aria-label="Đoạn tìm được">
              <h3>Đoạn tìm được ({result.contexts?.length ?? 0})</h3>
              {result.contexts?.length ? (
                <ul>
                  {result.contexts.map((context, index) => {
                    const locator = chunkLocator(context);
                    return (
                      <li className="retrieval-chunk" key={context.chunk_id ?? `${index}-${context.text}`}>
                        <div className="retrieval-chunk-src">
                          <strong>{context.source_name || context.source || "Không rõ nguồn"}</strong>
                          <span>#{index + 1}</span>
                        </div>
                        {locator && <p className="retrieval-chunk-locator">{locator}</p>}
                        <p className="retrieval-chunk-text">{context.text}</p>
                        <p className="retrieval-chunk-scores">
                          cos {formatScore(context.vector_score)} · bm25{" "}
                          {formatScore(context.bm25_norm_score)} · rerank{" "}
                          {formatScore(context.rerank_score)}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="retrieval-test-note">Không có đoạn nào.</p>
              )}
            </section>

            <p className="retrieval-test-note">
              Chạy trên cấu hình đã lưu. Ngưỡng nháp được so tại chỗ với điểm trả về; thay đổi
              Top-K, tỷ trọng hay xếp hạng lại cần lưu rồi chạy lại.
            </p>
          </div>
        )}

        {runs.length > 1 && (
          <section className="retrieval-history" aria-label="Các lần chạy gần nhất">
            <h3>Các lần chạy gần nhất</h3>
            <ul>
              {runs.map((run) => {
                const runReason = run.result?.retrieval_debug?.confidence?.reason;
                const runStrong = runReason
                  ? String(runReason).startsWith("passed")
                  : Boolean(run.result?.strong_context);
                return (
                  <li key={run.id}>
                    <button
                      type="button"
                      className={`retrieval-history-item ${
                        currentRun?.id === run.id ? "is-active" : ""
                      }`}
                      onClick={() => setSelectedRunId(run.id)}
                    >
                      <span className="retrieval-history-question">{run.question}</span>
                      <span className={runStrong ? "is-ok" : "is-bad"}>{verdictText(runStrong)}</span>
                      <time dateTime={run.at.toISOString()}>{formatClock(run.at)}</time>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </aside>
    </>
  );
}
