/**
 * Luật confidence gate phía client, dùng để so ngưỡng nháp với điểm vừa trả về.
 *
 * Bản sao của `assess_context` trong `backend/app/generation/confidence.py`: gate đạt
 * khi **mọi** tín hiệu đang dùng (ngưỡng khác `null`) đều vượt ngưỡng; tín hiệu thiếu
 * tính là trượt; thứ tự kiểm tra `bm25_norm` → `vector` → `rerank`. Sửa luật ở đây thì
 * sửa cả `backend/tests/test_retrieval_confidence.py` và
 * `frontend/src/lib/gateDecision.test.js`.
 */

/**
 * Ngưỡng dự phòng khi caller không truyền: chỉ dùng tín hiệu từ khóa; vector và
 * rerank `null` (không áp dụng) vì ngưỡng của chúng phụ thuộc mô hình.
 */
export const DEFAULT_GATE_THRESHOLDS = {
  min_bm25_norm_score: 0.25,
  min_vector_score: null,
  min_rerank_score: null,
  vector_source: "calibrated",
};

export const GATE_SIGNALS = [
  {
    key: "bm25_norm",
    label: "Độ khớp từ khóa",
    scoreField: "bm25_norm_score",
    thresholdField: "min_bm25_norm_score",
    scale: [0, 1],
  },
  {
    key: "vector",
    label: "Độ tương đồng ngữ nghĩa",
    scoreField: "vector_score",
    thresholdField: "min_vector_score",
    scale: [0, 1],
  },
  {
    key: "rerank",
    label: "Điểm xếp hạng lại",
    scoreField: "rerank_score",
    thresholdField: "min_rerank_score",
    scale: [-10, 10],
  },
];

function topScore(contexts, field) {
  let top = null;
  (contexts ?? []).forEach((context) => {
    const raw = context?.[field];
    if (raw === null || raw === undefined) return;
    const value = Number(raw);
    if (Number.isNaN(value)) return;
    if (top === null || value > top) top = value;
  });
  return top;
}

/** Điểm top-1 của ba tín hiệu, đúng cách backend lấy max trên các context. */
export function signalsFromContexts(contexts) {
  return {
    vector: topScore(contexts, "vector_score"),
    bm25_norm: topScore(contexts, "bm25_norm_score"),
    rerank: topScore(contexts, "rerank_score"),
  };
}

/**
 * `contexts` + ngưỡng hiệu lực → `{ strong, reason, signals }`.
 *
 * `reason` khớp mã của backend: `no_context`, `below_bm25_norm`, `below_vector`,
 * `below_rerank`, `passed`, `passed_uncalibrated_model`.
 */
export function decideGate(contexts, thresholds = DEFAULT_GATE_THRESHOLDS) {
  const signals = signalsFromContexts(contexts);
  const limits = { ...DEFAULT_GATE_THRESHOLDS, ...(thresholds ?? {}) };

  if (!contexts || contexts.length === 0) {
    return { strong: false, reason: "no_context", signals };
  }

  const checks = [
    ["bm25_norm", limits.min_bm25_norm_score],
    ["vector", limits.min_vector_score],
    ["rerank", limits.min_rerank_score],
  ];
  for (const [name, minimum] of checks) {
    if (minimum === null || minimum === undefined) continue;
    const value = signals[name];
    if (value === null || value < Number(minimum)) {
      return { strong: false, reason: `below_${name}`, signals };
    }
  }

  return {
    strong: true,
    reason:
      limits.vector_source === "uncalibrated" ? "passed_uncalibrated_model" : "passed",
    signals,
  };
}

/** Ngưỡng lấy từ response `/retrieval/test` (đã gồm ngưỡng hiệu lực của bản đã lưu). */
export function thresholdsFromRetrievalResult(result) {
  return result?.retrieval_debug?.confidence?.thresholds ?? DEFAULT_GATE_THRESHOLDS;
}
