import { describe, expect, it } from "vitest";
import { DEFAULTS } from "../lib/configDraft";
import { pipelineSummary, shortModelName } from "./pipelineSummary";

const config = {
  llm: { model: "gpt-4.1-mini" },
  reranker: { provider: "heuristic", model: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" },
};

describe("pipelineSummary", () => {
  it("tóm tắt bốn bước theo bản nháp", () => {
    const summary = pipelineSummary(DEFAULTS, config, { vector: 0.37, rerank: null });

    expect(summary).toEqual({
      retrieval: ["Top-K 4", "Vector 65%", "+3 truy vấn"],
      reranker: ["Heuristic", "3× ứng viên"],
      gate: ["BM25 ≥ 0.25", "Cos ≥ 0.37"],
      generation: ["gpt-4.1-mini", "T 0", "30s"],
    });
  });

  it("phản ánh giá trị nháp: tắt mở rộng, bật viết lại, tắt reranker", () => {
    const values = {
      ...DEFAULTS,
      topK: 6,
      hybridVectorWeight: 0.4,
      multiQueryEnabled: false,
      queryRewriteUseLlm: true,
      rerankerEnabled: false,
      temperature: 0.7,
    };
    const summary = pipelineSummary(values, config, {});

    expect(summary.retrieval).toEqual(["Top-K 6", "Vector 40%", "Viết lại bằng LLM"]);
    expect(summary.reranker).toEqual(["Đang tắt"]);
    expect(summary.generation[1]).toBe("T 0.7");
  });

  it("ngưỡng: ghi đè thắng hiệu chỉnh, thiếu cả hai thì báo bỏ qua", () => {
    expect(pipelineSummary({ ...DEFAULTS, minVectorScore: 0.5 }, config, { vector: 0.37 }).gate[1]).toBe(
      "Cos ≥ 0.50"
    );
    expect(pipelineSummary(DEFAULTS, config, { vector: null }).gate[1]).toBe("Cos: bỏ qua");
  });

  it("cross-encoder: hiện tên mô hình và ngưỡng rerank", () => {
    const crossConfig = { ...config, reranker: { provider: "cross-encoder", model: "BAAI/bge-reranker-v2-m3" } };
    const summary = pipelineSummary(DEFAULTS, crossConfig, { vector: 0.37, rerank: -1.65 });

    expect(summary.reranker[0]).toBe("bge-reranker-v2-m3");
    expect(summary.gate).toEqual(["BM25 ≥ 0.25", "Cos ≥ 0.37", "Rerank ≥ -1.65"]);
  });

  it("chưa có bản nháp thì trả danh sách rỗng", () => {
    expect(pipelineSummary(null, config)).toEqual({ retrieval: [], reranker: [], gate: [], generation: [] });
    expect(shortModelName(null)).toBe("mô hình hiện tại");
  });
});
