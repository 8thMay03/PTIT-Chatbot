import { describe, expect, it } from "vitest";
import {
  decideGate,
  signalsFromContexts,
  thresholdsFromRetrievalResult,
} from "./gateDecision";

/*
 * Bộ ca chép từ `backend/tests/test_retrieval_confidence.py`. Luật gate phải giống
 * `assess_context` trong `backend/app/generation/confidence.py`; sửa một bên thì
 * sửa cả bên kia và chạy lại cả hai bộ test.
 */

function thresholds({
  bm25 = 0.25,
  vector = 0.37,
  rerank = null,
  vectorSource = "calibrated",
} = {}) {
  return {
    min_bm25_norm_score: bm25,
    min_vector_score: vector,
    min_rerank_score: rerank,
    vector_source: vectorSource,
  };
}

describe("decideGate", () => {
  it("đạt khi mọi tín hiệu vượt ngưỡng; tín hiệu là max trên các đoạn", () => {
    const decision = decideGate(
      [
        { vector_score: 0.62, bm25_norm_score: 0.41, rerank_score: 3.2 },
        { vector_score: 0.3, bm25_norm_score: null, rerank_score: -4.0 },
      ],
      thresholds({ rerank: -1.65 })
    );

    expect(decision.strong).toBe(true);
    expect(decision.reason).toBe("passed");
    expect(decision.signals).toEqual({ vector: 0.62, bm25_norm: 0.41, rerank: 3.2 });
  });

  it.each([
    [{ vector_score: 0.62, bm25_norm_score: 0.2, rerank_score: 3.0 }, "below_bm25_norm"],
    [{ vector_score: 0.33, bm25_norm_score: 0.4, rerank_score: 3.0 }, "below_vector"],
    [{ vector_score: 0.62, bm25_norm_score: 0.4, rerank_score: -2.0 }, "below_rerank"],
  ])("trượt khi một tín hiệu dưới ngưỡng %#", (context, reason) => {
    const decision = decideGate([context], thresholds({ rerank: -1.65 }));

    expect(decision.strong).toBe(false);
    expect(decision.reason).toBe(reason);
  });

  it("thiếu tín hiệu tính là trượt", () => {
    expect(decideGate([{ vector_score: 0.9 }], thresholds()).reason).toBe("below_bm25_norm");
    expect(
      decideGate([{ vector_score: 0.9, bm25_norm_score: 0.5 }], thresholds({ rerank: -1.65 })).reason
    ).toBe("below_rerank");
  });

  it("bỏ qua tín hiệu có ngưỡng null", () => {
    const decision = decideGate(
      [{ vector_score: 0.1, bm25_norm_score: 0.3, rerank_score: -9 }],
      thresholds({ vector: null, rerank: null, vectorSource: "uncalibrated" })
    );

    expect(decision.strong).toBe(true);
    expect(decision.reason).toBe("passed_uncalibrated_model");
  });

  it("không có đoạn nào thì từ chối với no_context", () => {
    const decision = decideGate([], thresholds());

    expect(decision.strong).toBe(false);
    expect(decision.reason).toBe("no_context");
    expect(decision.signals).toEqual({ vector: null, bm25_norm: null, rerank: null });
  });
});

describe("signalsFromContexts", () => {
  it("bỏ qua điểm null và điểm không phải số", () => {
    expect(
      signalsFromContexts([
        { vector_score: null, bm25_norm_score: "0.4" },
        { vector_score: 0.5, bm25_norm_score: "không phải số" },
      ])
    ).toEqual({ vector: 0.5, bm25_norm: 0.4, rerank: null });
  });
});

describe("thresholdsFromRetrievalResult", () => {
  it("lấy ngưỡng hiệu lực từ retrieval_debug.confidence", () => {
    const thresholdsValue = thresholds({ rerank: -1.65 });
    expect(
      thresholdsFromRetrievalResult({
        retrieval_debug: { confidence: { thresholds: thresholdsValue } },
      })
    ).toBe(thresholdsValue);
  });
});
