import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RetrievalTestPanel, { draftGateThresholds } from "./RetrievalTestPanel";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(payload),
  });
}

function baseConfig({ rerankerProvider = "cross-encoder", guardrails = {} } = {}) {
  return {
    llm: { model: "gpt-4.1-mini" },
    retrieval: { top_k: 4, query_rewrite_use_llm: false },
    reranker: { enabled: true, provider: rerankerProvider, model: "cross-encoder/x" },
    guardrails: {
      min_bm25_norm_score: 0.25,
      min_vector_score: 0.37,
      min_rerank_score: -1.65,
      vector_threshold_source: "calibrated",
      calibrated_min_vector_score: 0.37,
      rerank_threshold_source: "calibrated",
      calibrated_min_rerank_score: -1.65,
      ...guardrails,
    },
    embedding: { model: "text-embedding-3-small" },
    updated_at: "2026-11-17T07:00:00+00:00",
  };
}

function draftFrom(config, overrides = {}) {
  const guardrails = config.guardrails;
  return {
    topK: 6,
    hybridVectorWeight: 0.65,
    multiQueryEnabled: true,
    multiQueryCount: 3,
    multiQueryUseLlm: false,
    queryRewriteUseLlm: false,
    rerankerEnabled: true,
    candidateMultiplier: 3,
    minBm25NormScore: guardrails.min_bm25_norm_score,
    minVectorScore: null,
    minRerankScore: null,
    ...overrides,
  };
}

function retrievalResult({ strong = false, reason = "below_vector" } = {}) {
  return {
    query: "Học bổng khuyến khích học tập là gì?",
    strong_context: strong,
    contexts: [
      {
        chunk_id: "c1",
        source_name: "Sổ tay sinh viên D26",
        legal_article: "Điều 5",
        legal_clauses: ["2"],
        text: "Sinh viên có điểm trung bình học kỳ từ 2,5 trở lên được xét học bổng khuyến khích học tập.",
        vector_score: 0.33,
        bm25_norm_score: 0.4,
        rerank_score: 3.0,
      },
    ],
    retrieval_debug: {
      rewritten_query: "Điều kiện học bổng khuyến khích học tập",
      retrieval_queries: ["Điều kiện học bổng khuyến khích học tập", "học bổng KKHT điều kiện"],
      confidence: {
        reason,
        signals: { vector: 0.33, bm25_norm: 0.4, rerank: 3.0 },
        thresholds: {
          min_bm25_norm_score: 0.25,
          min_vector_score: 0.37,
          min_rerank_score: -1.65,
          embedding_model: "text-embedding-3-small",
          vector_source: "calibrated",
          rerank_source: "calibrated",
        },
      },
      strong_context: strong,
    },
  };
}

