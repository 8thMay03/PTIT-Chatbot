import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { request } from "./api";
import { ToastProvider } from "./components/Toast";

/**
 * Chat và danh sách hội thoại ném lỗi theo kịch bản của từng test; các API khác
 * (health, auth) đi qua `fetch` giả.
 */
const scenario = vi.hoisted(() => ({
  chatError: null,
  chatAfterStart: false,
  listErrors: [],
  conversations: [],
  getError: null,
  listCalls: 0,
}));

vi.mock("./api/chat", () => ({
  async *streamChat() {
    if (scenario.chatAfterStart) yield { type: "start", conversation_id: "c-1" };
    throw scenario.chatError;
  },
}));

vi.mock("./api/conversations", async (importOriginal) => ({
  ...(await importOriginal()),
  list: async () => {
    scenario.listCalls += 1;
    const error = scenario.listErrors.shift();
    if (error) throw error;
    return { total: scenario.conversations.length, conversations: scenario.conversations };
  },
  get: async () => {
    throw scenario.getError;
  },
}));

vi.mock("./lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  navigateTo: () => {},
}));

const { default: App } = await import("./App");
const { default: AdminShell } = await import("./admin/AdminShell");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const TECHNICAL_WORDS = ["FastAPI", "VITE_", "log server", "Backend", "ingest", "màn Mô hình"];
const UNKNOWN_MESSAGE = "Backend stream parse failed: Unexpected token";

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    url: "",
    headers: { get: () => "application/json" },
    json: () => Promise.resolve(payload),
  });
}

/** Proxy không tới được backend: body rỗng, không content-type. */
function emptyResponse(status) {
  return Promise.resolve({
    ok: false,
    status,
    url: "",
    headers: { get: () => null },
    json: () => Promise.reject(new SyntaxError("Unexpected end of JSON input")),
    text: () => Promise.resolve(""),
  });
}

/** Lỗi thật do lớp client tạo (cùng câu chữ người dùng sẽ thấy), không tự dựng chuỗi. */
async function clientError(kind) {
  if (kind === "unknown") return new Error(UNKNOWN_MESSAGE);
  const fetchByKind = {
    network: () => Promise.reject(new TypeError("Failed to fetch")),
    timeout: (_, init) =>
      new Promise((_resolve, reject) => {
        init.signal.addEventListener("abort", () =>
          reject(new DOMException("The operation was aborted.", "AbortError"))
        );
      }),
    404: () => jsonResponse({ detail: "Not Found" }, 404),
    500: () => emptyResponse(500),
    429: () =>
      jsonResponse({ detail: "Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau 30 giây." }, 429),
  };
  vi.stubGlobal("fetch", vi.fn(fetchByKind[kind]));
  try {
    await request("probe", { timeout: kind === "timeout" ? 5 : 0 });
  } catch (error) {
    return error;
  } finally {
    vi.unstubAllGlobals();
  }
  throw new Error(`Không tạo được lỗi ${kind}`);
}

function stubBackend() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const path = new URL(String(url), "http://localhost").pathname;
      if (path === "/api/auth/me") {
        return jsonResponse({ authenticated: false, user: null, registration_enabled: true });
      }
      if (path === "/api/health") {
        return jsonResponse({ status: "ok", database: "ok", database_type: "sqlite", embedding: "ready" });
      }
      return jsonResponse({});
    })
  );
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

