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
function createFakeServer({ profiles = [], active = {}, runtime = {}, listModels } = {}) {
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
    if (path === "model-profiles/test-embedding") {
      return jsonResponse({
        success: true,
        message: "Kết nối thành công tới Voyage AI (voyage-3.5).",
        latency_ms: 87,
        sample_output: "Vector 1024 chiều; được đệm 0 tới VECTOR_DIM=1536 khi lưu.",
      });
    }
    if (path === "model-profiles/test-reranker") {
      return jsonResponse({ success: true, message: "Kết nối thành công tới Rerank API.", latency_ms: 42 });
    }
    if (path === "model-profiles/list-models") {
      return jsonResponse(listModels ? listModels(body) : { success: true, message: null, models: [] });
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

describe("ModelsView — kho mô hình theo loại", () => {
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

  async function render(kind = "llm", { onKindSelect } = {}) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <ModelsView kind={kind} onKindSelect={onKindSelect} />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
    await waitFor(() => container.querySelector(`#mdl-panel-${kind} .mdl-row`));
  }

  /** Hàng trong danh sách theo tên hiển thị. */
  function rowByName(panel, name) {
    return [...panel.querySelectorAll(".mdl-row")].find(
      (row) => row.querySelector(".mdl-row-name").textContent === name
    );
  }

  // Hộp thoại thêm/sửa render qua portal vào body.
  const dialog = () => document.body.querySelector(".mdl-dialog");

  it("chỉ mở panel của mục Mô hình đang chọn và dọn khoá tab cũ", async () => {
    const { fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("ptit_models_tab", "embedding");
    await render("reranker");

    expect(container.querySelector('[role="tablist"]')).toBeNull();
    expect(container.querySelector("#mdl-panel-reranker").hidden).toBe(false);
    expect(container.querySelector("#mdl-panel-llm").hidden).toBe(true);
    expect(container.querySelector("#mdl-panel-embedding").hidden).toBe(true);
    expect(localStorage.getItem("ptit_models_tab")).toBeNull();
    // Không còn ô chọn "Mô hình đang dùng" kiểu cũ.
    expect(container.querySelector("select")).toBeNull();
  });

  it("thẻ khâu hiện mô hình đang dùng, trạng thái và đổi loại qua link", async () => {
    const { fetchMock } = createFakeServer({
      profiles: [
        { id: "e1", kind: "embedding", name: "bge-m3", provider: "sentence-transformers", model: "BAAI/bge-m3", dimension: 1536 },
      ],
      active: { embedding: "e1" },
      runtime: { restart_required: true },
    });
    vi.stubGlobal("fetch", fetchMock);
    const onKindSelect = vi.fn();
    await render("llm", { onKindSelect });

    const cards = [...container.querySelectorAll(".mdl-kind")];
    expect(cards.map((card) => card.getAttribute("href"))).toEqual([
      "#settings/models-llm",
      "#settings/models-embedding",
      "#settings/models-reranker",
    ]);
    expect(cards[0].getAttribute("aria-current")).toBe("page");
    expect(cards[1].hasAttribute("aria-current")).toBe(false);
    expect(cards[0].querySelector(".mdl-kind-name").textContent).toBe("Cấu hình máy chủ");
    expect(cards[0].querySelector(".mdl-kind-meta").textContent).toBe("OpenAI · gpt-4.1-mini");
    expect(cards[1].querySelector(".mdl-kind-name").textContent).toBe("bge-m3");
    expect(cards[1].querySelector(".mdl-pill").textContent).toBe("Chờ khởi động lại");
    expect(cards[2].querySelector(".mdl-kind-name").textContent).toBe("Heuristic");
    expect(cards[2].querySelector(".mdl-pill").textContent).toBe("Đang bật");

    await click(cards[2]);
    expect(onKindSelect).toHaveBeenCalledWith("models-reranker");
  });

  it("thêm LLM qua hộp thoại rồi bấm Dùng để chọn, bấm Dùng hàng .env để quay lại", async () => {
    const { state, fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render();
    const panel = container.querySelector("#mdl-panel-llm");
    expect(panel.querySelector(".mdl-row.is-env").getAttribute("aria-current")).toBe("true");

    await click(buttonByText(panel, "Thêm mô hình"));
    const modelInput = await waitFor(() => dialog()?.querySelector("#mdl-llm-form-model"));
    expect(dialog().getAttribute("role")).toBe("dialog");
    expect(document.activeElement).toBe(dialog().querySelector("#mdl-llm-form-name"));
    // Hộp thoại thêm mới không có mô tả phụ: không mô tả đầu hộp thoại, nhà cung cấp hay ô khoá.
    expect(dialog().querySelector(".mdl-dialog-heading p")).toBeNull();
    expect(dialog().querySelector(".mdl-choice-text span")).toBeNull();
    expect(dialog().querySelector("#mdl-llm-form-key-hint")).toBeNull();
    expect(modelInput.hasAttribute("placeholder")).toBe(false);
    expect(dialog().querySelector("#mdl-llm-form-key").hasAttribute("placeholder")).toBe(false);
    // OpenAI dự phòng khoá `.env` nhưng không ghi tên biến; ô khoá chỉ báo "Không bắt buộc".
    expect(dialog().textContent).not.toContain(".env");
    expect(dialog().textContent).toContain("Không bắt buộc");
    await changeInput(modelInput, "gpt-4.1");
    await changeInput(dialog().querySelector("#mdl-llm-form-key"), "sk-secret-123");
    await click(buttonByText(dialog(), "Thêm vào kho"));

    await waitFor(() => rowByName(panel, "gpt-4.1"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST");
    expect(JSON.parse(createOptions.body)).toEqual({
      kind: "llm",
      name: "gpt-4.1",
      provider: "openai",
      model: "gpt-4.1",
      base_url: null,
      api_key: "sk-secret-123",
    });
    // Hộp thoại đóng sau khi lưu, khoá không còn trong DOM.
    expect(dialog()).toBeNull();
    expect(document.body.innerHTML).not.toContain("sk-secret-123");
    expect(rowByName(panel, "gpt-4.1").textContent).toContain("Đã lưu khoá");

    await click(rowByName(panel, "gpt-4.1").querySelector('button[aria-label="Dùng gpt-4.1"]'));
    await waitFor(() => rowByName(panel, "gpt-4.1").classList.contains("is-active"));
    expect(state.active.llm).toBe("p1");
    const [[, activateOptions]] = requestsTo(fetchMock, "/model-profiles/activate", "POST");
    expect(JSON.parse(activateOptions.body)).toEqual({ kind: "llm", profile_id: "p1" });
    // Hàng đang dùng không có nút Dùng và không xoá được.
    expect(rowByName(panel, "gpt-4.1").querySelector(".mdl-use-btn")).toBeNull();
    expect(panel.querySelector('button[aria-label="Xoá gpt-4.1"]').disabled).toBe(true);

    await click(panel.querySelector('button[aria-label="Dùng Cấu hình máy chủ"]'));
    await waitFor(() => panel.querySelector(".mdl-row.is-env.is-active"));
    expect(state.active.llm).toBeNull();
    const activations = requestsTo(fetchMock, "/model-profiles/activate", "POST");
    expect(JSON.parse(activations[1][1].body)).toEqual({ kind: "llm", profile_id: null });
  });

  it("hộp thoại: Esc đóng khi chưa đổi, giữ mở khi đã nhập, Huỷ luôn đóng", async () => {
    const { fetchMock } = createFakeServer({
      profiles: [{ id: "p1", kind: "llm", name: "Mini", provider: "openai", model: "gpt-4.1-mini" }],
    });
    vi.stubGlobal("fetch", fetchMock);
    await render();
    const panel = container.querySelector("#mdl-panel-llm");
    const editButton = panel.querySelector('button[aria-label="Sửa Mini"]');

    // Trình duyệt focus nút khi bấm; jsdom thì không nên focus tay để kiểm tra trả focus.
    editButton.focus();
    await click(editButton);
    expect(dialog().querySelector(".mdl-dialog-heading h3").textContent).toBe("Sửa Mini");
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(dialog()).toBeNull();
    expect(document.activeElement).toBe(editButton);

    await click(editButton);
    await changeInput(dialog().querySelector("#mdl-llm-form-model"), "gpt-4.1");
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    await click(document.body.querySelector(".mdl-dialog-scrim"));
    expect(dialog()).not.toBeNull();
    expect(dialog().textContent).toContain("Có thay đổi chưa lưu");

    await click(buttonByText(dialog(), "Huỷ"));
    expect(dialog()).toBeNull();
  });

  it("reranker: thêm Rerank API có Base URL, khoá tuỳ chọn và kiểm tra kết nối", async () => {
    const { fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render("reranker");
    const panel = container.querySelector("#mdl-panel-reranker");

    await click(buttonByText(panel, "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-reranker-form-model"));
    // Cross-Encoder (mặc định): không có Base URL, khoá, ghi chú hay nút kiểm tra.
    expect(dialog().querySelector("#mdl-reranker-form-base_url")).toBeNull();
    expect(dialog().querySelector("#mdl-reranker-form-key")).toBeNull();
    expect(buttonByText(dialog(), "Kiểm tra kết nối")).toBeUndefined();

    await click(dialog().querySelector('input[type="radio"][value="rerank_api"]'));
    await waitFor(() => dialog().querySelector("#mdl-reranker-form-base_url"));
    expect(dialog().textContent).toContain("Không bắt buộc");
    await changeInput(dialog().querySelector("#mdl-reranker-form-base_url"), "https://api.cohere.com/v2");
    await changeInput(dialog().querySelector("#mdl-reranker-form-model"), "rerank-v3.5");
    await changeInput(dialog().querySelector("#mdl-reranker-form-key"), "rk-secret-456");

    await click(buttonByText(dialog(), "Kiểm tra kết nối"));
    await waitFor(() => dialog().querySelector(".mdl-test-result.is-ok"));
    const [[, testOptions]] = requestsTo(fetchMock, "/model-profiles/test-reranker", "POST");
    expect(JSON.parse(testOptions.body)).toEqual({
      provider: "rerank_api",
      model: "rerank-v3.5",
      base_url: "https://api.cohere.com/v2",
      api_key: "rk-secret-456",
      profile_id: null,
    });
    expect(requestsTo(fetchMock, "/model-profiles/test-llm", "POST")).toHaveLength(0);

    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => rowByName(panel, "rerank-v3.5"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST").filter(([url]) =>
      String(url).endsWith("/model-profiles")
    );
    expect(JSON.parse(createOptions.body)).toEqual({
      kind: "reranker",
      name: "rerank-v3.5",
      provider: "rerank_api",
      base_url: "https://api.cohere.com/v2",
      model: "rerank-v3.5",
      api_key: "rk-secret-456",
    });
    expect(document.body.innerHTML).not.toContain("rk-secret-456");
    expect(rowByName(panel, "rerank-v3.5").textContent).toContain("Rerank API");
  });

  it("reranker: thêm Voyage AI không có Base URL, khoá bắt buộc và kiểm tra kết nối", async () => {
    const { fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render("reranker");
    const panel = container.querySelector("#mdl-panel-reranker");

    await click(buttonByText(panel, "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-reranker-form-model"));
    await click(dialog().querySelector('input[type="radio"][value="voyage"]'));
    await waitFor(() => dialog().querySelector("#mdl-reranker-form-key"));
    expect(dialog().querySelector("#mdl-reranker-form-base_url")).toBeNull();
    expect(dialog().textContent).toContain("Bắt buộc");
    await changeInput(dialog().querySelector("#mdl-reranker-form-model"), "rerank-2.5");

    // Thiếu khoá: không gửi gì, báo lỗi ở ô khoá.
    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => dialog().querySelector("#mdl-reranker-form-key-error"));
    expect(requestsTo(fetchMock, "/model-profiles", "POST")).toHaveLength(0);

    await changeInput(dialog().querySelector("#mdl-reranker-form-key"), "pa-rerank-321");
    await click(buttonByText(dialog(), "Kiểm tra kết nối"));
    await waitFor(() => dialog().querySelector(".mdl-test-result.is-ok"));
    const [[, testOptions]] = requestsTo(fetchMock, "/model-profiles/test-reranker", "POST");
    expect(JSON.parse(testOptions.body)).toEqual({
      provider: "voyage",
      model: "rerank-2.5",
      base_url: null,
      api_key: "pa-rerank-321",
      profile_id: null,
    });

    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => rowByName(panel, "rerank-2.5"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST").filter(([url]) =>
      String(url).endsWith("/model-profiles")
    );
    expect(JSON.parse(createOptions.body)).toEqual({
      kind: "reranker",
      name: "rerank-2.5",
      provider: "voyage",
      model: "rerank-2.5",
      api_key: "pa-rerank-321",
    });
    expect(document.body.innerHTML).not.toContain("pa-rerank-321");
    expect(rowByName(panel, "rerank-2.5").textContent).toContain("Voyage AI");
  });

  it("embedding: thêm Voyage AI với khoá bắt buộc, số chiều tự điền và kiểm tra kết nối", async () => {
    const { fetchMock } = createFakeServer();
    vi.stubGlobal("fetch", fetchMock);
    await render("embedding");
    const panel = container.querySelector("#mdl-panel-embedding");

    await click(buttonByText(panel, "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-embedding-form-model"));
    // Sentence-Transformers chạy cục bộ: không khoá, không kiểm tra kết nối.
    await click(dialog().querySelector('input[type="radio"][value="sentence-transformers"]'));
    await waitFor(() => !dialog().querySelector("#mdl-embedding-form-key"));
    expect(buttonByText(dialog(), "Kiểm tra kết nối")).toBeUndefined();

    await click(dialog().querySelector('input[type="radio"][value="voyage"]'));
    await waitFor(() => dialog().querySelector("#mdl-embedding-form-key"));
    expect(dialog().querySelector("#mdl-embedding-form-base_url")).toBeNull();
    expect(dialog().textContent).toContain("Bắt buộc");
    await changeInput(dialog().querySelector("#mdl-embedding-form-model"), "voyage-3.5");
    expect(dialog().querySelector("#mdl-embedding-form-dimension").value).toBe("1024");

    // Thiếu khoá: không gửi gì, báo lỗi ở ô khoá.
    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => dialog().querySelector("#mdl-embedding-form-key-error"));
    expect(requestsTo(fetchMock, "/model-profiles", "POST")).toHaveLength(0);

    await changeInput(dialog().querySelector("#mdl-embedding-form-key"), "pa-secret-789");
    await click(buttonByText(dialog(), "Kiểm tra kết nối"));
    await waitFor(() => dialog().querySelector(".mdl-test-result.is-ok"));
    const [[, testOptions]] = requestsTo(fetchMock, "/model-profiles/test-embedding", "POST");
    expect(JSON.parse(testOptions.body)).toEqual({
      provider: "voyage",
      model: "voyage-3.5",
      base_url: null,
      dimension: 1024,
      api_key: "pa-secret-789",
      profile_id: null,
    });
    expect(dialog().textContent).toContain("Vector 1024 chiều");

    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => rowByName(panel, "voyage-3.5"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST").filter(([url]) =>
      String(url).endsWith("/model-profiles")
    );
    expect(JSON.parse(createOptions.body)).toEqual({
      kind: "embedding",
      name: "voyage-3.5",
      provider: "voyage",
      model: "voyage-3.5",
      dimension: 1024,
      api_key: "pa-secret-789",
    });
    expect(document.body.innerHTML).not.toContain("pa-secret-789");
    const row = rowByName(panel, "voyage-3.5");
    expect(row.textContent).toContain("Voyage AI · voyage-3.5 · 1024 chiều");
    expect(row.textContent).not.toContain("Vượt VECTOR_DIM");
    expect(panel.querySelector('button[aria-label="Dùng voyage-3.5"]').disabled).toBe(false);
  });

  it("xoá mô hình không dùng sau khi xác nhận", async () => {
    const { state, fetchMock } = createFakeServer({
      profiles: [{ id: "r1", kind: "reranker", name: "BGE", provider: "cross-encoder", model: "BAAI/bge-reranker-base" }],
    });
    vi.stubGlobal("fetch", fetchMock);
    await render("reranker");
    const panel = container.querySelector("#mdl-panel-reranker");
    expect(panel.hidden).toBe(false);
    // Hàng đầu của reranker là Heuristic có sẵn, đang dùng vì chưa chọn mô hình nào.
    const envRow = panel.querySelector(".mdl-row.is-env");
    expect(envRow.querySelector(".mdl-row-name").textContent).toBe("Heuristic");
    expect(envRow.classList.contains("is-active")).toBe(true);

    await click(panel.querySelector('button[aria-label="Xoá BGE"]'));
    const confirm = await waitFor(() =>
      [...document.querySelectorAll(".modal button")].find((item) => item.textContent.trim() === "Xoá")
    );
    await click(confirm);

    await waitFor(() => panel.textContent.includes("Chưa có Mô hình xếp hạng lại (Reranker) nào"));
    expect(state.profiles).toEqual([]);
    expect(requestsTo(fetchMock, "/model-profiles/r1", "DELETE")).toHaveLength(1);
  });

  it("embedding: khoá Dùng khi sai số chiều, hỏi xác nhận rồi báo cần khởi động lại", async () => {
    const { fetchMock } = createFakeServer({
      profiles: [
        { id: "e1", kind: "embedding", name: "Small", provider: "openai", model: "text-embedding-3-small", dimension: 1536 },
        { id: "e2", kind: "embedding", name: "Large", provider: "openai", model: "text-embedding-3-large", dimension: 3072 },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);
    await render("embedding");
    const panel = container.querySelector("#mdl-panel-embedding");

    expect(panel.querySelector('button[aria-label="Dùng Small"]').disabled).toBe(false);
    expect(panel.querySelector('button[aria-label="Dùng Large"]').disabled).toBe(true);
    expect(rowByName(panel, "Large").textContent).toContain("Vượt VECTOR_DIM");

    // Huỷ ở hộp xác nhận thì không gọi API.
    await click(panel.querySelector('button[aria-label="Dùng Small"]'));
    const cancel = await waitFor(() =>
      [...document.querySelectorAll(".modal button")].find((item) => item.textContent.trim() === "Huỷ")
    );
    expect(document.querySelector(".modal").textContent).toContain("Nạp lại toàn bộ");
    await click(cancel);
    expect(requestsTo(fetchMock, "/model-profiles/activate", "POST")).toHaveLength(0);

    await click(panel.querySelector('button[aria-label="Dùng Small"]'));
    const confirm = await waitFor(() =>
      [...document.querySelectorAll(".modal button")].find((item) => item.textContent.trim() === "Chọn mô hình này")
    );
    await click(confirm);
    await waitFor(() => panel.textContent.includes("khởi động lại backend"));
    expect(rowByName(panel, "Small").textContent).toContain("Đã chọn");
    expect(JSON.parse(requestsTo(fetchMock, "/model-profiles/activate", "POST")[0][1].body)).toEqual({
      kind: "embedding",
      profile_id: "e1",
    });
    // Backend vẫn chạy cấu hình .env cho tới khi khởi động lại.
    expect(panel.querySelector(".mdl-row.is-env").textContent).toContain("Đang chạy");
  });

  async function blur(input) {
    await act(async () => {
      input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    });
  }

  it("LLM tương thích OpenAI: rời ô Base URL thì tự tải danh sách, chọn mô hình trong ô chọn rồi lưu", async () => {
    const { fetchMock } = createFakeServer({
      listModels: () => ({ success: true, message: null, models: ["llama3.1:8b", "qwen2.5:7b"] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await render();
    const panel = container.querySelector("#mdl-panel-llm");
    await click(buttonByText(panel, "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-llm-form-model"));
    await click(dialog().querySelector('input[type="radio"][value="openai_compatible"]'));
    const baseUrl = await waitFor(() => dialog().querySelector("#mdl-llm-form-base_url"));

    // Ô trống: rời ô không gọi máy chủ.
    await blur(baseUrl);
    expect(requestsTo(fetchMock, "/model-profiles/list-models", "POST")).toHaveLength(0);

    await changeInput(baseUrl, "http://localhost:11434/v1");
    await blur(baseUrl);
    const select = await waitFor(() => dialog().querySelector("select#mdl-llm-form-model"));
    const [[, listOptions]] = requestsTo(fetchMock, "/model-profiles/list-models", "POST");
    expect(JSON.parse(listOptions.body)).toEqual({
      kind: "llm",
      provider: "openai_compatible",
      base_url: "http://localhost:11434/v1",
      api_key: null,
      profile_id: null,
    });
    expect([...select.options].map((option) => option.value)).toEqual(["", "llama3.1:8b", "qwen2.5:7b"]);

    // Rời ô lần nữa với cùng cấu hình: không tải lại.
    await blur(baseUrl);
    expect(requestsTo(fetchMock, "/model-profiles/list-models", "POST")).toHaveLength(1);

    await changeInput(select, "qwen2.5:7b");
    // Chuyển sang gõ tay vẫn giữ giá trị và gợi ý từ danh sách.
    await click(buttonByText(dialog(), "Nhập tên khác"));
    const input = dialog().querySelector("input#mdl-llm-form-model");
    expect(input.value).toBe("qwen2.5:7b");
    expect([...dialog().querySelectorAll("#mdl-llm-form-model-suggestions option")].map((o) => o.value)).toContain(
      "llama3.1:8b"
    );
    await click(buttonByText(dialog(), "Chọn trong danh sách (2)"));
    expect(dialog().querySelector("select#mdl-llm-form-model").value).toBe("qwen2.5:7b");

    await click(buttonByText(dialog(), "Thêm vào kho"));
    await waitFor(() => rowByName(panel, "qwen2.5:7b"));
    const [[, createOptions]] = requestsTo(fetchMock, "/model-profiles", "POST").filter(([url]) =>
      String(url).endsWith("/model-profiles")
    );
    expect(JSON.parse(createOptions.body)).toMatchObject({ provider: "openai_compatible", model: "qwen2.5:7b" });
  });

  it("đổi Base URL thì ẩn danh sách cũ; lỗi từ nhà cung cấp hiện cạnh ô và vẫn gõ tay được", async () => {
    const { fetchMock } = createFakeServer({
      listModels: (body) =>
        body.base_url === "http://localhost:8000/v1"
          ? { success: false, message: "HTTP 401. Kiểm tra API key.", models: [] }
          : { success: true, message: null, models: ["qwen2.5:7b"] },
    });
    vi.stubGlobal("fetch", fetchMock);
    await render();
    await click(buttonByText(container.querySelector("#mdl-panel-llm"), "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-llm-form-model"));
    await click(dialog().querySelector('input[type="radio"][value="openai_compatible"]'));
    const baseUrl = await waitFor(() => dialog().querySelector("#mdl-llm-form-base_url"));

    // Bấm tay khi chưa có Base URL: báo thiếu, không gọi máy chủ.
    await click(buttonByText(dialog(), "Tải danh sách"));
    expect(dialog().textContent).toContain("Nhập Base URL trước.");
    expect(requestsTo(fetchMock, "/model-profiles/list-models", "POST")).toHaveLength(0);

    await changeInput(baseUrl, "http://localhost:11434/v1");
    await click(buttonByText(dialog(), "Tải danh sách"));
    // Máy chủ chỉ có một mô hình: điền luôn vào ô đang trống.
    await waitFor(() => dialog().querySelector("select#mdl-llm-form-model")?.value === "qwen2.5:7b");

    await changeInput(baseUrl, "http://localhost:8000/v1");
    expect(dialog().querySelector("select#mdl-llm-form-model")).toBeNull();
    expect(dialog().querySelector("input#mdl-llm-form-model").value).toBe("qwen2.5:7b");

    await click(buttonByText(dialog(), "Tải danh sách"));
    await waitFor(() => dialog().querySelector("#mdl-llm-form-model-list-status[role=alert]"));
    expect(dialog().textContent).toContain("Không tải được danh sách: HTTP 401. Kiểm tra API key.");
    expect(dialog().querySelector("input#mdl-llm-form-model")).not.toBeNull();
  });

  it("sửa profile: tải danh sách bằng khoá đã lưu; khoá bắt buộc thì báo thiếu khoá; Azure không có nút tải", async () => {
    const { fetchMock } = createFakeServer({
      profiles: [
        { id: "r1", kind: "reranker", name: "Cohere", provider: "cohere", model: "rerank-v3.5", has_api_key: true },
      ],
      listModels: () => ({ success: true, message: null, models: ["rerank-v3.5", "rerank-v4.0-pro"] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await render("reranker");
    const panel = container.querySelector("#mdl-panel-reranker");
    await click(panel.querySelector('button[aria-label="Sửa Cohere"]'));
    await waitFor(() => dialog()?.querySelector("#mdl-reranker-form-model"));

    await click(buttonByText(dialog(), "Tải danh sách"));
    const select = await waitFor(() => dialog().querySelector("select#mdl-reranker-form-model"));
    expect(select.value).toBe("rerank-v3.5");
    const [[, listOptions]] = requestsTo(fetchMock, "/model-profiles/list-models", "POST");
    expect(JSON.parse(listOptions.body)).toEqual({
      kind: "reranker",
      provider: "cohere",
      base_url: null,
      api_key: null,
      profile_id: "r1",
    });

    // Đổi sang Pinecone (khoá Cohere không dùng được): thiếu khoá, không gọi máy chủ.
    await click(dialog().querySelector('input[type="radio"][value="pinecone"]'));
    await click(buttonByText(dialog(), "Tải danh sách"));
    expect(dialog().textContent).toContain("Nhập API key trước.");
    expect(requestsTo(fetchMock, "/model-profiles/list-models", "POST")).toHaveLength(1);

    // Cross-Encoder chạy cục bộ: không có nút tải.
    await click(dialog().querySelector('input[type="radio"][value="cross-encoder"]'));
    expect(buttonByText(dialog(), "Tải danh sách")).toBeUndefined();
    await click(buttonByText(dialog(), "Huỷ"));

    await render("llm");
    await click(buttonByText(container.querySelector("#mdl-panel-llm"), "Thêm mô hình"));
    await waitFor(() => dialog()?.querySelector("#mdl-llm-form-model"));
    expect(buttonByText(dialog(), "Tải danh sách")).not.toBeUndefined();
    await click(dialog().querySelector('input[type="radio"][value="azure"]'));
    expect(buttonByText(dialog(), "Tải danh sách")).toBeUndefined();
    // Azure: không placeholder, không gợi ý dưới ô.
    for (const name of ["endpoint", "deployment_name", "api_version", "key"]) {
      expect(dialog().querySelector(`#mdl-llm-form-${name}`).hasAttribute("placeholder")).toBe(false);
    }
    expect(dialog().querySelector(".mdl-field-hint")).toBeNull();
  });
});
