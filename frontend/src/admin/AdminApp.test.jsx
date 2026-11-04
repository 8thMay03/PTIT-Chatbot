import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { request } from "../api";

const navigateTo = vi.fn();
vi.mock("../lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  navigateTo: (url) => navigateTo(url),
}));

const { default: AdminApp } = await import("./AdminApp");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const EMAIL = "admin@ptit.edu.vn";
const PASSWORD = "mat-khau-dung";

function response(payload, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
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
    guardrails: { scope_enabled: true, min_vector_score: 0.3, min_bm25_score: 2.0 },
    embedding: { provider: "openai", model: "text-embedding-3-small" },
    available_providers: { llm: [], embedding: [], reranker: [] },
  };
}

/**
 * Backend giả: phiên admin là một biến; route quản trị trả 401 khi chưa đăng nhập,
 * đúng như `require_admin` phía server.
 */
function createBackend({ authenticated = false, configured = true } = {}) {
  const state = { authenticated, configured };
  const fetchMock = vi.fn((url, options = {}) => {
    const path = new URL(String(url), "http://localhost").pathname.replace(/^\/api\//, "");
    const method = options.method ?? "GET";

    if (path === "admin/session") {
      return response({
        authenticated: state.authenticated,
        expires_at: state.authenticated ? "2026-10-28T12:00:00+00:00" : null,
        configured: state.configured,
      });
    }
    if (path === "admin/login" && method === "POST") {
      if (!state.configured) {
        return response({ detail: "Chưa cấu hình ADMIN_EMAIL và ADMIN_PASSWORD." }, 503);
      }
      const { email, password } = JSON.parse(options.body);
      state.lastLogin = { email, password };
      if (email !== EMAIL || password !== PASSWORD) {
        return response({ detail: "Email hoặc mật khẩu không đúng." }, 401);
      }
      state.authenticated = true;
      return response({ authenticated: true, expires_at: "2026-10-28T12:00:00+00:00", configured: true });
    }
    if (path === "admin/logout" && method === "POST") {
      state.authenticated = false;
      return response({ authenticated: false, configured: true });
    }
    // Route công khai theo phiên ptit_sid, không bao giờ 401 (như backend thật).
    if (path === "conversations") return response({ total: 0, conversations: [] });
    if (!state.authenticated) return response({ detail: "Cần đăng nhập quản trị." }, 401);
    if (path === "config") return response(baseConfig());
    if (path === "model-profiles") {
      return response({
        profiles: [],
        active: { llm: null, embedding: null, reranker: null },
        embedding_runtime: { provider: "openai", model: "text-embedding-3-small", vector_dim: 1536 },
        env_defaults: {},
        secret_encryption_enabled: true,
      });
    }
    if (path === "documents") return response({ documents: [] });
    if (path === "datasets") return response({ datasets: [] });
    if (path === "parse-jobs") return response({ jobs: [] });
    return response({});
  });
  return { state, fetchMock };
}

async function waitFor(check, timeout = 2000) {
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

async function changeInput(input, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function submitLogin(scope, password, email = EMAIL) {
  const input = await waitFor(() => scope.querySelector('input[type="password"]'));
  await changeInput(scope.querySelector('input[type="email"]'), email);
  await changeInput(input, password);
  await act(async () => {
    scope.querySelector("form.admin-login-form").requestSubmit();
  });
}

function buttonByText(scope, text) {
  return [...scope.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

describe("AdminApp", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    navigateTo.mockReset();
    localStorage.clear();
    window.history.replaceState(null, "", "/admin#settings/config");
    // jsdom không có scrollIntoView; ChatView gọi khi cuộn xuống tin nhắn cuối.
    Element.prototype.scrollIntoView ??= vi.fn();
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
    window.history.replaceState(null, "", "/");
  });

  async function renderAdmin(backend) {
    vi.stubGlobal("fetch", backend.fetchMock);
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <AdminApp />
        </QueryClientProvider>
      );
    });
  }

  it("chưa đăng nhập thì chuyển sang /login chung, giữ màn đang mở trong next", async () => {
    const backend = createBackend();
    await renderAdmin(backend);

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith("/login?next=%2Fadmin%23settings%2Fconfig");
    expect(container.querySelector(".admin-shell")).toBeNull();
    expect(container.querySelector("form")).toBeNull();
    const paths = backend.fetchMock.mock.calls.map(([url]) => String(url));
    expect(paths.every((url) => /\/api\/admin\/session$/.test(url))).toBe(true);
  });

  it("đã đăng nhập vào Settings; đăng xuất xoá cache và chuyển về /login", async () => {
    const backend = createBackend({ authenticated: true });
    await renderAdmin(backend);

    await waitFor(() => container.querySelector(".admin-shell"));
    await waitFor(() => container.querySelector('input[aria-label="Giá trị Temperature"]'));
    expect(navigateTo).not.toHaveBeenCalled();
    const labels = [...container.querySelectorAll(".sidebar-nav-label")].map((item) =>
      item.textContent.trim()
    );
    // Bố cục đầy đủ như trước khi tách app: chat + lịch sử + Dataset + Settings, thêm Đăng xuất.
    expect(labels).toEqual(
      expect.arrayContaining(["Cuộc trò chuyện mới", "Dataset", "Settings", "Đăng xuất"])
    );
    expect(container.querySelector(".admin-shell .chat")).not.toBeNull();
    expect(container.querySelector(".admin-shell .sidebar-chat-area")).not.toBeNull();

    await act(async () => {
      buttonByText(container, "Đăng xuất").click();
    });
    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo.mock.calls[0][0]).toMatch(/^\/login\?next=%2Fadmin/);
    expect(container.querySelector(".admin-shell")).toBeNull();
    expect(backend.state.authenticated).toBe(false);
    expect(queryClient.getQueryData(["config"])).toBeUndefined();
  });

  it("chưa cấu hình ADMIN_EMAIL/ADMIN_PASSWORD thì báo rõ, không chuyển trang", async () => {
    await renderAdmin(createBackend({ configured: false }));

    const notice = await waitFor(() => container.querySelector(".admin-login-alert.is-warning"));
    expect(notice.textContent).toContain("ADMIN_EMAIL");
    expect(notice.textContent).toContain("ADMIN_PASSWORD");
    expect(navigateTo).not.toHaveBeenCalled();
  });

  it("401 giữa chừng hiện lớp phủ đăng nhập mà không mất bản nháp Settings", async () => {
    const backend = createBackend({ authenticated: true });
    await renderAdmin(backend);

    const panel = await waitFor(() => container.querySelector("#settings-panel-config"));
    const temperature = await waitFor(() =>
      container.querySelector('input[aria-label="Giá trị Temperature"]')
    );
    await changeInput(temperature, "0.7");

    // Phiên hết hạn phía server: request quản trị kế tiếp nhận 401.
    backend.state.authenticated = false;
    await act(async () => {
      await request("documents").catch(() => {});
    });

    const dialog = await waitFor(() => container.querySelector('[role="dialog"]'));
    expect(dialog.textContent).toContain("Phiên đăng nhập đã hết hạn");
    expect(container.querySelector(".admin-shell").hasAttribute("inert")).toBe(true);
    // Form Settings vẫn là cùng node DOM, bản nháp còn nguyên.
    expect(container.querySelector("#settings-panel-config")).toBe(panel);
    expect(temperature.value).toBe("0.7");

    await submitLogin(dialog, PASSWORD, "khac@ptit.edu.vn");
    const alert = await waitFor(() => dialog.querySelector('[role="alert"]'));
    expect(alert.textContent).toContain("Email hoặc mật khẩu không đúng.");
    expect(container.querySelector("#settings-panel-config")).toBe(panel);

    await submitLogin(dialog, PASSWORD);
    expect(backend.state.lastLogin).toEqual({ email: EMAIL, password: PASSWORD });
    await waitFor(() => !container.querySelector('[role="dialog"]'));
    expect(container.querySelector(".admin-shell").hasAttribute("inert")).toBe(false);
    expect(container.querySelector("#settings-panel-config")).toBe(panel);
    expect(container.querySelector('input[aria-label="Giá trị Temperature"]').value).toBe("0.7");
  });
});