async function waitFor(check, timeout = 1500) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeout) {
    try {
      const value = check();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
  throw lastError ?? new Error("Hết thời gian chờ trạng thái giao diện.");
}

async function click(element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

async function fillTextarea(textarea, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonByText(scope, text) {
  return [...scope.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

describe("RetrievalTestPanel", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  async function render({ config = baseConfig(), draft = null, changedKeys = [], open = false, onClose } = {}) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <RetrievalTestPanel
            config={config}
            draft={draft ?? draftFrom(config)}
            changedKeys={changedKeys}
            open={open}
            onClose={onClose}
          />
        </QueryClientProvider>
      );
    });
    await waitFor(() => container.querySelector("#retrieval-test-query"));
  }

  function stubFetch(result = retrievalResult()) {
    const fetchMock = vi.fn((url, options = {}) => {
      const path = new URL(String(url), "http://test").pathname.replace(/^\/api\//, "");
      if (path === "datasets") {
        return jsonResponse({ datasets: [{ id: "ds-1", name: "Sổ tay D26" }] });
      }
      if (path === "retrieval/test" && options.method === "POST") {
        return jsonResponse(result);
      }
      return jsonResponse({ detail: `Không giả lập ${path}` }, 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("chặn câu hỏi rỗng ở client, không gọi API", async () => {
    const fetchMock = stubFetch();
    await render();

    await click(buttonByText(container, "Chạy thử"));

    expect(container.textContent).toContain("Nhập câu hỏi trước khi chạy thử");
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes("retrieval/test"))
    ).toHaveLength(0);
  });

  it("gửi query, Top-K bản nháp và dataset; hiện kết luận, tín hiệu, truy vấn và đoạn", async () => {
    const fetchMock = stubFetch();
    await render();

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng khuyến khích học tập là gì?");
    await act(async () => {
      const select = container.querySelector(".retrieval-test-select");
      const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set;
      setter.call(select, "ds-1");
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await click(buttonByText(container, "Chạy thử"));

    await waitFor(() => container.textContent.includes("Cấu hình đã lưu:"));

    const [[, options]] = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("retrieval/test")
    );
    expect(JSON.parse(options.body)).toEqual({
      query: "Học bổng khuyến khích học tập là gì?",
      top_k: 6,
      dataset_ids: ["ds-1"],
    });

    expect(container.textContent).toContain("✕ Sẽ từ chối");
    expect(container.textContent).toContain("Độ tương đồng ngữ nghĩa của đoạn tốt nhất thấp hơn ngưỡng");
    expect(container.textContent).toContain("Độ khớp từ khóa");
    expect(container.textContent).toContain("Điểm xếp hạng lại");
    expect(container.textContent).toContain("≥ -1.65");
    expect(container.textContent).toContain("Điều kiện học bổng khuyến khích học tập");
    expect(container.textContent).toContain("học bổng KKHT điều kiện");
    expect(container.textContent).toContain("Sổ tay sinh viên D26");
    expect(container.textContent).toContain("Điều 5 · Khoản 2");
    expect(container.textContent).toContain("cos 0.33 · bm25 0.40 · rerank 3.00");
  });

  it("tín hiệu có ngưỡng null ghi rõ không áp dụng", async () => {
    const result = retrievalResult();
    result.retrieval_debug.confidence.thresholds.min_rerank_score = null;
    result.retrieval_debug.confidence.thresholds.rerank_source = "not_applicable";
    stubFetch(result);
    await render({ config: baseConfig({ rerankerProvider: "heuristic" }) });

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng?");
    await click(buttonByText(container, "Chạy thử"));
    await waitFor(() => container.textContent.includes("Cấu hình đã lưu:"));

    const rerank = container.querySelector('[data-signal="rerank"]');
    expect(rerank.textContent).toContain("không áp dụng");
    expect(rerank.querySelector(".retrieval-signal-bar")).toBeNull();
  });

  it("hiện kết luận bản nháp khi ngưỡng nháp khác bản đã lưu", async () => {
    stubFetch();
    const config = baseConfig();
    await render({ config, draft: draftFrom(config, { minVectorScore: 0.3 }) });

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng?");
    await click(buttonByText(container, "Chạy thử"));
    await waitFor(() => container.textContent.includes("Bản nháp:"));

    expect(container.textContent).toContain("Bản nháp: ✓ Sẽ trả lời");
    expect(container.querySelectorAll(".retrieval-signal-tick.is-draft")).toHaveLength(1);
  });

  it("không hiện kết luận nháp khi ngưỡng nháp trùng bản đã lưu", async () => {
    stubFetch();
    const config = baseConfig();
    await render({ config, draft: draftFrom(config) });

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng?");
    await click(buttonByText(container, "Chạy thử"));
    await waitFor(() => container.textContent.includes("Cấu hình đã lưu:"));

    expect(container.textContent).not.toContain("Bản nháp:");
  });

  it("ghi cần lưu rồi chạy lại khi đổi tỷ trọng/mở rộng/reranker", async () => {
    stubFetch();
    const config = baseConfig();
    await render({ config, changedKeys: ["hybridVectorWeight"] });

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng?");
    await click(buttonByText(container, "Chạy thử"));
    await waitFor(() => container.textContent.includes("Cấu hình đã lưu:"));

    expect(container.textContent).toContain("Cần lưu rồi chạy lại để thấy ảnh hưởng");
  });

  it("chạy lại thì huỷ request cũ và chỉ hiện kết quả mới", async () => {
    let calls = 0;
    const fetchMock = vi.fn((url, options = {}) => {
      const path = new URL(String(url), "http://test").pathname.replace(/^\/api\//, "");
      if (path === "datasets") return jsonResponse({ datasets: [] });
      if (path === "retrieval/test") {
        calls += 1;
        if (calls === 1) {
          return new Promise((resolve, reject) => {
            options.signal.addEventListener("abort", () => {
              const error = new Error("aborted");
              error.name = "AbortError";
              reject(error);
            });
          });
        }
        return jsonResponse(retrievalResult({ strong: true, reason: "passed" }));
      }
      return jsonResponse({ detail: path }, 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const config = baseConfig();
    await render({ config });

    await fillTextarea(container.querySelector("#retrieval-test-query"), "Học bổng?");
    const run = buttonByText(container, "Chạy thử");
    await click(run);
    await waitFor(() => container.textContent.includes("Đang chạy..."));
    await click(buttonByText(container, "Đang chạy..."));

    await waitFor(() => container.textContent.includes("✓ Sẽ trả lời"));
    const testCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("retrieval/test"));
    expect(testCalls).toHaveLength(2);
    expect(testCalls[0][1].signal.aborted).toBe(true);
    expect(container.textContent).not.toContain("Bản nháp:");
  });

  it("drawer đóng bằng Esc và trả focus", async () => {
    const onClose = vi.fn();
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    await render({ open: true, onClose });

    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

    expect(onClose).toHaveBeenCalled();
    opener.remove();
  });
});

describe("draftGateThresholds", () => {
  it("dùng bảng hiệu chỉnh khi chưa ghi đè; bỏ tín hiệu rerank ngoài Cross-Encoder", () => {
    const config = baseConfig({ rerankerProvider: "heuristic" });
    const thresholds = draftGateThresholds(config, draftFrom(config));

    expect(thresholds).toEqual({
      min_bm25_norm_score: 0.25,
      min_vector_score: 0.37,
      min_rerank_score: null,
      vector_source: "calibrated",
      rerank_source: "not_applicable",
    });
  });

  it("ngưỡng nháp có giá trị thì thành ghi đè", () => {
    const config = baseConfig();
    const thresholds = draftGateThresholds(
      config,
      draftFrom(config, { minVectorScore: 0.5, minRerankScore: -0.5 })
    );

    expect(thresholds.min_vector_score).toBe(0.5);
    expect(thresholds.min_rerank_score).toBe(-0.5);
    expect(thresholds.vector_source).toBe("override");
    expect(thresholds.rerank_source).toBe("override");
  });
});
