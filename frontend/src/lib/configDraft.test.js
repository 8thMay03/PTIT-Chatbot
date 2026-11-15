import { describe, expect, it } from "vitest";
import {
  buildConfigPayload,
  calibratedFromConfig,
  listConfigChanges,
  mergeConfigDraft,
  valuesFromConfig,
} from "./configDraft";

function config(guardrails = {}) {
  return {
    llm: { temperature: 0, timeout: 30, max_retries: 2 },
    retrieval: { top_k: 4, hybrid_vector_weight: 0.65, multi_query_enabled: true, multi_query_count: 3 },
    reranker: { enabled: true, provider: "cross-encoder", candidate_multiplier: 3 },
    guardrails: {
      scope_enabled: true,
      min_vector_score: 0.37,
      min_bm25_score: 2.0,
      min_bm25_norm_score: 0.25,
      min_rerank_score: -1.65,
      vector_threshold_source: "calibrated",
      calibrated_min_vector_score: 0.37,
      rerank_threshold_source: "calibrated",
      calibrated_min_rerank_score: -1.65,
      ...guardrails,
    },
  };
}

describe("mergeConfigDraft", () => {
  it("nhận giá trị mới từ tab khác nhưng giữ trường đang sửa dở", () => {
    const previous = { rerankerEnabled: true, temperature: 0, topK: 4 };
    const current = { rerankerEnabled: true, temperature: 0.7, topK: 4 };
    const next = { rerankerEnabled: false, temperature: 0, topK: 6 };

    expect(mergeConfigDraft(current, previous, next)).toEqual({
      rerankerEnabled: false,
      temperature: 0.7,
      topK: 6,
    });
  });

  it("lần đọc đầu tiên lấy toàn bộ giá trị máy chủ", () => {
    const next = { rerankerEnabled: false, temperature: 0.2, topK: 5 };
    expect(mergeConfigDraft({}, null, next)).toEqual(next);
  });
});

describe("valuesFromConfig", () => {
  it("ngưỡng theo bảng hiệu chỉnh là null (không ghi đè), không rơi về 0.30", () => {
    const values = valuesFromConfig(config());
    expect(values.minVectorScore).toBeNull();
    expect(values.minRerankScore).toBeNull();
    expect(values.minBm25NormScore).toBe(0.25);
    expect(values).not.toHaveProperty("minBm25Score");
  });

  it("ngưỡng ghi đè giữ đúng số", () => {
    const values = valuesFromConfig(
      config({
        min_vector_score: 0.4,
        vector_threshold_source: "override",
        min_rerank_score: -1,
        rerank_threshold_source: "override",
      })
    );
    expect(values.minVectorScore).toBe(0.4);
    expect(values.minRerankScore).toBe(-1);
  });

  it("model chưa hiệu chỉnh: ngưỡng null và không có giá trị hiệu chỉnh", () => {
    const data = config({
      min_vector_score: null,
      vector_threshold_source: "uncalibrated",
      calibrated_min_vector_score: null,
    });
    expect(valuesFromConfig(data).minVectorScore).toBeNull();
    expect(calibratedFromConfig(data).vector).toBeNull();
  });

  it("backend thiếu trường mới không làm vỡ form", () => {
    const values = valuesFromConfig({ guardrails: { scope_enabled: true, min_vector_score: 0.3 } });
    expect(values.minBm25NormScore).toBe(0.25);
    expect(values.minRerankScore).toBeNull();
    expect(calibratedFromConfig({ guardrails: {} })).toEqual({ vector: null, rerank: null });
  });
});

describe("buildConfigPayload", () => {
  const saved = valuesFromConfig(config());

  it("chỉ gửi trường đã đổi", () => {
    expect(buildConfigPayload({ ...saved, topK: 6 }, saved)).toEqual({ retrieval: { top_k: 6 } });
    expect(buildConfigPayload(saved, saved)).toEqual({});
  });

  it("gửi null tường minh để xoá ghi đè, không bao giờ gửi min_bm25_score", () => {
    const overridden = { ...saved, minVectorScore: 0.4 };
    const payload = buildConfigPayload({ ...overridden, minVectorScore: null, scopeEnabled: false }, overridden);
    expect(payload).toEqual({ guardrails: { min_vector_score: null, scope_enabled: false } });
    expect(JSON.stringify(payload)).not.toContain("min_bm25_score");
  });

  it("ánh xạ ngưỡng BM25 chuẩn hoá và các nhóm khác", () => {
    const payload = buildConfigPayload(
      { ...saved, minBm25NormScore: 0.3, temperature: 0.2, rerankerEnabled: false },
      saved
    );
    expect(payload).toEqual({
      llm: { temperature: 0.2 },
      reranker: { enabled: false },
      guardrails: { min_bm25_norm_score: 0.3 },
    });
  });
});

describe("listConfigChanges", () => {
  it("liệt kê nhãn cũ→mới theo thứ tự cố định", () => {
    const saved = valuesFromConfig(config());
    const changes = listConfigChanges(
      { ...saved, minVectorScore: 0.4, topK: 6 },
      saved,
      calibratedFromConfig(config())
    );
    expect(changes).toEqual([
      { key: "topK", label: "Top-K", from: "4", to: "6" },
      { key: "minVectorScore", label: "Ngưỡng ngữ nghĩa", from: "hiệu chỉnh 0.37", to: "0.40" },
    ]);
  });
});
