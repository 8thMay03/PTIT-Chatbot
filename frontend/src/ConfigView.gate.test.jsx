import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ConfigView from "./ConfigView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(payload),
  });
}

function baseConfig({ guardrails = {}, reranker = {} } = {}) {
  return {
    llm: { provider: "openai", model: "gpt-4.1-mini", temperature: 0, timeout: 30, max_retries: 2 },
    retrieval: {
      top_k: 4,
      hybrid_vector_weight: 0.65,
      multi_query_enabled: true,
      multi_query_count: 3,
      multi_query_use_llm: false,
    },
    reranker: {
      enabled: true,
      provider: "heuristic",
      model: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
      candidate_multiplier: 3,
      ...reranker,
    },
    guardrails: {
      scope_enabled: true,
      min_vector_score: 0.37,
      min_bm25_score: 2.0,
      min_bm25_norm_score: 0.25,
      min_rerank_score: null,
      vector_threshold_source: "calibrated",
      calibrated_min_vector_score: 0.37,
      rerank_threshold_source: "not_applicable",
      calibrated_min_rerank_score: -1.65,
      ...guardrails,
    },
    embedding: { provider: "openai", model: "text-embedding-3-small" },
    available_providers: { llm: [], embedding: [], reranker: [] },
  };
}

const OVERRIDE = { min_vector_score: 0.4, vector_threshold_source: "override" };
const UNCALIBRATED = {
  min_vector_score: null,
  vector_threshold_source: "uncalibrated",
  calibrated_min_vector_score: null,
};

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

