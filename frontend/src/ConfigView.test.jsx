import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ConfigView from "./ConfigView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function baseConfig() {
  return {
    llm: { temperature: 0, timeout: 30, max_retries: 2 },
    retrieval: {
      top_k: 4,
      hybrid_vector_weight: 0.65,
      multi_query_enabled: true,
      multi_query_count: 3,
      multi_query_use_llm: false,
    },
    reranker: { enabled: true, candidate_multiplier: 3 },
    guardrails: { scope_enabled: true, min_vector_score: 0.3, min_bm25_score: 2.0 },
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

async function changeInput(input, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonByText(container, text) {
  return [...container.querySelectorAll("button")].find(
    (item) => item.textContent.trim() === text
  );
}

describe("ConfigView — thao tác chỉnh sửa", () => {
  let container;
  let root;
  let queryClient;
  let fetchMock;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(baseConfig()) })
    );
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
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  it("đánh dấu trường đã sửa và hoàn tác riêng trường đó", async () => {
    const topK = container.querySelector('input[aria-label="Số đoạn nạp vào LLM"]');
    await changeInput(topK, "7");

    const revertButton = await waitFor(() =>
      container.querySelector('button[aria-label^="Hoàn tác Số đoạn nạp vào LLM"]')
    );
    expect(container.querySelector(".unsaved-badge").textContent).toContain("1 thay đổi");
    expect(container.querySelector(".cfg-savebar-fields").textContent).toBe("Top-K");

    await click(revertButton);
    await waitFor(() => !container.querySelector(".unsaved-badge"));
    expect(container.querySelector("#cfg-topk").value).toBe("4");
    expect(topK.value).toBe("4");
  });

  it("Huỷ thay đổi đưa mọi trường về bản đã lưu mà không gọi máy chủ", async () => {
    await changeInput(container.querySelector('input[aria-label="Giá trị Temperature"]'), "0.7");
    await click(container.querySelector('button[aria-labelledby="cfg-scope-label"]'));
    expect(container.querySelector(".unsaved-badge").textContent).toContain("2 thay đổi");

    await click(buttonByText(container, "Huỷ thay đổi"));

    await waitFor(() => !container.querySelector(".unsaved-badge"));
    expect(
      container.querySelector('button[aria-labelledby="cfg-scope-label"]').getAttribute("aria-checked")
    ).toBe("true");
    expect(buttonByText(container, "Lưu cấu hình").disabled).toBe(true);
    expect(fetchMock.mock.calls.every(([, options = {}]) => options.method !== "PUT")).toBe(true);
  });

  it("khoá cài đặt phụ khi tắt công tắc cha và kẹp số nhập ngoài khoảng", async () => {
    await click(container.querySelector('button[aria-labelledby="cfg-reranker-label"]'));
    expect(container.querySelector("#cfg-candidate").disabled).toBe(true);
    expect(
      container.querySelector('input[aria-label="Hệ số ứng viên sơ bộ"]').disabled
    ).toBe(true);

    const timeout = container.querySelector(
      'input[aria-label="Thời gian chờ tối đa, tính bằng giây"]'
    );
    await changeInput(timeout, "500");
    // Giá trị ngoài khoảng chưa được nhận khi đang gõ...
    expect(container.querySelector("#cfg-timeout").value).toBe("30");
    await act(async () => {
      timeout.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    });
    // ...và được kẹp về mức tối đa khi rời ô.
    await waitFor(() => timeout.value === "90");
    expect(container.querySelector("#cfg-timeout").value).toBe("90");
  });
});
