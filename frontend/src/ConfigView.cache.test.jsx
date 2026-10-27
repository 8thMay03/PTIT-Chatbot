import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";
import { ToastProvider } from "./components/Toast";
import { queryKeys } from "./api";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
}

function baseConfig() {
  return {
    llm: {
      provider: "openai",
      model: "gpt-4.1-mini",
      temperature: 0,
      timeout: 30,
      max_retries: 2,
      openai_model: "gpt-4.1-mini",
      openai_has_key: true,
    },
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
    },
    guardrails: {
      scope_enabled: true,
      min_vector_score: 0.3,
      min_bm25_score: 2.0,
    },
    embedding: { provider: "openai", model: "text-embedding-3-small" },
    available_providers: { llm: [], embedding: [], reranker: [] },
  };
}

function applyPatch(config, patch) {
  const next = structuredClone(config);
  Object.entries(patch).forEach(([section, values]) => {
    next[section] = { ...(next[section] ?? {}), ...values };
  });
  return next;
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
    const setter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value"
    ).set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("cache cấu hình giữa ConfigView và ModelsView", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  async function renderViews(children) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>{children}</ToastProvider>
        </QueryClientProvider>
      );
    });
  }

  it("lưu trạng thái reranker ở tab Cấu hình thì tab Mô hình cập nhật ngay", async () => {
    let current = baseConfig();
    const fetchMock = vi.fn((_url, options = {}) => {
      if (options.method === "PUT") {
        current = applyPatch(current, JSON.parse(options.body));
      }
      return jsonResponse(current);
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderViews(
      <>
        <ConfigView />
        <ModelsView />
      </>
    );

    const rerankerSwitch = await waitFor(() =>
      container.querySelector('button[aria-labelledby="cfg-reranker-label"]')
    );
    await waitFor(() => container.textContent.includes("Đang bật"));

    expect(rerankerSwitch.getAttribute("aria-checked")).toBe("true");

    await click(rerankerSwitch);
    expect(rerankerSwitch.getAttribute("aria-checked")).toBe("false");

    const saveButton = [...container.querySelectorAll("button")].find(
      (item) => item.textContent.trim() === "Lưu cấu hình"
    );
    expect(saveButton.disabled).toBe(false);
    await click(saveButton);

    await waitFor(() => {
      const pill = [...container.querySelectorAll(".mdl-pill")].find(
        (item) => item.textContent.trim() === "Đang tắt"
      );
      return Boolean(pill);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/config$/),
      expect.objectContaining({ method: "PUT" })
    );
    expect(current.reranker.enabled).toBe(false);
  });

  it("nhận cấu hình mới từ tab khác nhưng giữ trường đang sửa dở", async () => {
    const initial = baseConfig();
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(initial)));

    await renderViews(<ConfigView />);

    const temperature = await waitFor(() =>
      container.querySelector('input[aria-label="Giá trị Temperature"]')
    );
    const rerankerSwitch = container.querySelector(
      'button[aria-labelledby="cfg-reranker-label"]'
    );
    expect(rerankerSwitch.getAttribute("aria-checked")).toBe("true");

    await changeInput(temperature, "0.7");
    expect(temperature.value).toBe("0.7");

    await act(async () => {
      queryClient.setQueryData(queryKeys.config, {
        ...initial,
        reranker: { ...initial.reranker, enabled: false },
      });
    });

    await waitFor(
      () => rerankerSwitch.getAttribute("aria-checked") === "false"
    );
    expect(temperature.value).toBe("0.7");
  });

  it("reset đồng bộ form ngay cả khi máy chủ trả đúng dữ liệu đã cache", async () => {
    const initial = baseConfig();
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(initial)));

    await renderViews(<ConfigView />);

    const temperature = await waitFor(() =>
      container.querySelector('input[aria-label="Giá trị Temperature"]')
    );
    await changeInput(temperature, "0.7");
    expect(container.querySelector(".unsaved-badge")).not.toBeNull();

    await click(container.querySelector(".btn-outline-reset"));
    const confirmReset = await waitFor(() => {
      const button = [...container.querySelectorAll("button")].find(
        (item) => item.textContent.trim() === "Khôi phục"
      );
      return button ? button : null;
    });
    await click(confirmReset);

    await waitFor(() => temperature.value === "0");
    await waitFor(() => !container.querySelector(".unsaved-badge"));

    // Sau reset, sửa tiếp rồi nhận cập nhật từ tab Mô hình: bản nháp phải được giữ.
    await changeInput(temperature, "0.7");
    const rerankerSwitch = container.querySelector(
      'button[aria-labelledby="cfg-reranker-label"]'
    );
    await act(async () => {
      queryClient.setQueryData(queryKeys.config, {
        ...initial,
        reranker: { ...initial.reranker, enabled: false },
      });
    });
    await waitFor(
      () => rerankerSwitch.getAttribute("aria-checked") === "false"
    );
    expect(temperature.value).toBe("0.7");
  });

  it("lưu chỉ API key thì xoá khoá khỏi input và tắt trạng thái chưa lưu", async () => {
    const initial = baseConfig();
    initial.llm.openai_has_key = false;
    let current = initial;
    const fetchMock = vi.fn((_url, options = {}) => {
      if (options.method === "PUT") {
        const patch = JSON.parse(options.body);
        current = applyPatch(current, patch);
        if (patch.llm?.openai_api_key) {
          current.llm.openai_has_key = true;
          delete current.llm.openai_api_key;
        }
      }
      return jsonResponse(current);
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderViews(<ModelsView />);

    const section = await waitFor(() => container.querySelector("#mdl-llm"));
    const keyInput = section.querySelector("#llm-openai-key");
    const saveButton = [...section.querySelectorAll("button")].find(
      (item) => item.textContent.trim() === "Lưu"
    );
    expect(saveButton.disabled).toBe(true);

    await changeInput(keyInput, "sk-test");
    expect(saveButton.disabled).toBe(false);
    await click(saveButton);

    await waitFor(() => keyInput.value === "");
    expect(saveButton.disabled).toBe(true);
    expect(section.querySelector(".mdl-dirty").textContent.trim()).toBe("");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/config$/),
      expect.objectContaining({ method: "PUT" })
    );
    expect(current.llm.openai_has_key).toBe(true);
  });
});
