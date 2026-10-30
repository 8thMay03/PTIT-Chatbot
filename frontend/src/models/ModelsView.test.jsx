import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ModelsView from "../ModelsView";
import { ToastProvider } from "../components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(payload),
  });
}

function baseConfig() {
  return {
    llm: { provider: "openai", model: "gpt-4.1-mini", has_api_key: true },
    reranker: { enabled: true, provider: "heuristic", model: "cross-encoder/x" },
  };
}

/** Máy chủ giả giữ kho mô hình trong bộ nhớ, theo hợp đồng /api/model-profiles. */
function createFakeServer({ profiles = [], active = {}, runtime = {} } = {}) {
  const state = {
    profiles: [...profiles],
    active: { llm: null, embedding: null, reranker: null, ...active },
    embedding_runtime: {
      provider: "openai",
      model: "text-embedding-3-small",
      profile_id: null,
      vector_dim: 1536,
      restart_required: false,
      load_error: null,
      ...runtime,
    },
    env_defaults: {
      llm: { provider: "openai", model: "gpt-4.1-mini" },
      embedding: { provider: "openai", model: "text-embedding-3-small" },
      reranker: { provider: "heuristic", model: null },
    },
    secret_encryption_enabled: true,
  };
  let nextId = 1;
  const snapshot = () => structuredClone(state);

  const fetchMock = vi.fn((url, options = {}) => {
    const path = new URL(String(url), "http://test").pathname.replace(/^\/api\//, "");
    const method = options.method ?? "GET";
    const body = options.body ? JSON.parse(options.body) : null;
    if (path === "config") return jsonResponse(baseConfig());
    if (path === "model-profiles" && method === "GET") return jsonResponse(snapshot());
    if (path === "model-profiles" && method === "POST") {
      const { api_key: apiKey, kind, ...rest } = body;
      state.profiles.push({ id: `p${nextId++}`, kind, ...rest, has_api_key: Boolean(apiKey) });
      return jsonResponse(snapshot(), 201);
    }
    if (path === "model-profiles/activate") {
      state.active[body.kind] = body.profile_id;
      if (body.kind === "embedding") state.embedding_runtime.restart_required = body.profile_id !== null;
      return jsonResponse(snapshot());
    }
    const match = path.match(/^model-profiles\/(.+)$/);
    if (match && method === "DELETE") {
      state.profiles = state.profiles.filter((profile) => profile.id !== match[1]);
      return jsonResponse(snapshot());
    }
    return jsonResponse({ detail: `Không giả lập ${method} ${path}` }, 500);
  });
  return { state, fetchMock };
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
    const proto = input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(input, value);
    input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
  });
}