async function changeInput(input, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonByText(container, text) {
  return [...container.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

describe("ConfigView — ngưỡng tin cậy, thanh lưu, vùng nguy hiểm", () => {
  let container;
  let root;
  let queryClient;
  let current;
  let putBodies;
  let putStatus;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    putBodies = [];
    putStatus = 200;
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  /** Máy chủ giả: PUT áp payload một phần; `null` ngưỡng vector quay về bảng hiệu chỉnh. */
  async function render(config) {
    current = config;
    const fetchMock = vi.fn((url, options = {}) => {
      if (options.method === "PUT") {
        const body = JSON.parse(options.body);
        putBodies.push(body);
        if (putStatus !== 200) return jsonResponse({ detail: "Giá trị không hợp lệ" }, putStatus);
        const next = structuredClone(current);
        Object.entries(body).forEach(([section, patch]) => {
          next[section] = { ...next[section], ...patch };
        });
        if (body.guardrails && "min_vector_score" in body.guardrails) {
          const value = body.guardrails.min_vector_score;
          next.guardrails.min_vector_score = value ?? next.guardrails.calibrated_min_vector_score;
          next.guardrails.vector_threshold_source = value === null ? "calibrated" : "override";
        }
        current = next;
      }
      return jsonResponse(current);
    });
    vi.stubGlobal("fetch", fetchMock);
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <ConfigView />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
    await waitFor(() => container.querySelector("#cfg-topk"));
    return fetchMock;
  }

  const vectorGroup = () => container.querySelector('[data-testid="gate-vector"]');
  const saveBar = () => container.querySelector('[role="region"][aria-label="Thay đổi chưa lưu"]');

  describe("nhóm Ngưỡng tin cậy (AC-01)", () => {
    it("không còn điều khiển BM25 thô; có độ khớp từ khóa 0–1 bước 0.01 và mô tả đúng cơ chế", async () => {
      await render(baseConfig());

      expect(container.querySelector("#cfg-minbm25")).toBeNull();
      expect(container.textContent).not.toContain("BM25 tối thiểu");
      const norm = container.querySelector("#cfg-minbm25norm");
      expect([norm.min, norm.max, norm.step, norm.value]).toEqual(["0", "1", "0.01", "0.25"]);
      expect(container.textContent).toContain("Ngưỡng tin cậy");
      expect(container.textContent).toContain("đoạn khớp nhất");
      expect(container.textContent).toContain("Chưa tìm thấy thông tin này trong tài liệu.");
      expect(container.textContent).toContain("không gọi mô hình");
    });

    it("calibrated: huy hiệu nêu embedding model, không có link bỏ ghi đè", async () => {
      await render(baseConfig());

      expect(vectorGroup().textContent).toContain("Đã hiệu chỉnh cho text-embedding-3-small");
      expect(vectorGroup().querySelector("#cfg-minvec-number").value).toBe("0.37");
      expect(vectorGroup().textContent).not.toContain("Dùng giá trị hiệu chỉnh");
    });

    it("override: huy hiệu Ghi đè và link Dùng giá trị hiệu chỉnh", async () => {
      await render(baseConfig({ guardrails: OVERRIDE }));

      expect(vectorGroup().querySelector(".config-status-badge").textContent).toBe("Ghi đè");
      expect(vectorGroup().querySelector("#cfg-minvec-number").value).toBe("0.4");
      expect(buttonByText(vectorGroup(), "Dùng giá trị hiệu chỉnh (0.37)")).toBeTruthy();
    });

    it("uncalibrated: cảnh báo tín hiệu bị bỏ qua, ô trống, không hiện 0.30", async () => {
      await render(baseConfig({ guardrails: UNCALIBRATED }));

      expect(vectorGroup().textContent).toContain("Chưa hiệu chỉnh cho text-embedding-3-small");
      expect(vectorGroup().textContent).toContain("đang bỏ qua tín hiệu này");
      expect(vectorGroup().querySelector("#cfg-minvec-number").value).toBe("");
      expect(vectorGroup().querySelector("#cfg-minvec")).toBeNull();
      expect(vectorGroup().textContent).not.toContain("0.30");
      expect(vectorGroup().querySelector(".config-status-badge")).toBeNull();
    });

    it("ngưỡng reranker chỉ hiện khi reranker bật và provider là cross-encoder", async () => {
      await render(baseConfig({ reranker: { provider: "heuristic" } }));
      expect(container.querySelector("#cfg-minrerank-number")).toBeNull();
      expect(container.querySelector('[data-testid="gate-rerank-na"]').textContent).toContain(
        "không áp dụng với Heuristic"
      );
    });

    it("cross-encoder bật thì hiện ngưỡng rerank; tắt reranker trong bản nháp thì ẩn", async () => {
      await render(
        baseConfig({
          reranker: { provider: "cross-encoder" },
          guardrails: { min_rerank_score: -1.65, rerank_threshold_source: "calibrated" },
        })
      );
      const rerank = container.querySelector('[data-testid="gate-rerank"]');
      expect(rerank.querySelector("#cfg-minrerank-number").value).toBe("-1.65");
      expect(rerank.textContent).toContain("Đã hiệu chỉnh cho mmarco-mMiniLMv2-L12-H384-v1");

      await click(container.querySelector('button[aria-labelledby="cfg-reranker-label"]'));
      expect(container.querySelector("#cfg-minrerank-number")).toBeNull();
      expect(container.querySelector('[data-testid="gate-rerank-na"]').textContent).toContain(
        "không áp dụng khi tắt xếp hạng lại"
      );
    });
  });

  describe("payload chỉ gồm trường đã đổi (AC-02, AC-03)", () => {
    it("đổi Top-K: payload không có ngưỡng cosine và không có min_bm25_score", async () => {
      await render(baseConfig({ guardrails: OVERRIDE }));

      await changeInput(container.querySelector("#cfg-topk"), "6");
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => putBodies.length === 1);

      expect(putBodies[0]).toEqual({ retrieval: { top_k: 6 } });
      await waitFor(() => !saveBar());
    });

    it("đổi ngưỡng cosine gửi đúng giá trị, không kèm trường khác", async () => {
      await render(baseConfig());

      await changeInput(container.querySelector("#cfg-minvec-number"), "0.45");
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => putBodies.length === 1);

      expect(putBodies[0]).toEqual({ guardrails: { min_vector_score: 0.45 } });
      expect(JSON.stringify(putBodies[0])).not.toContain("min_bm25_score");
    });

    it("model chưa hiệu chỉnh: ô rỗng khi đang gõ không tạo thay đổi, nhập số thì thành ghi đè", async () => {
      await render(baseConfig({ guardrails: UNCALIBRATED }));
      const input = vectorGroup().querySelector("#cfg-minvec-number");

      await changeInput(input, "");
      expect(saveBar()).toBeNull();

      await changeInput(input, "0.5");
      expect(vectorGroup().querySelector(".config-status-badge").textContent).toBe("Ghi đè");
      expect(buttonByText(vectorGroup(), "Bỏ ghi đè (mô hình chưa hiệu chỉnh nên tín hiệu này sẽ bị bỏ qua)")).toBeTruthy();
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => putBodies.length === 1);
      expect(putBodies[0]).toEqual({ guardrails: { min_vector_score: 0.5 } });
    });

    it("Dùng giá trị hiệu chỉnh gửi null rồi cập nhật form theo phản hồi", async () => {
      await render(baseConfig({ guardrails: OVERRIDE }));

      await click(buttonByText(vectorGroup(), "Dùng giá trị hiệu chỉnh (0.37)"));
      expect(saveBar().textContent).toContain("Ngưỡng ngữ nghĩa 0.40→hiệu chỉnh 0.37");
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => putBodies.length === 1);

      expect(putBodies[0]).toEqual({ guardrails: { min_vector_score: null } });
      await waitFor(() => vectorGroup().textContent.includes("Đã hiệu chỉnh cho text-embedding-3-small"));
      expect(vectorGroup().querySelector("#cfg-minvec-number").value).toBe("0.37");
      expect(saveBar()).toBeNull();
    });

    it("công tắc Viết lại câu hỏi bằng LLM gửi query_rewrite_use_llm", async () => {
      await render(baseConfig());

      const toggle = container.querySelector('button[aria-labelledby="cfg-rewrite-label"]');
      expect(toggle.getAttribute("aria-checked")).toBe("false");
      await click(toggle);
      expect(toggle.getAttribute("aria-checked")).toBe("true");
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => putBodies.length === 1);

      expect(putBodies[0]).toEqual({ retrieval: { query_rewrite_use_llm: true } });
    });

    it("dòng mô hình của Xếp hạng lại và Sinh câu trả lời dẫn tới mục mô hình", async () => {
      await render(baseConfig({ reranker: { provider: "cross-encoder" } }));

      const links = [...container.querySelectorAll(".config-model-link")].map((link) => [
        link.textContent.trim(),
        link.getAttribute("href"),
      ]);
      expect(links).toEqual([
        ["Đổi mô hình →", "#settings/models-reranker"],
        ["Đổi mô hình →", "#settings/models-llm"],
      ]);
    });
  });

  describe("thanh lưu và trường đã sửa (AC-04)", () => {
    it("không có thay đổi thì không có thanh lưu; form không còn header panel riêng", async () => {
      await render(baseConfig());

      expect(saveBar()).toBeNull();
      expect(container.querySelector(".settings-subtabs-header")).toBeNull();
      expect(container.querySelector(".unsaved-badge")).toBeNull();
      expect([...container.querySelectorAll(".config-section")].map((node) => node.id)).toEqual([
        "settings-section-retrieval",
        "settings-section-reranker",
        "settings-section-gate",
        "settings-section-generation",
      ]);
    });

    it("đếm số thay đổi, tóm tắt cũ→mới và đánh dấu từng trường", async () => {
      await render(baseConfig());

      await changeInput(container.querySelector("#cfg-topk"), "6");
      expect(saveBar().textContent).toContain("1 thay đổi chưa lưu");
      await click(container.querySelector('button[aria-labelledby="cfg-scope-label"]'));

      expect(saveBar().textContent).toContain("2 thay đổi chưa lưu");
      expect(saveBar().textContent).toContain("Top-K 4→6 · Chặn yêu cầu không an toàn Bật→Tắt");
      const topKGroup = container.querySelector("#cfg-topk").closest(".config-field-group");
      expect(topKGroup.classList.contains("is-changed")).toBe(true);
      expect(topKGroup.textContent).toContain("trước: 4");
      expect(topKGroup.querySelector('button[aria-label="Trả \\"Top-K\\" về giá trị đã lưu (4)"]')).toBeTruthy();

      // Mở danh sách đầy đủ.
      const summary = saveBar().querySelector(".save-bar-summary");
      await click(summary);
      expect(summary.getAttribute("aria-expanded")).toBe("true");
      expect(saveBar().querySelectorAll(".save-bar-list li")).toHaveLength(2);
    });

    it("nút trả từng trường chỉ trả trường đó", async () => {
      await render(baseConfig());

      await changeInput(container.querySelector("#cfg-topk"), "6");
      await changeInput(container.querySelector('input[aria-label="Giá trị Temperature"]'), "0.5");
      await click(container.querySelector('button[aria-label="Trả \\"Top-K\\" về giá trị đã lưu (4)"]'));

      expect(container.querySelector("#cfg-topk").value).toBe("4");
      expect(container.querySelector('input[aria-label="Giá trị Temperature"]').value).toBe("0.5");
      expect(saveBar().textContent).toContain("1 thay đổi chưa lưu");
    });

    it("Hủy thay đổi trả form về bản đã lưu và không gọi API", async () => {
      const fetchMock = await render(baseConfig());
      const callsBefore = fetchMock.mock.calls.length;

      await changeInput(container.querySelector("#cfg-topk"), "6");
      await changeInput(container.querySelector("#cfg-minbm25norm"), "0.4");
      await click(buttonByText(saveBar(), "Hủy thay đổi"));

      expect(saveBar()).toBeNull();
      expect(container.querySelector("#cfg-topk").value).toBe("4");
      expect(container.querySelector("#cfg-minbm25norm").value).toBe("0.25");
      expect(fetchMock.mock.calls.length).toBe(callsBefore);
    });

    it("lưu lỗi giữ bản nháp và thanh lưu", async () => {
      await render(baseConfig());
      putStatus = 422;

      await changeInput(container.querySelector("#cfg-topk"), "6");
      await click(buttonByText(saveBar(), "Lưu"));
      await waitFor(() => document.body.textContent.includes("CHƯA được lưu"));

      expect(container.querySelector("#cfg-topk").value).toBe("6");
      expect(saveBar().textContent).toContain("1 thay đổi chưa lưu");
    });

    it("beforeunload chỉ chặn khi còn thay đổi chưa lưu", async () => {
      await render(baseConfig());
      const fire = () => {
        const event = new Event("beforeunload", { cancelable: true });
        window.dispatchEvent(event);
        return event.defaultPrevented;
      };

      expect(fire()).toBe(false);
      await changeInput(container.querySelector("#cfg-topk"), "6");
      expect(fire()).toBe(true);
    });
  });

  it("Khôi phục mặc định nằm trong Vùng nguy hiểm và vẫn qua hộp xác nhận (AC-05)", async () => {
    await render(baseConfig());

    const zone = container.querySelector(".config-danger-zone");
    expect(zone.textContent).toContain("Vùng nguy hiểm");
    await click(buttonByText(zone, "Khôi phục mặc định…"));

    const dialog = await waitFor(() => document.querySelector('[role="dialog"], [role="alertdialog"]'));
    expect(dialog.textContent).toContain("Khôi phục cấu hình mặc định?");
    expect(buttonByText(dialog, "Khôi phục")).toBeTruthy();
  });
});
