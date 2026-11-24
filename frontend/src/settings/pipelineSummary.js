/**
 * Nhãn ngắn mô tả cấu hình từng bước của "Hệ thống trả lời", tính từ bản nháp.
 * Dùng ở dải bước (desktop) và danh sách mục (mobile).
 */

export const RERANKER_PROVIDER_LABELS = {
  heuristic: "Heuristic",
  "cross-encoder": "Cross-Encoder",
  cohere: "Cohere",
  jina: "Jina AI",
  voyage: "Voyage AI",
  pinecone: "Pinecone",
  tei: "HF TEI",
  rerank_api: "Rerank API",
};

/** Reranker gọi dịch vụ ngoài: điểm liên quan trong [0, 1], chưa có bảng hiệu chỉnh. */
export function isApiReranker(provider) {
  return Object.hasOwn(RERANKER_PROVIDER_LABELS, provider) && provider !== "heuristic" && provider !== "cross-encoder";
}

/**
 * Reranker cho điểm tuyệt đối nên confidence gate dùng được ngưỡng rerank. Heuristic chuẩn
 * hoá trong danh sách ứng viên nên không dùng được; reranker qua API chỉ dùng khi có ghi đè.
 */
export function rerankScoreApplies(provider) {
  return provider === "cross-encoder" || isApiReranker(provider);
}

export function shortModelName(model) {
  return model ? String(model).split("/").pop() : "mô hình hiện tại";
}

const fixed2 = (value) => Number(value).toFixed(2);

/** Ngưỡng hiệu lực: ghi đè nếu có, không thì giá trị hiệu chỉnh; `null` = tín hiệu bị bỏ qua. */
function effectiveThreshold(override, calibratedValue) {
  if (override !== null && override !== undefined) return override;
  return calibratedValue ?? null;
}

/**
 * @param values bản nháp (`valuesFromConfig`)
 * @param config phản hồi `/config` (tên mô hình, provider reranker)
 * @param calibrated `{ vector, rerank }` từ `calibratedFromConfig`
 * @returns {{retrieval: string[], reranker: string[], gate: string[], generation: string[]}}
 */
export function pipelineSummary(values, config, calibrated = {}) {
  if (!values) return { retrieval: [], reranker: [], gate: [], generation: [] };

  const retrieval = [
    `Top-K ${values.topK}`,
    `Vector ${Math.round(Number(values.hybridVectorWeight) * 100)}%`,
  ];
  if (values.multiQueryEnabled) retrieval.push(`+${values.multiQueryCount} truy vấn`);
  if (values.queryRewriteUseLlm) retrieval.push("Viết lại bằng LLM");

  const provider = config?.reranker?.provider;
  const reranker = values.rerankerEnabled
    ? [
        provider === "cross-encoder"
          ? shortModelName(config?.reranker?.model)
          : isApiReranker(provider)
            ? `${RERANKER_PROVIDER_LABELS[provider]} · ${shortModelName(config?.reranker?.model)}`
            : RERANKER_PROVIDER_LABELS[provider] ?? provider ?? "Reranker",
        `${values.candidateMultiplier}× ứng viên`,
      ]
    : ["Đang tắt"];

  const gate = [`BM25 ≥ ${fixed2(values.minBm25NormScore)}`];
  const vector = effectiveThreshold(values.minVectorScore, calibrated.vector);
  gate.push(vector === null ? "Cos: bỏ qua" : `Cos ≥ ${fixed2(vector)}`);
  if (values.rerankerEnabled && rerankScoreApplies(provider)) {
    const rerank = effectiveThreshold(values.minRerankScore, calibrated.rerank);
    gate.push(rerank === null ? "Rerank: bỏ qua" : `Rerank ≥ ${fixed2(rerank)}`);
  }

  const generation = [
    shortModelName(config?.llm?.model),
    `T ${Number(values.temperature)}`,
    `${values.llmTimeout}s`,
  ];

  return { retrieval, reranker, gate, generation };
}
