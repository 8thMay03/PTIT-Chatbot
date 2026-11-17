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

function navButton(dialog, label) {
  return [...dialog.querySelectorAll(".ss-nav-item")].find((item) => item.textContent.trim() === label);
}

function navLabels(dialog) {
  return [...dialog.querySelectorAll(".ss-nav-item")].map((item) => item.textContent.trim());
}

function activeSection(dialog) {
  return dialog.querySelector(".ss-section.is-active h3").textContent;
}

function radio(dialog, group, label) {
  return [...dialog.querySelectorAll(`[role="radiogroup"][aria-label="${group}"] [role="radio"]`)].find(
    (item) => item.textContent.trim() === label
  );
}

function switchByTitle(dialog, title) {
  const titleNode = [...dialog.querySelectorAll(".ss-row-title")].find((item) => item.textContent === title);
  return dialog.querySelector(`[role="switch"][aria-labelledby="${titleNode.id}"]`);
}

// Menu tài khoản render qua portal vào document.body.
function menuItem(label) {
  return [...document.querySelectorAll('[role="menuitem"]')].find((item) => item.textContent.trim() === label);
}

function pressEscape() {
  return act(async () => {
    document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  });
}

/**
 * Backend giả cho người dùng đã đăng nhập có một hội thoại (`conv-tk`); hỗ trợ
 * đăng xuất và `DELETE /conversations`.
 */