function buttonByText(root, text) {
  return [...root.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

function requestsTo(fetchMock, pathPart, method) {
  return fetchMock.mock.calls.filter(
    ([url, options = {}]) => String(url).includes(pathPart) && (options.method ?? "GET") === method
  );
}

describe("ModelsView — kho mô hình ba tab", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
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
    await waitFor(() => container.querySelector('[role="tablist"]'));
  }

  it("có ba tab con và chuyển panel khi chọn tab", async () => {
    const { fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render();

    const tabs = [...container.querySelectorAll('[role="tab"]')];
    expect(tabs.map((tab) => tab.textContent.replace(/\d+$/, "").trim())).toEqual([
      "LLM model",
      "Embedding model",
      "Rerank model",
    ]);
    expect(container.querySelector("#mdl-panel-llm").hidden).toBe(false);
    expect(container.querySelector("#mdl-panel-embedding").hidden).toBe(true);

    await click(tabs[1]);
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
    expect(container.querySelector("#mdl-panel-embedding").hidden).toBe(false);
    expect(container.querySelector("#mdl-panel-llm").hidden).toBe(true);
    expect(localStorage.getItem("ptit_models_tab")).toBe("embedding");
  });

  it("thêm LLM vào kho rồi chọn làm mô hình đang dùng", async () => {
    const { state, fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render();
    const panel = container.querySelector("#mdl-panel-llm");

    await click(buttonByText(panel, "Thêm mô hình"));
    const modelInput = await waitFor(() => panel.querySelector("#mdl-llm-form-model"));
    await changeInput(modelInput, "gpt-4.1");
    await changeInput(panel.querySelector("#mdl-llm-form-key"), "sk-secret-123");
    await click(buttonByText(panel, "Thêm vào kho"));

    await waitFor(() => panel.querySelector(".mdl-profile"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST");
    expect(JSON.parse(createOptions.body)).toEqual({
      kind: "llm",
      name: "gpt-4.1",
      provider: "openai",
      model: "gpt-4.1",
      base_url: null,
      api_key: "sk-secret-123",
    });
    // Form đóng sau khi lưu, khoá không còn trong DOM.
    expect(panel.querySelector("#mdl-llm-form-key")).toBeNull();
    expect(container.innerHTML).not.toContain("sk-secret-123");
    expect(panel.querySelector(".mdl-profile").textContent).toContain("Đã lưu khoá");

    const select = panel.querySelector("#mdl-llm-active");
    expect([...select.options].map((option) => option.textContent)).toEqual([
      "Cấu hình .env · gpt-4.1-mini (OpenAI)",
      "gpt-4.1 — OpenAI · gpt-4.1",
    ]);
    const apply = buttonByText(panel, "Dùng mô hình này");
    expect(apply.disabled).toBe(true);
    await changeInput(select, "p1");
    expect(apply.disabled).toBe(false);
    await click(apply);

    await waitFor(() => panel.querySelector(".mdl-profile.is-active"));
    expect(state.active.llm).toBe("p1");
    const [[, activateOptions]] = requestsTo(fetchMock, "/model-profiles/activate", "POST");
    expect(JSON.parse(activateOptions.body)).toEqual({ kind: "llm", profile_id: "p1" });
    // Không xoá được mô hình đang dùng.
    expect(panel.querySelector('button[aria-label="Xoá gpt-4.1"]').disabled).toBe(true);
  });

  it("xoá mô hình không dùng sau khi xác nhận", async () => {
    const { state, fetchMock } = createFakeServer({
      profiles: [{ id: "r1", kind: "reranker", name: "BGE", provider: "cross-encoder", model: "BAAI/bge-reranker-base" }],
    });
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("ptit_models_tab", "reranker");
    await render();
    const panel = container.querySelector("#mdl-panel-reranker");
    expect(panel.hidden).toBe(false);
    expect(panel.querySelector("#mdl-reranker-active").options[0].textContent).toBe(
      "Heuristic (có sẵn, không cần mô hình)"
    );

    await click(panel.querySelector('button[aria-label="Xoá BGE"]'));
    const confirm = await waitFor(() =>
      [...document.querySelectorAll(".modal button")].find((item) => item.textContent.trim() === "Xoá")
    );
    await click(confirm);

    await waitFor(() => panel.textContent.includes("Chưa có Rerank model nào"));
    expect(state.profiles).toEqual([]);
    expect(requestsTo(fetchMock, "/model-profiles/r1", "DELETE")).toHaveLength(1);
  });

  it("embedding: khoá lựa chọn sai số chiều và báo cần khởi động lại", async () => {
    const { fetchMock } = createFakeServer({
      profiles: [
        { id: "e1", kind: "embedding", name: "Small", provider: "openai", model: "text-embedding-3-small", dimension: 1536 },
        { id: "e2", kind: "embedding", name: "Large", provider: "openai", model: "text-embedding-3-large", dimension: 3072 },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("ptit_models_tab", "embedding");
    await render();
    const panel = container.querySelector("#mdl-panel-embedding");

    const select = panel.querySelector("#mdl-embedding-active");
    const options = Object.fromEntries([...select.options].map((option) => [option.value, option]));
    expect(options.e1.disabled).toBe(false);
    expect(options.e2.disabled).toBe(true);
    expect(panel.textContent).toContain("Khác VECTOR_DIM");

    await changeInput(select, "e1");
    await click(buttonByText(panel, "Dùng mô hình này"));
    await waitFor(() => panel.textContent.includes("khởi động lại backend"));
    expect(panel.querySelector(".mdl-profile.is-active").textContent).toContain("Đã chọn");
  });
});
