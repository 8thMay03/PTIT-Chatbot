import { describe, expect, it } from "vitest";
import { activeModelSummary, normalizeEnvLlmProvider } from "./activeModels";

function registry(overrides = {}) {
  return {
    profiles: [
      { id: "p1", kind: "llm", name: "Gemini Flash", provider: "gemini", model: "gemini-2.5-flash" },
      { id: "e1", kind: "embedding", name: "bge-m3", provider: "sentence-transformers", model: "BAAI/bge-m3", dimension: 1024 },
      { id: "r1", kind: "reranker", name: "BGE v2", provider: "cross-encoder", model: "BAAI/bge-reranker-v2-m3" },
    ],
    active: { llm: null, embedding: null, reranker: null },
    embedding_runtime: { profile_id: null, restart_required: false, load_error: null },
    env_defaults: {
      llm: { provider: "openai", model: "gpt-4.1-mini" },
      embedding: { provider: "openai", model: "text-embedding-3-small" },
    },
    ...overrides,
  };
}

describe("activeModelSummary", () => {
  it("chưa có dữ liệu kho thì trả null", () => {
    expect(activeModelSummary("llm", null, null)).toBeNull();
  });

  it("LLM: tên theo lựa chọn trong kho, nhà cung cấp/mô hình theo cấu hình đang chạy", () => {
    const config = { llm: { provider: "google", model: "gemini-2.5-flash", has_api_key: true } };
    expect(activeModelSummary("llm", registry({ active: { llm: "p1" } }), config)).toEqual({
      name: "Gemini Flash",
      meta: "Google Gemini · gemini-2.5-flash",
      status: { tone: "ok", label: "Đang chạy" },
    });
  });

  it("LLM: chưa chọn thì là cấu hình máy chủ; thiếu API key thì cảnh báo", () => {
    const summary = activeModelSummary("llm", registry(), { llm: { provider: "openai", model: "gpt-4.1-mini", has_api_key: false } });
    expect(summary.name).toBe("Cấu hình máy chủ");
    expect(summary.meta).toBe("OpenAI · gpt-4.1-mini");
    expect(summary.status).toEqual({ tone: "warn", label: "Thiếu API key" });
  });

  it("embedding: lỗi nạp ưu tiên hơn lựa chọn chưa áp dụng", () => {
    const pending = registry({
      active: { embedding: "e1" },
      embedding_runtime: { profile_id: null, restart_required: true, load_error: null },
    });
    expect(activeModelSummary("embedding", pending)).toEqual({
      name: "bge-m3",
      meta: "Sentence-Transformers · 1024 chiều",
      status: { tone: "warn", label: "Chưa áp dụng" },
    });
    const failed = registry({ embedding_runtime: { restart_required: true, load_error: "OOM" } });
    expect(activeModelSummary("embedding", failed).status.label).toBe("Lỗi khi nạp");
    expect(activeModelSummary("embedding", failed).meta).toBe("OpenAI · text-embedding-3-small");
  });

  it("reranker: Heuristic khi chưa chọn, báo đang tắt theo cấu hình", () => {
    expect(activeModelSummary("reranker", registry(), { reranker: { enabled: true } })).toEqual({
      name: "Heuristic",
      meta: "Không cần mô hình",
      status: { tone: "ok", label: "Đang bật" },
    });
    const off = activeModelSummary("reranker", registry({ active: { reranker: "r1" } }), { reranker: { enabled: false } });
    expect(off.name).toBe("BGE v2");
    expect(off.meta).toBe("Cross-Encoder · BAAI/bge-reranker-v2-m3");
    expect(off.status).toEqual({ tone: "warn", label: "Đang tắt" });
  });
});

describe("normalizeEnvLlmProvider", () => {
  it("quy tên provider trong .env về key của kho", () => {
    expect(normalizeEnvLlmProvider("google")).toBe("gemini");
    expect(normalizeEnvLlmProvider("AZURE_OPENAI")).toBe("azure");
    expect(normalizeEnvLlmProvider("openai")).toBe("openai");
    expect(normalizeEnvLlmProvider("ollama")).toBe("openai_compatible");
  });
});
