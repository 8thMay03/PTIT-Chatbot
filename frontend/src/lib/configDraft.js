/**
 * Bản nháp form Cấu hình RAG: đọc từ `/config`, so với bản đã lưu, dựng payload PUT.
 *
 * Ngưỡng vector/rerank trong bản nháp là **ghi đè** chứ không phải ngưỡng hiệu lực:
 * `null` nghĩa là theo bảng hiệu chỉnh của model (gate RAG-18). Gửi `null` trong PUT
 * `/config` xoá ghi đè; không gửi khoá thì backend giữ nguyên.
 */

export const DEFAULTS = {
  temperature: 0.0,
  llmTimeout: 30,
  maxRetries: 2,
  topK: 4,
  hybridVectorWeight: 0.65,
  multiQueryEnabled: true,
  multiQueryCount: 3,
  multiQueryUseLlm: false,
  queryRewriteUseLlm: false,
  scopeEnabled: true,
  minVectorScore: null,
  minBm25NormScore: 0.25,
  minRerankScore: null,
  rerankerEnabled: true,
  candidateMultiplier: 3,
};

const fixed2 = (value) => Number(value).toFixed(2);
const onOff = (value) => (value ? "Bật" : "Tắt");

/**
 * Thứ tự = thứ tự pipeline trong form và trong tóm tắt thay đổi.
 * `path` là vị trí trong payload PUT; `section` là mục danh mục Settings.
 */
export const CONFIG_FIELDS = {
  topK: { label: "Top-K", path: ["retrieval", "top_k"], section: "retrieval", format: String },
  hybridVectorWeight: {
    label: "Tỷ trọng vector",
    path: ["retrieval", "hybrid_vector_weight"],
    section: "retrieval",
    format: (v) => `${Math.round(Number(v) * 100)}%`,
  },
  multiQueryEnabled: {
    label: "Mở rộng câu hỏi",
    path: ["retrieval", "multi_query_enabled"],
    section: "retrieval",
    format: onOff,
  },
  multiQueryCount: {
    label: "Số truy vấn phụ",
    path: ["retrieval", "multi_query_count"],
    section: "retrieval",
    format: String,
  },
  multiQueryUseLlm: {
    label: "Sinh truy vấn phụ bằng LLM",
    path: ["retrieval", "multi_query_use_llm"],
    section: "retrieval",
    format: onOff,
  },
  queryRewriteUseLlm: {
    label: "Viết lại câu hỏi bằng LLM",
    path: ["retrieval", "query_rewrite_use_llm"],
    section: "retrieval",
    format: onOff,
  },
  rerankerEnabled: {
    label: "Xếp hạng lại",
    path: ["reranker", "enabled"],
    section: "reranker",
    format: onOff,
  },
  candidateMultiplier: {
    label: "Hệ số ứng viên",
    path: ["reranker", "candidate_multiplier"],
    section: "reranker",
    format: (v) => `${v}×`,
  },
  minBm25NormScore: {
    label: "Độ khớp từ khóa",
    path: ["guardrails", "min_bm25_norm_score"],
    section: "gate",
    format: fixed2,
  },
  minVectorScore: {
    label: "Ngưỡng ngữ nghĩa",
    path: ["guardrails", "min_vector_score"],
    section: "gate",
    format: fixed2,
    calibratedKey: "vector",
  },
  minRerankScore: {
    label: "Điểm xếp hạng lại",
    path: ["guardrails", "min_rerank_score"],
    section: "gate",
    format: fixed2,
    calibratedKey: "rerank",
  },
  scopeEnabled: {
    label: "Kiểm soát phạm vi PTIT",
    path: ["guardrails", "scope_enabled"],
    section: "gate",
    format: onOff,
  },
  temperature: {
    label: "Độ ngẫu nhiên",
    path: ["llm", "temperature"],
    section: "generation",
    format: fixed2,
  },
  llmTimeout: {
    label: "Thời gian chờ",
    path: ["llm", "timeout"],
    section: "generation",
    format: (v) => `${v}s`,
  },
  maxRetries: {
    label: "Số lần thử lại",
    path: ["llm", "max_retries"],
    section: "generation",
    format: (v) => `${v} lần`,
  },
};

/** Ghi đè ngưỡng đang lưu; backend cũ không có trường nguồn thì coi số trả về là ghi đè. */
function overrideFrom(score, source) {
  if (score === null || score === undefined) return null;
  if (source === undefined) return score;
  return source === "override" ? score : null;
}