function signedInBackend() {
  let authenticated = true;
  let loggedOut = false;
  let deletedAll = false;
  const conversation = {
    id: "conv-tk",
    title: "Hội thoại của tài khoản",
    message_count: 2,
    created_at: "2026-10-28T00:00:00Z",
    updated_at: "2026-10-28T00:00:00Z",
  };
  fetch.mockImplementation((url, options = {}) => {
    const path = new URL(String(url), "http://localhost").pathname;
    if (path.endsWith("/auth/logout")) {
      authenticated = false;
      loggedOut = true;
      return jsonResponse({ authenticated: false, user: null, registration_enabled: true });
    }
    if (path.endsWith("/auth/me")) {
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
    if (path.endsWith("/conversations") && options.method === "DELETE") {
      deletedAll = true;
      return jsonResponse({ deleted: 1 });
    }
    if (path.endsWith("/conversations/conv-tk")) {
      return jsonResponse({
        ...conversation,
        messages: [
          { role: "user", content: "Học phí bao nhiêu?" },
          {
            role: "assistant",
            content: "Học phí theo tín chỉ [1].",
            sources: [{ citation_id: 1, locator: "Điều 5", source_name: "Sổ tay sinh viên" }],
          },
        ],
      });
    }
    const empty = !authenticated || deletedAll;
    return jsonResponse(empty ? { total: 0, conversations: [] } : { total: 1, conversations: [conversation] });
  });
  return { loggedOut: () => loggedOut, deletedAll: () => deletedAll };
}

describe("App sinh viên", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
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
    expect(labels).toContain("Cài đặt");
    expect(labels).not.toContain("Giao diện");
    expect(labels).not.toContain("Dataset");
    expect(labels).not.toContain("Settings");
    expect(container.querySelector('a[href^="/admin"]')).toBeNull();

    const urls = fetch.mock.calls.map(([url]) => String(url));
    expect(urls.every((url) => /\/api\/(conversations|auth\/me|health)/.test(url))).toBe(true);
  });

  it("chuyển động: link sang trang khác qua pixel transition, màn chào giữ nguyên chữ", async () => {
    await renderApp();
    await waitFor(() => container.querySelector(".user-login-link"));

    // jsdom không có matchMedia → chuyển động tắt, không gắn listener.
    expect(container.querySelector(".app-shell").classList.contains("motion-ready")).toBe(false);
    expect(container.querySelector(".sidebar-brand").hasAttribute("data-transition")).toBe(true);
    expect(container.querySelector(".user-login-link").hasAttribute("data-transition")).toBe(true);
    // Mọi link nội bộ sang trang khác đều có data-transition (link ngoài/mở tab mới thì không).
    const internal = [...container.querySelectorAll('a[href^="/"]')];
    expect(internal.length).toBeGreaterThan(0);
    expect(internal.every((a) => a.hasAttribute("data-transition"))).toBe(true);
    expect(container.querySelector(".welcome h2").textContent).toBe("Hỏi đáp về quy chế PTIT");
    expect(container.querySelectorAll(".suggestion[data-tilt][data-pulse]")).toHaveLength(4);
    expect(container.querySelector(".composer-glow").getAttribute("aria-hidden")).toBe("true");
  });

  it("mục Cài đặt trên thanh bên mở hộp thoại ở mục Chung; Esc đóng và trả focus", async () => {
    await renderApp();

    const entry = buttonByText(container, "Cài đặt");
    entry.focus();
    await act(async () => {
      entry.click();
    });
    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    expect(dialog.getAttribute("aria-labelledby")).toBe(dialog.querySelector("h2").id);
    expect(dialog.querySelector("h2").textContent).toBe("Cài đặt");
    expect(activeSection(dialog)).toBe("Chung");
    // Khách: không có mục Tài khoản.
    expect(navLabels(dialog)).toEqual(["Chung", "Dữ liệu & lịch sử"]);

    await act(async () => {
      radio(dialog, "Giao diện", "Tối").click();
    });
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(radio(dialog, "Giao diện", "Tối").getAttribute("aria-checked")).toBe("true");
    expect(dialog.querySelector(".ss-saved").textContent).toContain("Đã lưu trên thiết bị này");

    await act(async () => {
      radio(dialog, "Giao diện", "Theo hệ thống").click();
    });
    await pressEscape();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(entry);
  });

  it("đi danh mục bằng nút; nút đóng đóng hộp thoại", async () => {
    await renderApp();
    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'));

    const dataTab = navButton(dialog, "Dữ liệu & lịch sử");
    await act(async () => {
      dataTab.click();
    });
    expect(activeSection(dialog)).toBe("Dữ liệu & lịch sử");
    expect(dataTab.getAttribute("aria-current")).toBe("true");

    await act(async () => {
      dialog.querySelector('button[aria-label="Đóng cài đặt"]').click();
    });
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });

  it("nhóm Chung: cỡ chữ, gửi bằng Enter, giữ mở suy luận áp dụng ngay và giữ sau khi tải lại", async () => {
    await renderApp();
    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    let dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    expect(radio(dialog, "Cỡ chữ", "Vừa").getAttribute("aria-checked")).toBe("true");
    expect(dialog.querySelector(".ss-preview")).not.toBeNull();

    await act(async () => {
      radio(dialog, "Cỡ chữ", "Lớn").click();
    });
    expect(document.documentElement.getAttribute("data-font-scale")).toBe("lg");

    const enterSwitch = switchByTitle(dialog, "Gửi bằng Enter");
    expect(enterSwitch.getAttribute("aria-checked")).toBe("true");
    await act(async () => {
      enterSwitch.click();
    });
    expect(enterSwitch.getAttribute("aria-checked")).toBe("false");
    expect(container.querySelector(".composer-hint").textContent).toContain("Ctrl + Enter để gửi");

    await act(async () => {
      switchByTitle(dialog, "Giữ mở quá trình suy luận").click();
    });
    expect(dialog.querySelector(".ss-saved").textContent).toContain("Đã lưu trên thiết bị này");
    expect(JSON.parse(localStorage.getItem("ptit_chatbot_prefs"))).toEqual({
      version: 1,
      fontScale: "lg",
      enterToSend: false,
      keepReasoningOpen: true,
    });

    // Tải lại trang: mount lại App, tùy chọn còn nguyên.
    act(() => root.unmount());
    expect(document.documentElement.hasAttribute("data-font-scale")).toBe(false);
    root = createRoot(container);
    await renderApp();
    expect(document.documentElement.getAttribute("data-font-scale")).toBe("lg");
    expect(container.querySelector(".composer-hint").textContent).toContain("Ctrl + Enter để gửi");
    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    expect(radio(dialog, "Cỡ chữ", "Lớn").getAttribute("aria-checked")).toBe("true");
    expect(switchByTitle(dialog, "Giữ mở quá trình suy luận").getAttribute("aria-checked")).toBe("true");
  });

  it("segmented đổi lựa chọn bằng phím mũi tên", async () => {
    await renderApp();
    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    const medium = radio(dialog, "Cỡ chữ", "Vừa");
    expect(medium.tabIndex).toBe(0);
    expect(radio(dialog, "Cỡ chữ", "Nhỏ").tabIndex).toBe(-1);

    medium.focus();
    await act(async () => {
      medium.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    });
    expect(radio(dialog, "Cỡ chữ", "Nhỏ").getAttribute("aria-checked")).toBe("true");
    expect(document.activeElement).toBe(radio(dialog, "Cỡ chữ", "Nhỏ"));
    expect(document.documentElement.getAttribute("data-font-scale")).toBe("sm");
  });

  it("#settings/appearance mở hộp thoại Cài đặt ở mục Chung", async () => {
    window.history.replaceState(null, "", "/#settings/appearance");
    await renderApp();

    const dialog = document.querySelector('[role="dialog"]');
    expect(activeSection(dialog)).toBe("Chung");
    expect(dialog.querySelector('[role="radiogroup"][aria-label="Giao diện"]')).not.toBeNull();
    expect(navigateTo).not.toHaveBeenCalled();

    await act(async () => {
      dialog.querySelector('button[aria-label="Đóng cài đặt"]').click();
    });
    // Đóng thì bỏ hash để tải lại trang không mở lại.
    expect(window.location.hash).toBe("");

    await act(async () => {
      window.history.replaceState(null, "", "/#settings/appearance");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(activeSection(document.querySelector('[role="dialog"]'))).toBe("Chung");
  });

  it("hash cũ của màn quản trị chuyển sang /admin tương ứng", async () => {
    await renderApp();

    for (const [hash, target] of [
      ["#documents", "/admin#documents"],
      ["#config", "/admin#settings/retrieval"],
      ["#models", "/admin#settings/models-llm"],
      ["#settings/models", "/admin#settings/models-llm"],
      ["#settings/gate", "/admin#settings/gate"],
    ]) {
      await act(async () => {
        window.history.replaceState(null, "", `/${hash}`);
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      });
      expect(navigateTo).toHaveBeenLastCalledWith(target);
    }
  });

  it("khách thấy Đăng nhập ở chân thanh bên (không ở header) và lời nhắc đóng được", async () => {
    await renderApp();

    const login = await waitFor(() => container.querySelector(".sidebar-footer a.user-login-link"));
    expect(login.textContent.trim()).toBe("Đăng nhập");
    expect(container.querySelector(".chat-header a[href^='/login']")).toBeNull();
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

  it("đã đăng nhập: chip ở chân thanh bên mở menu Cài đặt/Đăng xuất; đăng xuất về khách", async () => {
    const backend = signedInBackend();
    await renderApp();

    const chip = await waitFor(() => container.querySelector(".sidebar-footer button.user-chip"));
    expect(chip.querySelector(".user-name").textContent).toBe("Nguyễn Văn An");
    expect(chip.getAttribute("aria-haspopup")).toBe("menu");
    expect(chip.getAttribute("aria-expanded")).toBe("false");
    expect(container.querySelector(".chat-header .user-chip")).toBeNull();
    expect(container.querySelector(".guest-hint")).toBeNull();
    await waitFor(() => container.textContent.includes("Hội thoại của tài khoản"));

    await act(async () => {
      chip.click();
    });
    const menu = document.querySelector('[role="menu"]');
    expect(chip.getAttribute("aria-expanded")).toBe("true");
    expect([...menu.querySelectorAll('[role="menuitem"]')].map((item) => item.textContent.trim())).toEqual([
      "Cài đặt",
      "Đăng xuất",
    ]);
    expect(document.activeElement).toBe(menu.querySelector('[role="menuitem"]'));

    // Mũi tên đi giữa các mục; Esc đóng menu và trả focus về chip.
    await act(async () => {
      document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    });
    expect(document.activeElement).toBe(menuItem("Đăng xuất"));
    await pressEscape();
    expect(document.querySelector('[role="menu"]')).toBeNull();
    expect(document.activeElement).toBe(chip);

    // Menu nằm trong portal cuối <body>: Tab đóng menu và trả focus về chip.
    await act(async () => {
      chip.click();
    });
    expect(container.contains(document.querySelector('[role="menu"]'))).toBe(false);
    await act(async () => {
      document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    });
    expect(document.querySelector('[role="menu"]')).toBeNull();
    expect(document.activeElement).toBe(chip);

    await act(async () => {
      chip.click();
    });
    await act(async () => {
      menuItem("Đăng xuất").click();
    });

    await waitFor(() => container.querySelector(".sidebar-footer a.user-login-link"));
    await waitFor(() => !container.textContent.includes("Hội thoại của tài khoản"));
    expect(backend.loggedOut()).toBe(true);
  });

  it("menu tài khoản → Cài đặt: mục Tài khoản có tên, email; Đăng xuất đóng hộp thoại", async () => {
    signedInBackend();
    await renderApp();

    const chip = await waitFor(() => container.querySelector(".sidebar-footer button.user-chip"));
    await act(async () => {
      chip.click();
    });
    await act(async () => {
      menuItem("Cài đặt").click();
    });
    let dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    expect(activeSection(dialog)).toBe("Chung");
    expect(navLabels(dialog)).toEqual(["Chung", "Tài khoản", "Dữ liệu & lịch sử"]);

    await act(async () => {
      navButton(dialog, "Tài khoản").click();
    });
    const account = dialog.querySelector('[data-section="account"]');
    expect(account.textContent).toContain("Nguyễn Văn An");
    expect(account.textContent).toContain("an@stu.ptit.edu.vn");

    // Esc trả focus về chip đã mở menu.
    await pressEscape();
    expect(document.activeElement).toBe(chip);

    await act(async () => {
      chip.click();
    });
    await act(async () => {
      menuItem("Cài đặt").click();
    });
    dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    await act(async () => {
      navButton(dialog, "Tài khoản").click();
    });
    await act(async () => {
      buttonByText(dialog.querySelector('[data-section="account"]'), "Đăng xuất").click();
    });

    await waitFor(() => document.querySelector('[role="dialog"]') === null);
    await waitFor(() => container.querySelector(".sidebar-footer a.user-login-link"));
    await waitFor(() => !container.textContent.includes("Hội thoại của tài khoản"));
  });

  it("Dữ liệu & lịch sử: tải lịch sử gom mọi hội thoại thành tệp Markdown", async () => {
    signedInBackend();
    const blobs = [];
    const downloads = [];
    const createObjectURL = vi.fn((blob) => {
      blobs.push(blob);
      return "blob:lich-su";
    });
    // jsdom không có createObjectURL/revokeObjectURL; chỉ vá hai hàm này, giữ `new URL()`.
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      downloads.push(this.download);
    });
    await renderApp();
    await waitFor(() => container.textContent.includes("Hội thoại của tài khoản"));

    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    await act(async () => {
      navButton(dialog, "Dữ liệu & lịch sử").click();
    });
    await act(async () => {
      buttonByText(dialog, "Tải xuống").click();
    });

    await waitFor(() => createObjectURL.mock.calls.length === 1);
    click.mockRestore();
    delete URL.createObjectURL;
    delete URL.revokeObjectURL;
    // Blob của jsdom không có .text().
    const text = await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsText(blobs[0]);
    });
    expect(text).toContain("## Hội thoại của tài khoản");
    expect(text).toContain("### Câu hỏi\n\nHọc phí bao nhiêu?");
    expect(text).toContain("### Trả lời\n\nHọc phí theo tín chỉ [1].");
    expect(text).toContain("- [1] Điều 5 — Sổ tay sinh viên");
    expect(downloads[0]).toMatch(/^ptit-chatbot-lich-su-\d{4}-\d{2}-\d{2}\.md$/);
    const urls = fetch.mock.calls.map(([url]) => String(url));
    expect(urls.some((url) => url.includes("/conversations?limit=200&offset=0"))).toBe(true);
    expect(urls.some((url) => url.endsWith("/conversations/conv-tk"))).toBe(true);
  });

  it("Dữ liệu & lịch sử: xoá toàn bộ cần xác nhận, gọi DELETE rồi làm mới sidebar và chat", async () => {
    const backend = signedInBackend();
    await renderApp();
    const openButton = await waitFor(() => container.querySelector(".conv-open-btn"));
    await act(async () => {
      openButton.click();
    });
    await waitFor(() => container.textContent.includes("Học phí theo tín chỉ"));

    await act(async () => {
      buttonByText(container, "Cài đặt").click();
    });
    const dialog = await waitFor(() => document.querySelector('[role="dialog"]'));
    await act(async () => {
      navButton(dialog, "Dữ liệu & lịch sử").click();
    });
    const danger = dialog.querySelector(".ss-danger");
    expect(danger.querySelector("h4").textContent).toBe("Vùng nguy hiểm");

    await act(async () => {
      buttonByText(danger, "Xoá toàn bộ…").click();
    });
    const confirm = danger.querySelector('[role="alertdialog"]');
    expect(confirm.textContent).toContain("1 hội thoại");
    expect(confirm.textContent).toContain("không thể hoàn tác");
    expect(document.activeElement).toBe(buttonByText(confirm, "Huỷ"));
    expect(backend.deletedAll()).toBe(false);

    await act(async () => {
      buttonByText(confirm, "Xoá vĩnh viễn").click();
    });

    await waitFor(() => backend.deletedAll());
    await waitFor(() => !container.textContent.includes("Hội thoại của tài khoản"));
    await waitFor(() => container.querySelector(".welcome"));
    expect(danger.querySelector('[role="alertdialog"]')).toBeNull();
    await waitFor(() => danger.textContent.includes("Chưa có hội thoại nào."));
    const deleteCall = fetch.mock.calls.find(([, options]) => options?.method === "DELETE");
    expect(new URL(String(deleteCall[0]), "http://localhost").pathname).toBe("/api/conversations");
  });

  it("nút header Cuộc trò chuyện mới bỏ đánh dấu hội thoại đang mở trên sidebar", async () => {
    fetch.mockImplementation((url) => {
      const path = new URL(String(url), "http://localhost").pathname;
      if (path.endsWith("/auth/me")) {
        return jsonResponse({ authenticated: false, user: null, registration_enabled: true });
      }
      if (path.endsWith("/conversations/conv-cu")) {
        return jsonResponse({
          id: "conv-cu",
          messages: [
            { role: "user", content: "Học phí bao nhiêu?" },
            { role: "assistant", content: "Học phí theo tín chỉ.", sources: [] },
          ],
        });
      }
      return jsonResponse({
        total: 1,
        conversations: [
          {
            id: "conv-cu",
            title: "Hội thoại cũ",
            message_count: 2,
            created_at: "2026-11-01T00:00:00Z",
            updated_at: "2026-11-01T00:00:00Z",
          },
        ],
      });
    });
    await renderApp();

    const sidebarNewChat = () => container.querySelector('.sidebar-nav button[aria-label="Cuộc trò chuyện mới"]');
    const headerNewChat = container.querySelector('.chat-header button[aria-label="Cuộc trò chuyện mới"]');
    expect(headerNewChat.title).toBe("Cuộc trò chuyện mới");

    const openButton = await waitFor(() => container.querySelector(".conv-open-btn"));
    await act(async () => {
      openButton.click();
    });
    await waitFor(() => container.textContent.includes("Học phí theo tín chỉ."));
    expect(container.querySelector(".conv-item.active")).not.toBeNull();
    expect(sidebarNewChat().classList.contains("active")).toBe(false);
    expect(container.querySelector(".welcome")).toBeNull();

    await act(async () => {
      headerNewChat.click();
    });

    await waitFor(() => container.querySelector(".welcome"));
    expect(container.querySelector(".conv-item.active")).toBeNull();
    expect(sidebarNewChat().classList.contains("active")).toBe(true);
  });

  it("/chat?q= điền sẵn câu hỏi vào ô nhập, không tự gửi và xoá q khỏi URL", async () => {
    window.history.replaceState(null, "", `/chat?q=${encodeURIComponent("Điều kiện tốt nghiệp?")}`);
    await renderApp();

    const textarea = container.querySelector("textarea");
    expect(textarea.value).toBe("Điều kiện tốt nghiệp?");
    expect(document.activeElement).toBe(textarea);
    expect(window.location.search).toBe("");
    expect(fetch.mock.calls.some(([url]) => String(url).includes("/chat/stream"))).toBe(false);
  });
});
