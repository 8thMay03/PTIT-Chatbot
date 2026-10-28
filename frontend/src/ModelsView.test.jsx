import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ModelsView from "./ModelsView";
import { ToastProvider } from "./components/Toast";

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
      openai_model: "gpt-4.1-mini",
      openai_has_key: true,
    },
    reranker: {
      enabled: true,
      provider: "heuristic",
      model: "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    },
    embedding: { provider: "openai", model: "text-embedding-3-small" },
    persistence: { secret_encryption_enabled: true },
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

async function keyDown(element, key) {
  await act(async () => {
    element.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  });
}

async function changeInput(input, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("ModelsView — thanh luồng xử lý", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(baseConfig())));
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  async function render() {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <ModelsView />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
    return waitFor(() => container.querySelector('[role="tablist"]'));
  }

  const tab = (key) => container.querySelector(`#mdl-tab-${key}`);
  const panel = (key) => container.querySelector(`#mdl-panel-${key}`);

  it("mở khâu LLM mặc định và tóm tắt cấu hình đang chạy trên từng thẻ", async () => {
    await render();

    expect(tab("llm").getAttribute("aria-selected")).toBe("true");
    expect(panel("llm").hidden).toBe(false);
    expect(panel("reranker").hidden).toBe(true);
    expect(panel("embedding").hidden).toBe(true);

    expect(tab("embedding").textContent).toContain("text-embedding-3-small");
    expect(tab("reranker").textContent).toContain("Đang bật");
    expect(tab("llm").textContent).toContain("gpt-4.1-mini");
  });

  it("đổi khâu bằng chuột và phím mũi tên", async () => {
    await render();

    await click(tab("reranker"));
    expect(tab("reranker").getAttribute("aria-selected")).toBe("true");
    expect(panel("reranker").hidden).toBe(false);
    expect(panel("llm").hidden).toBe(true);

    await keyDown(tab("reranker"), "ArrowLeft");
    expect(tab("embedding").getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(tab("embedding"));

    await keyDown(tab("embedding"), "ArrowLeft");
    expect(tab("llm").getAttribute("aria-selected")).toBe("true");

    await keyDown(tab("llm"), "Home");
    expect(tab("embedding").getAttribute("aria-selected")).toBe("true");
  });

  it("giữ bản nháp khi đổi khâu và đánh dấu khâu chưa lưu", async () => {
    await render();

    const modelInput = container.querySelector("#llm-openai-model");
    await changeInput(modelInput, "gpt-4o");
    await waitFor(() => tab("llm").textContent.includes("Chưa lưu"));
    expect(tab("reranker").textContent).not.toContain("Chưa lưu");

    await click(tab("reranker"));
    await click(tab("llm"));
    expect(container.querySelector("#llm-openai-model").value).toBe("gpt-4o");

    const undo = [...panel("llm").querySelectorAll("button")].find(
      (item) => item.textContent.trim() === "Hoàn tác"
    );
    await click(undo);
    await waitFor(() => !tab("llm").textContent.includes("Chưa lưu"));
    expect(container.querySelector("#llm-openai-model").value).toBe("gpt-4.1-mini");
  });

  it("bấm gợi ý mô hình thì điền vào ô và bật nút Lưu", async () => {
    await render();

    const chip = [...panel("llm").querySelectorAll(".mdl-chip")].find(
      (item) => item.textContent.trim() === "gpt-4.1"
    );
    await click(chip);

    expect(container.querySelector("#llm-openai-model").value).toBe("gpt-4.1");
    expect(chip.getAttribute("aria-pressed")).toBe("true");
    const save = [...panel("llm").querySelectorAll("button")].find(
      (item) => item.textContent.trim() === "Lưu"
    );
    expect(save.disabled).toBe(false);
  });
});
