import { describe, expect, it } from "vitest";
import {
  KINDS,
  buildPayload,
  buildRerankerTestPayload,
  buildTestPayload,
  canTestConnection,
  draftFromProfile,
  emptyDraft,
  isDraftDirty,
  keyRule,
  sendsDocumentsToService,
  validateDraft,
} from "./catalog";

describe("catalog kho mô hình", () => {
  it("reranker Rerank API: Base URL + mô hình bắt buộc, khoá tuỳ chọn không dự phòng .env", () => {
    expect(KINDS.reranker.providers.map((item) => item.key)).toEqual(["cross-encoder", "rerank_api"]);
    expect(keyRule("reranker", "rerank_api")).toEqual({ envFallback: false });
    expect(keyRule("reranker", "cross-encoder")).toBeNull();
    expect(canTestConnection("reranker", "rerank_api")).toBe(true);
    expect(canTestConnection("reranker", "cross-encoder")).toBe(false);
    expect(sendsDocumentsToService("reranker", "rerank_api")).toBe(true);
    expect(sendsDocumentsToService("reranker", "cross-encoder")).toBe(false);

    const empty = { ...emptyDraft("reranker"), provider: "rerank_api" };
    expect(validateDraft("reranker", empty)).toEqual({ base_url: "Nhập base url.", model: "Nhập mô hình." });
    expect(validateDraft("reranker", { ...empty, base_url: "api.cohere.com", model: "m" })).toEqual({
      base_url: "Phải bắt đầu bằng http:// hoặc https://.",
    });

    const draft = { ...empty, base_url: " https://api.cohere.com/v2 ", model: "rerank-v3.5", apiKey: " rk-x " };
    expect(buildPayload("reranker", draft)).toEqual({
      kind: "reranker",
      name: "rerank-v3.5",
      provider: "rerank_api",
      base_url: "https://api.cohere.com/v2",
      model: "rerank-v3.5",
      api_key: "rk-x",
    });
    expect(buildRerankerTestPayload({ ...draft, apiKey: "" }, "r1")).toEqual({
      provider: "rerank_api",
      model: "rerank-v3.5",
      base_url: "https://api.cohere.com/v2",
      api_key: null,
      profile_id: "r1",
    });
  });

  it("bắt trường bắt buộc, URL và số chiều theo nhà cung cấp", () => {
    const llm = { ...emptyDraft("llm"), provider: "openai_compatible", base_url: "localhost:11434" };
    expect(validateDraft("llm", llm)).toEqual({
      base_url: "Phải bắt đầu bằng http:// hoặc https://.",
      model: "Nhập mô hình.",
    });

    const embedding = { ...emptyDraft("embedding"), model: "BAAI/bge-m3", dimension: "1.5" };
    expect(validateDraft("embedding", embedding)).toEqual({ dimension: "Phải là số nguyên dương." });
  });

  it("chỉ gửi trường của nhà cung cấp đang chọn, tên mặc định là tên mô hình", () => {
    const draft = {
      ...emptyDraft("llm"),
      provider: "gemini",
      model: " gemini-2.0-flash ",
      base_url: "https://bo-qua.example.com",
      apiKey: " sk-x ",
    };
    expect(buildPayload("llm", draft)).toEqual({
      kind: "llm",
      name: "gemini-2.0-flash",
      provider: "gemini",
      model: "gemini-2.0-flash",
      api_key: "sk-x",
    });

    const azure = {
      ...emptyDraft("llm"),
      provider: "azure",
      endpoint: "https://a.openai.azure.com",
      deployment_name: "gpt-4o-mini",
    };
    expect(buildPayload("llm", azure).name).toBe("gpt-4o-mini");
  });

  it("khi sửa: khoá trống giữ khoá cũ, có thể yêu cầu xoá khoá; reranker không gửi khoá", () => {
    const profile = { id: "p1", kind: "llm", name: "GPT", provider: "openai", model: "gpt-4.1", has_api_key: true };
    const draft = draftFromProfile(profile);
    expect(isDraftDirty("llm", draft, draft)).toBe(false);
    expect(buildPayload("llm", draft, { isEdit: true })).toEqual({
      name: "GPT",
      provider: "openai",
      model: "gpt-4.1",
      base_url: null,
    });
    const cleared = { ...draft, clearApiKey: true };
    expect(isDraftDirty("llm", cleared, draft)).toBe(true);
    expect(buildPayload("llm", cleared, { isEdit: true }).clear_api_key).toBe(true);

    const reranker = { ...emptyDraft("reranker"), model: "BAAI/bge-reranker-base", apiKey: "k" };
    expect(buildPayload("reranker", reranker)).toEqual({
      kind: "reranker",
      name: "BAAI/bge-reranker-base",
      provider: "cross-encoder",
      model: "BAAI/bge-reranker-base",
    });

    const embedding = { ...emptyDraft("embedding"), model: "BAAI/bge-m3", dimension: "1024" };
    expect(buildPayload("embedding", embedding).dimension).toBe(1024);
  });

  it("payload kiểm tra kết nối gửi profile_id để máy chủ dùng khoá đã lưu", () => {
    const draft = { ...emptyDraft("llm"), model: "gpt-4.1-mini" };
    expect(buildTestPayload(draft, "p1")).toMatchObject({
      provider: "openai",
      model: "gpt-4.1-mini",
      api_key: null,
      profile_id: "p1",
    });
  });
});
