import React from "react";
import { Brain, Check, ChevronDown, Loader2 } from "lucide-react";

/**
 * Nhãn hiển thị cho từng bước pipeline RAG do backend phát trong event `step`.
 * detail chứa dữ liệu thô từ backend (rewritten_query, candidate_count...).
 */
const STEP_LABELS = {
  guardrail: "Kiểm tra phạm vi câu hỏi",
  query_rewrite: "Chuẩn hóa truy vấn",
  multi_query: "Sinh biến thể truy vấn",
  retrieve: "Tìm kiếm trong tài liệu",
  rerank: "Xếp hạng đoạn văn",
  generate: "Soạn câu trả lời",
};

function stepDetailText(step) {
  const detail = step.detail || {};
  switch (step.step) {
    case "guardrail":
      return detail.allowed === false ? "Ngoài phạm vi" : "Trong phạm vi";
    case "query_rewrite":
      return detail.rewritten_query || "";
    case "multi_query":
      return `${(detail.queries || []).length} biến thể`;
    case "retrieve": {
      const count = detail.candidate_count ?? 0;
      const sources = detail.sources || [];
      const sourceText = sources.length ? ` · ${sources.join(", ")}` : "";
      return `Tìm thấy ${count} đoạn ứng viên${sourceText}`;
    }
    case "rerank":
      return `Chọn ${detail.selected_count ?? 0} đoạn liên quan nhất`;
    default:
      return "";
  }
}

function formatSeconds(totalMs) {
  if (!totalMs) return "";
  const seconds = totalMs / 1000;
  // Dưới 10 giây hiện 1 chữ số thập phân để thấy được khác biệt giữa các bước.
  return seconds < 10 ? `${seconds.toFixed(1)} giây` : `${Math.round(seconds)} giây`;
}

/**
 * Panel suy luận: timeline các bước RAG + chuỗi thinking của model.
 *
 * - `steps`: mảng event step từ backend ({step, status, detail, elapsed_ms}).
 * - `reasoning`: text thinking đã stream (rỗng khi model không hỗ trợ).
 * - `streaming`: true khi câu trả lời đang được tạo.
 * - `open`/`onToggle`: trạng thái mở/đóng do ChatView giữ để tự thu gọn khi
 *   phần câu trả lời bắt đầu stream.
 */
export default function ReasoningPanel({ steps = [], reasoning = "", streaming = false, open, onToggle }) {
  if (!steps.length && !reasoning) return null;

  const totalMs = steps.reduce((sum, step) => sum + (step.elapsed_ms || 0), 0);
  const title = streaming ? "Đang suy luận..." : `Đã suy luận${totalMs ? ` · ${formatSeconds(totalMs)}` : ""}`;

  return (
    <div className={`reasoning-panel ${open ? "open" : ""} ${streaming ? "streaming" : ""}`}>
      <button
        type="button"
        className="reasoning-header"
        onClick={onToggle}
        aria-expanded={open}
        aria-label={open ? "Thu gọn quá trình suy luận" : "Mở quá trình suy luận"}
      >
        <span className="reasoning-icon" aria-hidden="true">
          {streaming ? <Loader2 size={14} /> : <Brain size={14} />}
        </span>
        <span className="reasoning-title">{title}</span>
        <ChevronDown size={14} className="reasoning-chevron" aria-hidden="true" />
      </button>

      {open && (
        <div className="reasoning-body">
          {steps.length > 0 && (
            <ol className="reasoning-steps">
              {steps.map((step, index) => {
                const running = streaming && step.status === "start";
                return (
                  <li className={`reasoning-step ${running ? "running" : ""}`} key={`${step.step}-${index}`}>
                    <span className="step-marker" aria-hidden="true">
                      {running ? <Loader2 size={12} /> : <Check size={12} />}
                    </span>
                    <span className="step-label">
                      {STEP_LABELS[step.step] || step.step}
                      {stepDetailText(step) && <span className="step-detail">{stepDetailText(step)}</span>}
                    </span>
                    {step.elapsed_ms > 0 && <span className="step-ms">{step.elapsed_ms}ms</span>}
                  </li>
                );
              })}
            </ol>
          )}

          {reasoning && (
            <div className="reasoning-text">
              {reasoning}
              {streaming && <span className="typing-cursor" aria-hidden="true" />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
