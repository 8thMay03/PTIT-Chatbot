import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const navigateTo = vi.fn();
vi.mock("./lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  navigateTo: (url) => navigateTo(url),
}));

const { default: App } = await import("./App");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => "application/json" },
    json: () => Promise.resolve(payload),
  });
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

function buttonByText(container, text) {
  return [...container.querySelectorAll("button")].find(
    (item) => item.textContent.trim() === text
  );
}

describe("App sinh viên", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState(null, "", "/");
    navigateTo.mockReset();
    // jsdom không có scrollIntoView; ChatView gọi khi cuộn xuống tin nhắn cuối.
    Element.prototype.scrollIntoView ??= vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        String(url).includes("/auth/me")
          ? jsonResponse({ authenticated: false, user: null, registration_enabled: true })
          : jsonResponse({ total: 0, conversations: [] })
      )
    );
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

  async function renderApp() {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      );
    });
  }

  it("không có lối vào Dataset/Settings, chỉ gọi API công khai", async () => {
    await renderApp();
    await waitFor(() => fetch.mock.calls.length > 0);

    const labels = [...container.querySelectorAll(".sidebar-nav-label")].map((item) =>
      item.textContent.trim()
    );
    expect(labels).toContain("Cuộc trò chuyện mới");
    expect(labels).toContain("Giao diện");
    expect(labels).not.toContain("Dataset");
    expect(labels).not.toContain("Settings");
    expect(container.querySelector('a[href^="/admin"]')).toBeNull();

    const urls = fetch.mock.calls.map(([url]) => String(url));
    expect(urls.every((url) => /\/api\/(conversations|auth\/me)/.test(url))).toBe(true);
  });

  it("nút Giao diện mở bộ chọn chủ đề và đổi được chủ đề", async () => {
    await renderApp();

    await act(async () => {
      buttonByText(container, "Giao diện").click();
    });
    const dialog = await waitFor(() => container.querySelector('[role="dialog"]'));
    expect(dialog.querySelector('[aria-label="Chế độ giao diện"]')).not.toBeNull();

    await act(async () => {
      buttonByText(dialog, "Tối").click();
    });
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(buttonByText(dialog, "Tối").getAttribute("aria-pressed")).toBe("true");

    await act(async () => {
      buttonByText(dialog, "Theo hệ thống").click();
      buttonByText(dialog, "Đóng").click();
    });
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it("#settings/appearance mở bộ chọn giao diện tại chỗ", async () => {
    window.history.replaceState(null, "", "/#settings/appearance");
    await renderApp();

    expect(container.querySelector('[role="dialog"] [aria-label="Chế độ giao diện"]')).not.toBeNull();
    expect(navigateTo).not.toHaveBeenCalled();
  });

  it("hash cũ của màn quản trị chuyển sang /admin tương ứng", async () => {
    await renderApp();

    for (const [hash, target] of [
      ["#documents", "/admin#documents"],
      ["#config", "/admin#settings/config"],
      ["#models", "/admin#settings/models"],
      ["#settings/models", "/admin#settings/models"],
    ]) {
      await act(async () => {
        window.history.replaceState(null, "", `/${hash}`);
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      });
      expect(navigateTo).toHaveBeenLastCalledWith(target);
    }
  });

  it("khách thấy nút Đăng nhập trên header chat và lời nhắc đóng được", async () => {
    await renderApp();

    const login = await waitFor(() => container.querySelector(".chat-header a.user-login-btn"));
    expect(login.textContent.trim()).toBe("Đăng nhập");
    expect(login.getAttribute("href")).toBe("/login");
    expect(container.querySelector("a.sidebar-brand").getAttribute("href")).toBe("/");

    const hint = container.querySelector(".guest-hint");
    expect(hint.textContent).toContain("lưu lịch sử trên mọi thiết bị");
    await act(async () => {
      hint.querySelector("button").click();
    });
    expect(container.querySelector(".guest-hint")).toBeNull();
    expect(localStorage.getItem("ptit_chatbot_guest_hint_dismissed")).toBe("1");
  });

  it("đã đăng nhập: header hiện tên + Đăng xuất; đăng xuất xoá cache hội thoại và về khách", async () => {
    let authenticated = true;
    const accountList = {
      total: 1,
      conversations: [
        {
          id: "conv-tk",
          title: "Hội thoại của tài khoản",
          message_count: 2,
          created_at: "2026-10-28T00:00:00Z",
          updated_at: "2026-10-28T00:00:00Z",
        },
      ],
    };
    fetch.mockImplementation((url, options = {}) => {
      const path = String(url);
      if (path.includes("/auth/logout")) {
        authenticated = false;
        return jsonResponse({ authenticated: false, user: null, registration_enabled: true });
      }
      if (path.includes("/auth/me")) {
        return jsonResponse(
          authenticated
            ? {
                authenticated: true,
                user: { id: "u-1", email: "an@stu.ptit.edu.vn", full_name: "Nguyễn Văn An" },
                registration_enabled: true,
              }
            : { authenticated: false, user: null, registration_enabled: true }
        );
      }
      return jsonResponse(authenticated ? accountList : { total: 0, conversations: [] });
    });
    await renderApp();

    await waitFor(() => container.querySelector(".chat-header .user-name"));
    expect(container.querySelector(".chat-header .user-name").textContent).toBe("Nguyễn Văn An");
    expect(container.querySelector(".guest-hint")).toBeNull();
    await waitFor(() => container.textContent.includes("Hội thoại của tài khoản"));

    const logout = container.querySelector('.chat-header button[title="Đăng xuất"]');
    expect(logout.getAttribute("aria-label")).toBe("Đăng xuất (Nguyễn Văn An)");
    await act(async () => {
      logout.click();
    });

    await waitFor(() => container.querySelector(".chat-header a.user-login-btn"));
    await waitFor(() => !container.textContent.includes("Hội thoại của tài khoản"));
    expect(fetch.mock.calls.some(([url, options]) => String(url).includes("/auth/logout") && options?.method === "POST")).toBe(true);
  });
});