export function valuesFromConfig(data) {
  const guardrails = data?.guardrails ?? {};
  return {
    temperature: data?.llm?.temperature ?? DEFAULTS.temperature,
    llmTimeout: data?.llm?.timeout ?? DEFAULTS.llmTimeout,
    maxRetries: data?.llm?.max_retries ?? DEFAULTS.maxRetries,
    topK: data?.retrieval?.top_k ?? DEFAULTS.topK,
    hybridVectorWeight: data?.retrieval?.hybrid_vector_weight ?? DEFAULTS.hybridVectorWeight,
    multiQueryEnabled: Boolean(data?.retrieval?.multi_query_enabled),
    multiQueryCount: data?.retrieval?.multi_query_count ?? DEFAULTS.multiQueryCount,
    multiQueryUseLlm: Boolean(data?.retrieval?.multi_query_use_llm),
    queryRewriteUseLlm: Boolean(data?.retrieval?.query_rewrite_use_llm),
    scopeEnabled: Boolean(guardrails.scope_enabled),
    minVectorScore: overrideFrom(guardrails.min_vector_score, guardrails.vector_threshold_source),
    minBm25NormScore: guardrails.min_bm25_norm_score ?? DEFAULTS.minBm25NormScore,
    // Backend cũ không trả nguồn ngưỡng rerank: không đoán, coi như chưa ghi đè.
    minRerankScore:
      guardrails.rerank_threshold_source === "override" ? guardrails.min_rerank_score ?? null : null,
    rerankerEnabled: Boolean(data?.reranker?.enabled),
    candidateMultiplier: data?.reranker?.candidate_multiplier ?? DEFAULTS.candidateMultiplier,
  };
}

/** Giá trị bảng hiệu chỉnh theo model (null nếu model chưa hiệu chỉnh). */
export function calibratedFromConfig(data) {
  const guardrails = data?.guardrails ?? {};
  const pick = (explicit, score, source) => {
    if (explicit !== undefined) return explicit;
    return source === "calibrated" ? score ?? null : null;
  };
  return {
    vector: pick(
      guardrails.calibrated_min_vector_score,
      guardrails.min_vector_score,
      guardrails.vector_threshold_source
    ),
    rerank: pick(
      guardrails.calibrated_min_rerank_score,
      guardrails.min_rerank_score,
      guardrails.rerank_threshold_source
    ),
  };
}

/** Hiển thị một giá trị bản nháp; ngưỡng `null` là "theo hiệu chỉnh" hoặc "bỏ qua". */
export function formatConfigValue(key, value, calibrated = {}) {
  const field = CONFIG_FIELDS[key];
  if (!field) return String(value);
  if (field.calibratedKey && (value === null || value === undefined)) {
    const fallback = calibrated[field.calibratedKey];
    return fallback === null || fallback === undefined
      ? "chưa hiệu chỉnh"
      : `hiệu chỉnh ${fixed2(fallback)}`;
  }
  return field.format(value);
}

function sameValue(a, b) {
  if (typeof a === "number" && typeof b === "number") return Math.abs(a - b) < 1e-9;
  return a === b;
}

export function isFieldChanged(values, saved, key) {
  return !sameValue(values[key], saved[key]);
}

/** Mục Settings có ít nhất một trường khác bản đã lưu (dùng cho chấm trong danh mục). */
export function listDirtySections(values, saved) {
  const sections = new Set();
  Object.entries(CONFIG_FIELDS).forEach(([key, field]) => {
    if (isFieldChanged(values, saved, key)) sections.add(field.section);
  });
  return [...sections];
}

/** Các trường khác bản đã lưu, theo thứ tự `CONFIG_FIELDS`, kèm chuỗi hiển thị cũ/mới. */
export function listConfigChanges(values, saved, calibrated = {}) {
  return Object.keys(CONFIG_FIELDS)
    .filter((key) => isFieldChanged(values, saved, key))
    .map((key) => ({
      key,
      label: CONFIG_FIELDS[key].label,
      from: formatConfigValue(key, saved[key], calibrated),
      to: formatConfigValue(key, values[key], calibrated),
    }));
}

/**
 * Payload PUT `/config` chỉ gồm trường đã đổi. Ngưỡng ghi đè `null` được gửi tường minh
 * để xoá ghi đè; `min_bm25_score` (BM25 thô, gate không còn dùng) không bao giờ được gửi.
 */
export function buildConfigPayload(values, saved) {
  const payload = {};
  Object.entries(CONFIG_FIELDS).forEach(([key, { path }]) => {
    if (!isFieldChanged(values, saved, key)) return;
    const [section, apiKey] = path;
    const value = values[key];
    payload[section] = payload[section] ?? {};
    payload[section][apiKey] = typeof value === "boolean" || value === null ? value : Number(value);
  });
  return payload;
}

/**
 * Gộp giá trị cấu hình mới từ máy chủ vào bản nháp đang sửa.
 *
 * Trường người dùng đã sửa cục bộ (`current[key] !== previousServer[key]`) được
 * giữ nguyên; trường còn lại nhận giá trị mới. Nhờ vậy lưu ở tab Mô hình cập nhật
 * ngay tab Cấu hình RAG mà không xoá bản nháp đang sửa ở tab đó.
 */
export function mergeConfigDraft(current, previousServer, nextServer) {
  if (!previousServer) return { ...nextServer };

  const merged = { ...nextServer };
  Object.keys(nextServer).forEach((key) => {
    if (current[key] !== previousServer[key]) {
      merged[key] = current[key];
    }
  });
  return merged;
}