function typeInto(textarea, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  act(() => {
    setter.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function ask(container, question) {
  typeInto(container.querySelector("#chat-input"), question);
  await act(async () => {
    container
      .querySelector("#chat-input")
      .dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function click(element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function expectNoTechnicalWords(text) {
  for (const word of TECHNICAL_WORDS) expect(text).not.toContain(word);
}

const KINDS = ["network", "timeout", "404", "500", "429", "unknown"];

describe("câu chữ lỗi theo trang", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    Object.assign(scenario, {
      chatError: null,
      chatAfterStart: false,
      listErrors: [],
      conversations: [],
      getError: null,
      listCalls: 0,
    });
    localStorage.clear();
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

  async function renderStudent() {
    window.history.replaceState(null, "", "/chat");
    stubBackend();
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      );
    });
  }

  async function renderAdmin() {
    window.history.replaceState(null, "", "/admin#chat");
    stubBackend();
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <AdminShell onLogout={() => {}} />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
  }

  /** Thông báo lỗi của khung chat: bubble lỗi hoặc thông báo ở khung nhập. */
  function chatErrorText() {
    const node = container.querySelector(".bubble.is-error, .composer-alert");
    return node?.textContent ?? "";
  }

  describe("trang sinh viên /chat (AC-01, AC-04)", () => {
    it.each(KINDS.flatMap((kind) => [[kind, false], [kind, true]]))(
      "lỗi %s (sau event start: %s): sidebar và khung chat không có chữ kỹ thuật",
      async (kind, afterStart) => {
        const error = await clientError(kind);
        scenario.listErrors = [error, error, error];
        scenario.chatError = error;
        scenario.chatAfterStart = afterStart;
        await renderStudent();

        const sidebarError = await waitFor(() => container.querySelector(".conv-error"));
        expectNoTechnicalWords(sidebarError.textContent);
        expect(sidebarError.textContent.toLowerCase()).toMatch(/thử lại|báo quản trị viên/);

        await ask(container, "Học phí?");
        const text = await waitFor(() => chatErrorText());
        expectNoTechnicalWords(text);
        if (kind === "unknown") expect(text).not.toContain(UNKNOWN_MESSAGE);
        expect(text.toLowerCase()).toMatch(/thử lại|báo quản trị viên/);
        expectNoTechnicalWords(container.textContent);

        const bubble = container.querySelector(".bubble.is-error");
        if (bubble) {
          const expected = kind === "network" || kind === "timeout" ? "lucide-wifi-off" : "lucide-triangle-alert";
          expect(bubble.querySelector(`.chat-error-icon svg.${expected}`)).not.toBeNull();
        }
      }
    );

    it.each(KINDS)("lỗi %s khi mở hội thoại: bubble lỗi không có chữ kỹ thuật", async (kind) => {
      scenario.conversations = [
        { id: "conv-1", title: "Hội thoại cũ", created_at: "2026-11-15T00:00:00Z", updated_at: "2026-11-15T00:00:00Z" },
      ];
      scenario.getError = await clientError(kind);
      // Bubble lỗi mở hội thoại chỉ hiện khi đã có hội thoại đang mở (màn chào che
      // khi chưa có): mở một lượt trước, lượt này lỗi sau event start.
      scenario.chatAfterStart = true;
      scenario.chatError = new Error("");
      await renderStudent();
      await ask(container, "Học phí?");
      await waitFor(() => container.querySelector(".message-row.user"));

      await click(await waitFor(() => container.querySelector(".conv-open-btn")));
      await waitFor(() => !container.querySelector(".message-row.user"));
      const bubble = await waitFor(() => container.querySelector(".bubble.is-error"));
      expectNoTechnicalWords(bubble.textContent);
      if (kind === "unknown") expect(bubble.textContent).not.toContain(UNKNOWN_MESSAGE);
    });

    it("mã tham chiếu trong detail 5xx của backend vẫn hiện cho sinh viên", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() => jsonResponse({ detail: "Hệ thống đang bận, vui lòng thử lại sau. (Mã: ab12cd)" }, 500))
      );
      scenario.chatError = await request("probe", { timeout: 0 }).catch((error) => error);
      vi.unstubAllGlobals();
      scenario.chatAfterStart = true;
      await renderStudent();

      await ask(container, "Học phí?");
      const text = await waitFor(() => chatErrorText());
      expect(text).toContain("Mã: ab12cd");
      expectNoTechnicalWords(text);
    });
  });

  describe("trang quản trị giữ gợi ý kỹ thuật (AC-02)", () => {
    it.each([
      ["network", "Trình duyệt không gọi được API. Kiểm tra kết nối mạng, hoặc xem server FastAPI đã chạy chưa."],
      ["timeout", "Máy chủ có thể đang xử lý lâu hoặc mất kết nối."],
      ["404", "Đường dẫn API không đúng. Kiểm tra biến VITE_API_BASE_URL của frontend."],
      ["500", "Backend trả về lỗi khi xử lý câu hỏi. Kiểm tra log server và cấu hình LLM trong màn Mô hình."],
      ["429", "Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau 30 giây."],
      ["unknown", UNKNOWN_MESSAGE],
    ])("khung chat, lỗi %s: giữ câu chữ hiện tại", async (kind, expected) => {
      scenario.chatError = await clientError(kind);
      await renderAdmin();

      await ask(container, "Học phí?");
      expect(await waitFor(() => chatErrorText())).toContain(expected);
    });

    it("khung chat, lỗi không có thông điệp: giữ câu dự phòng kỹ thuật", async () => {
      scenario.chatError = new Error("");
      scenario.chatAfterStart = true;
      await renderAdmin();

      await ask(container, "Học phí?");
      expect(await waitFor(() => chatErrorText())).toContain(
        "Có lỗi ngoài dự kiến. Kiểm tra server FastAPI và chắc chắn tài liệu đã được ingest."
      );
    });

    it.each([
      ["network", "Không kết nối được máy chủ. Trình duyệt không gọi được API. Kiểm tra kết nối mạng, hoặc xem server FastAPI đã chạy chưa."],
      ["500", "Máy chủ gặp sự cố. Backend trả về lỗi khi xử lý yêu cầu. Kiểm tra log server rồi thử lại."],
      ["unknown", `Không tải được lịch sử hội thoại. ${UNKNOWN_MESSAGE}`],
    ])("sidebar, lỗi %s: giữ câu chữ hiện tại", async (kind, expected) => {
      const error = await clientError(kind);
      scenario.listErrors = [error];
      await renderAdmin();

      const sidebarError = await waitFor(() => container.querySelector(".conv-error .conv-empty"));
      expect(sidebarError.textContent).toBe(expected);
    });
  });

  describe("nút Thử lại ở sidebar (AC-03)", () => {
    it("là nút bàn phím focus được; bấm thì gọi lại query và hiện danh sách", async () => {
      scenario.listErrors = [await clientError("500")];
      scenario.conversations = [
        { id: "conv-1", title: "Học phí kỳ 1", created_at: "2026-11-15T00:00:00Z", updated_at: "2026-11-15T00:00:00Z" },
      ];
      await renderStudent();

      const retry = await waitFor(() => container.querySelector(".conv-error button"));
      expect(retry.textContent.trim()).toBe("Thử lại");
      expect(retry.getAttribute("type")).toBe("button");
      expect(retry.disabled).toBe(false);
      retry.focus();
      expect(document.activeElement).toBe(retry);
      expect(scenario.listCalls).toBe(1);

      await click(retry);

      await waitFor(() => container.querySelector(".conv-open-btn"));
      expect(scenario.listCalls).toBe(2);
      expect(container.querySelector(".conv-error")).toBeNull();
      expect(container.querySelector(".conv-title").textContent).toBe("Học phí kỳ 1");
    });

    it("trang quản trị cũng có nút Thử lại", async () => {
      scenario.listErrors = [await clientError("network")];
      await renderAdmin();

      const retry = await waitFor(() => container.querySelector(".conv-error button"));
      expect(retry.textContent.trim()).toBe("Thử lại");
    });
  });
});
