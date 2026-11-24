import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, focusManager } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChatView from "./ChatView";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    url: "",
    headers: { get: () => "application/json" },
    json: () => Promise.resolve(payload),
  });
}

/** Stream NDJSON do test đẩy từng event; huỷ theo signal như fetch thật. */
function controllableStream(signal) {
  const encoder = new TextEncoder();
  let controller;
  const body = new ReadableStream({
    start(streamController) {
      controller = streamController;
    },
  });
  signal?.addEventListener("abort", () => {
    try {
      controller.error(new DOMException("The operation was aborted.", "AbortError"));
    } catch {
      // Stream đã đóng.
    }
  });
  return {
    body,
    async send(event) {
      await act(async () => {
        controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    },
    async close() {
      await act(async () => {
        controller.close();
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    },
  };
}

function streamResponse(stream) {
  return Promise.resolve({ ok: true, status: 200, headers: { get: () => "application/x-ndjson" }, body: stream.body });
}

const healthOk = () => jsonResponse({ status: "ok", database: "ok", database_type: "sqlite", embedding: "ready" });

/**
 * Backend giả: `chat/stream` trả stream điều khiển được (hoặc `chatResponse(body)` nếu
 * test đặt), `conversations/<id>` trả `conversations[id]`, `health` trả `health()`.
 * `fetchMock` chỉ ghi các request khác `health`; `healthCalls` đếm riêng.
 */
function createBackend({ chatResponse, conversations = {}, health = healthOk } = {}) {
  const streams = [];
  const chatBodies = [];
  const healthCalls = { count: 0 };
  const fetchMock = vi.fn((url, options = {}) => {
    const path = new URL(String(url), "http://localhost").pathname.replace(/^\/api\//, "");
    if (path === "chat/stream") {
      const body = JSON.parse(options.body);
      chatBodies.push(body);
      if (chatResponse) return chatResponse(body);
      const stream = controllableStream(options.signal);
      streams.push(stream);
      return streamResponse(stream);
    }
    const match = path.match(/^conversations\/(.+)$/);
    if (match && conversations[match[1]]) return jsonResponse(conversations[match[1]]);
    return jsonResponse({ detail: "Không có" }, 404);
  });
  vi.stubGlobal("fetch", (url, options) => {
    if (new URL(String(url), "http://localhost").pathname === "/api/health") {
      healthCalls.count += 1;
      return health();
    }
    return fetchMock(url, options);
  });
  return { fetchMock, streams, chatBodies, healthCalls };
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

function pressEnter(target, init = {}) {
  const event = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true, ...init });
  if (init.keyCode !== undefined) Object.defineProperty(event, "keyCode", { value: init.keyCode });
  act(() => {
    target.dispatchEvent(event);
  });
  return event;
}

function buttonByText(container, text) {
  return [...container.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

function click(element) {
  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

/** Click rồi chờ các cập nhật bất đồng bộ nó gây ra (ví dụ stream bị huỷ) trong act. */
async function clickAndSettle(element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("ChatView", () => {
  let container;
  let root;
  let chatRef;
  let onConversationSaved;
  let queryClient;

  function renderChat(element) {
    act(() => root.render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>));
  }

  function textarea() {
    return container.querySelector("#chat-input");
  }

  function sendButton() {
    return container.querySelector('button[aria-label="Gửi câu hỏi"]');
  }

  function userRows() {
    return [...container.querySelectorAll(".message-row.user .bubble")].map((bubble) => bubble.textContent.trim());
  }

  async function ask(question) {
    typeInto(textarea(), question);
    pressEnter(textarea());
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  beforeEach(() => {
    // jsdom không có scrollIntoView; ChatView gọi khi cuộn xuống tin nhắn cuối.
    Element.prototype.scrollIntoView ??= vi.fn();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    chatRef = React.createRef();
    onConversationSaved = vi.fn();
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // Health lúc mount trả ok; test nào cần backend khác tự gọi createBackend sau đó.
    createBackend();
    renderChat(<ChatView ref={chatRef} onConversationSaved={onConversationSaved} />);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    focusManager.setFocused(undefined);
    vi.unstubAllGlobals();
  });

  describe("bộ gõ IME (AC-01)", () => {
    it("Enter chốt chữ IME hoặc Shift+Enter không gửi; Enter thường mới gửi", async () => {
      const { fetchMock } = createBackend();
      typeInto(textarea(), "học phí");

      const composing = pressEnter(textarea(), { isComposing: true });
      const safari = pressEnter(textarea(), { keyCode: 229 });
      pressEnter(textarea(), { shiftKey: true });

      expect(fetchMock).not.toHaveBeenCalled();
      // Không chặn Enter của IME: bộ gõ cần nó để chốt chữ.
      expect(composing.defaultPrevented).toBe(false);
      expect(safari.defaultPrevented).toBe(false);

      pressEnter(textarea());
      await waitFor(() => fetchMock.mock.calls.length === 1);
    });
  });

  describe("tùy chọn Gửi bằng Enter (student-settings AC-03)", () => {
    function hint() {
      return container.querySelector(".composer-hint").textContent;
    }

    it("mặc định: Enter gửi, dòng gợi ý nói Enter để gửi", () => {
      expect(hint()).toContain("Enter để gửi · Shift + Enter để xuống dòng");
    });

    it("tắt: Enter xuống dòng, Ctrl/Cmd+Enter gửi, Enter chốt chữ IME không gửi", async () => {
      renderChat(<ChatView ref={chatRef} onConversationSaved={onConversationSaved} enterToSend={false} />);
      expect(hint()).toContain("Ctrl + Enter để gửi · Enter để xuống dòng");
      const { fetchMock } = createBackend();
      typeInto(textarea(), "học phí");

      const plain = pressEnter(textarea());
      const composing = pressEnter(textarea(), { ctrlKey: true, isComposing: true });
      expect(fetchMock).not.toHaveBeenCalled();
      // Enter thường để trình duyệt xuống dòng như bình thường.
      expect(plain.defaultPrevented).toBe(false);
      expect(composing.defaultPrevented).toBe(false);

      const submit = pressEnter(textarea(), { ctrlKey: true });
      expect(submit.defaultPrevented).toBe(true);
      await waitFor(() => fetchMock.mock.calls.length === 1);
    });

    it("tắt: Cmd+Enter cũng gửi", async () => {
      renderChat(<ChatView ref={chatRef} onConversationSaved={onConversationSaved} enterToSend={false} />);
      const { fetchMock } = createBackend();
      typeInto(textarea(), "học phí");
      pressEnter(textarea(), { metaKey: true });
      await waitFor(() => fetchMock.mock.calls.length === 1);
    });
  });

  describe("tùy chọn Giữ mở quá trình suy luận (student-settings AC-03)", () => {
    async function streamUntilAnswer() {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "step", step: "retrieve", status: "done", detail: {}, elapsed_ms: 5 });
      await stream.send({ type: "reasoning", content: "Tìm điều khoản học phí" });
      const header = await waitFor(() => container.querySelector(".reasoning-header"));
      expect(header.getAttribute("aria-expanded")).toBe("true");
      await stream.send({ type: "delta", content: "Học phí được tính" });
      return container.querySelector(".reasoning-header");
    }

    it("mặc định: panel tự thu gọn khi câu trả lời bắt đầu stream", async () => {
      const header = await streamUntilAnswer();
      expect(header.getAttribute("aria-expanded")).toBe("false");
    });

    it("bật: panel vẫn mở khi câu trả lời stream", async () => {
      renderChat(<ChatView ref={chatRef} onConversationSaved={onConversationSaved} keepReasoningOpen />);
      const header = await streamUntilAnswer();
      expect(header.getAttribute("aria-expanded")).toBe("true");
    });
  });

  describe("chọn mức suy luận ở khung nhập", () => {
    function trigger() {
      return container.querySelector(".effort-trigger");
    }

    function menuItem(label) {
      return [...document.querySelectorAll('.effort-menu [role="menuitemradio"]')].find(
        (item) => item.querySelector(".effort-menu-label").textContent === label
      );
    }

    it("mặc định Tự động và không gửi reasoning_effort", async () => {
      const { chatBodies } = createBackend();
      expect(trigger().getAttribute("aria-label")).toBe("Mức suy luận: Tự động");

      await ask("Học phí?");
      await waitFor(() => chatBodies.length === 1);
      expect("reasoning_effort" in chatBodies[0]).toBe(false);
    });

    it("chọn Cao trong menu thì câu hỏi sau gửi reasoning_effort=high (app admin giữ trong phiên)", async () => {
      const { chatBodies } = createBackend();
      click(trigger());
      expect(trigger().getAttribute("aria-expanded")).toBe("true");
      // Menu mở thì focus vào mức đang chọn.
      expect(document.activeElement).toBe(menuItem("Tự động"));

      click(menuItem("Cao"));
      expect(document.querySelector(".effort-menu")).toBeNull();
      expect(trigger().getAttribute("aria-label")).toBe("Mức suy luận: Cao");
      expect(document.activeElement).toBe(trigger());

      await ask("Học phí?");
      await waitFor(() => chatBodies.length === 1);
      expect(chatBodies[0].reasoning_effort).toBe("high");
    });

    it("app sinh viên: hiển thị giá trị được truyền và báo thay đổi qua onReasoningEffortChange", () => {
      const onReasoningEffortChange = vi.fn();
      renderChat(
        <ChatView
          ref={chatRef}
          onConversationSaved={onConversationSaved}
          reasoningEffort="low"
          onReasoningEffortChange={onReasoningEffortChange}
        />
      );
      expect(trigger().getAttribute("aria-label")).toBe("Mức suy luận: Thấp");

      click(trigger());
      expect(menuItem("Thấp").getAttribute("aria-checked")).toBe("true");
      click(menuItem("Trung bình"));
      expect(onReasoningEffortChange).toHaveBeenCalledWith("medium");
    });

    it("Esc đóng menu và trả focus về nút", () => {
      click(trigger());
      act(() => {
        menuItem("Tự động").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      });
      expect(document.querySelector(".effort-menu")).toBeNull();
      expect(document.activeElement).toBe(trigger());
    });
  });

  describe("gửi tin", () => {
    it("body không có top_k (AC-03)", async () => {
      const { chatBodies } = createBackend();
      await ask("Học phí?");

      await waitFor(() => chatBodies.length === 1);
      expect(chatBodies[0]).toEqual({ message: "Học phí?", conversation_id: null });
    });

    it("báo hội thoại đã lưu ngay ở event start, trước done (AC-04)", async () => {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);

      await stream.send({ type: "start", conversation_id: "c-1" });
      expect(onConversationSaved).toHaveBeenCalledWith("c-1");
      expect(onConversationSaved).toHaveBeenCalledTimes(1);

      await stream.send({ type: "delta", content: "Trả lời" });
      await stream.send({ type: "done", answer: "Trả lời", sources: [], conversation_id: "c-1", steps: [] });
      await stream.close();
      expect(onConversationSaved).toHaveBeenCalledTimes(2);
    });
  });

  describe("bấm Dừng (AC-04)", () => {
    it("sau delta: giữ phần đã sinh kèm nhãn Đã dừng", async () => {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "delta", content: "Học phí được tính" });

      await clickAndSettle(container.querySelector('button[aria-label="Dừng tạo câu trả lời"]'));

      await waitFor(() => container.querySelector(".message-status"));
      expect(container.querySelector(".message-status").textContent).toBe("Đã dừng");
      expect(container.textContent).toContain("Học phí được tính");
      expect(container.querySelector(".is-error")).toBeNull();
      expect(sendButton()).not.toBeNull();
    });

    it("trước delta: bong bóng Đã dừng trước khi có câu trả lời", async () => {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "step", step: "retrieve", status: "done", detail: {}, elapsed_ms: 5 });

      await clickAndSettle(container.querySelector('button[aria-label="Dừng tạo câu trả lời"]'));

      const bubble = await waitFor(() => container.querySelector(".bubble.is-stopped"));
      expect(bubble.textContent).toBe("Đã dừng trước khi có câu trả lời.");
      expect(container.querySelector(".is-error")).toBeNull();
      expect(buttonByText(container, "Thử lại")).toBeUndefined();
    });
  });

  describe("mở lại hội thoại (AC-04, AC-05)", () => {
    const conversation = {
      id: "c-9",
      title: "Học phí",
      messages: [
        { id: "1", role: "user", content: "Câu 1" },
        { id: "2", role: "assistant", content: "Phần đã sinh", interrupted: true, error: null },
        { id: "3", role: "user", content: "Câu 2" },
        { id: "4", role: "assistant", content: "", interrupted: true, error: null },
        { id: "5", role: "user", content: "Câu 3" },
        { id: "6", role: "assistant", content: "", interrupted: false, error: { type: "retrieval", request_id: "abc123" } },
      ],
    };

    it("hiện nhãn Đã dừng, bong bóng dừng sớm và bubble lỗi có mã tham chiếu", async () => {
      createBackend({ conversations: { "c-9": conversation } });

      await act(async () => {
        await chatRef.current.loadConversation("c-9");
      });

      expect(container.querySelector(".message-status").textContent).toBe("Đã dừng");
      expect(container.textContent).toContain("Phần đã sinh");
      expect(container.querySelector(".bubble.is-stopped").textContent).toBe(
        "Đã dừng trước khi có câu trả lời."
      );
      const error = container.querySelector(".bubble.is-error");
      expect(error.textContent).toContain("Câu trả lời bị gián đoạn");
      expect(error.textContent).toContain("Mã tham chiếu: abc123");
      // Không còn hàng assistant chỉ có avatar + tên.
      const assistantRows = [...container.querySelectorAll(".message-row.assistant")];
      expect(assistantRows.every((row) => row.querySelector(".bubble"))).toBe(true);
    });

    it("Thử lại trên tin lỗi đã lưu gửi lại câu hỏi ngay trước nó, giữ cặp cũ", async () => {
      const { chatBodies } = createBackend({ conversations: { "c-9": conversation } });
      await act(async () => {
        await chatRef.current.loadConversation("c-9");
      });

      click(buttonByText(container, "Thử lại"));

      await waitFor(() => chatBodies.length === 1);
      expect(chatBodies[0]).toEqual({ message: "Câu 3", conversation_id: "c-9" });
      expect(userRows()).toEqual(["Câu 1", "Câu 2", "Câu 3", "Câu 3"]);
    });
  });

  describe("Thử lại sau event error (AC-05, Q-04)", () => {
    it("giữ cặp hỏi–đáp lỗi và thêm cặp mới, khớp lịch sử server", async () => {
      const { streams, chatBodies } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "delta", content: "Học" });
      await stream.send({ type: "error", message: "Mô hình bị gián đoạn. (Mã: r1)", request_id: "r1" });
      await stream.close();

      click(await waitFor(() => buttonByText(container, "Thử lại")));

      await waitFor(() => chatBodies.length === 2);
      expect(chatBodies[1]).toEqual({ message: "Học phí?", conversation_id: "c-1" });
      expect(userRows()).toHaveLength(2);
      expect(container.querySelectorAll(".bubble.is-error")).toHaveLength(1);
    });
  });

  describe("bị từ chối trước khi lưu (AC-06)", () => {
    it.each([
      ["quá hạn mức", "Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau 30 giây."],
      ["đang bận", "Câu trả lời trước vẫn đang được tạo. Vui lòng đợi hoặc bấm Dừng rồi gửi lại."],
    ])("429 %s: trả câu hỏi về ô nhập, không thêm cặp tin, thông điệp của backend", async (_, detail) => {
      createBackend({ chatResponse: () => jsonResponse({ detail }, 429) });
      await ask("Học phí?");

      const alert = await waitFor(() => container.querySelector(".composer-alert"));
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("Chưa gửi được câu hỏi");
      expect(alert.textContent).toContain(detail);
      expect(container.textContent).not.toContain("Vượt quá giới hạn gọi mô hình");
      expect(textarea().value).toBe("Học phí?");
      expect(userRows()).toEqual([]);
      expect(container.querySelector(".is-error")).toBeNull();

      // Sửa ô nhập thì thông báo tự ẩn.
      typeInto(textarea(), "Học phí kỳ này?");
      expect(container.querySelector(".composer-alert")).toBeNull();
    });

    it("422 câu hỏi quá dài: không có tiền tố message:", async () => {
      createBackend({
        chatResponse: () =>
          jsonResponse(
            {
              detail: [
                {
                  type: "message_too_long",
                  loc: ["body", "message"],
                  msg: "Câu hỏi quá dài (tối đa 1500 ký tự).",
                  input: "…",
                },
              ],
            },
            422
          ),
      });
      await ask("Học phí?");

      const alert = await waitFor(() => container.querySelector(".composer-alert"));
      expect(alert.textContent).toContain("Câu hỏi quá dài (tối đa 1500 ký tự).");
      expect(alert.textContent).not.toContain("message:");
      expect(textarea().value).toBe("Học phí?");
      expect(userRows()).toEqual([]);
    });

    it("trong hội thoại đang mở: chỉ gỡ cặp tin tạm, giữ các tin trước", async () => {
      const first = controllableStream();
      let calls = 0;
      createBackend({
        chatResponse: () => {
          calls += 1;
          return calls === 1 ? streamResponse(first) : jsonResponse({ detail: "Bận" }, 429);
        },
      });
      await ask("Câu 1");
      await first.send({ type: "start", conversation_id: "c-1" });
      await first.send({ type: "done", answer: "Đáp 1", sources: [], conversation_id: "c-1", steps: [] });
      await first.close();
      await waitFor(() => sendButton());

      await ask("Câu 2");

      await waitFor(() => container.querySelector(".composer-alert"));
      expect(userRows()).toEqual(["Câu 1"]);
      expect(container.textContent).toContain("Đáp 1");
      expect(textarea().value).toBe("Câu 2");
    });
  });

  describe("nhãn khối nguồn (RAG-22)", () => {
    const SOURCES = [
      { citation_id: 1, source_name: "so-tay.md", heading: "Học phí", section_path: "Sổ tay > Học phí", locator: "Học phí" },
    ];

    async function answerWith(answer, sources) {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "delta", content: answer });
      await stream.send({ type: "done", answer, sources, conversation_id: "c-1", steps: [] });
      await stream.close();
    }

    it("có chip [n] hợp lệ: Nguồn trích dẫn", async () => {
      await answerWith("Học phí thu theo học kỳ [1].", SOURCES);

      const label = await waitFor(() => container.querySelector(".sources-label"));
      expect(label.textContent).toBe("Nguồn trích dẫn");
    });

    it("không có [n] hoặc [n] không có trong sources: Nguồn liên quan", async () => {
      await answerWith("Tài liệu chưa đề cập mức phạt [4].", SOURCES);

      const label = await waitFor(() => container.querySelector(".sources-label"));
      expect(label.textContent).toBe("Nguồn liên quan");
    });

    it("câu từ chối không kèm sources thì không hiện khối nguồn", async () => {
      await answerWith("Chưa tìm thấy thông tin này trong tài liệu.", []);

      await waitFor(() => container.textContent.includes("Chưa tìm thấy thông tin này"));
      expect(container.querySelector(".message-sources")).toBeNull();
    });
  });

  describe("bộ đếm ký tự (AC-06)", () => {
    it("hiện n/2000 khi gần giới hạn; vượt thì khoá nút gửi và Enter", () => {
      const { fetchMock } = createBackend();

      typeInto(textarea(), "a".repeat(1599));
      expect(container.querySelector(".composer-counter")).toBeNull();

      typeInto(textarea(), "a".repeat(1600));
      expect(container.querySelector(".composer-counter").textContent).toBe("1600/2000 ký tự");
      expect(sendButton().disabled).toBe(false);

      typeInto(textarea(), "a".repeat(2001));
      const counter = container.querySelector(".composer-counter");
      expect(counter.classList.contains("is-over")).toBe(true);
      expect(counter.textContent).toContain("2001/2000");
      expect(textarea().getAttribute("aria-describedby")).toBe(counter.id);
      expect(textarea().getAttribute("aria-invalid")).toBe("true");
      expect(sendButton().disabled).toBe(true);

      pressEnter(textarea());
      expect(fetchMock).not.toHaveBeenCalled();
    });
  });

  describe("nút Cuộc trò chuyện mới trên header", () => {
    function headerNewChat() {
      return container.querySelector('.chat-header button[aria-label="Cuộc trò chuyện mới"]');
    }

    it("có onNewChat: gọi handler của trang cha, không tự reset", async () => {
      createBackend({
        conversations: { "c-1": { id: "c-1", messages: [{ role: "user", content: "Câu cũ" }] } },
      });
      const onNewChat = vi.fn();
      renderChat(<ChatView ref={chatRef} onNewChat={onNewChat} />);
      await act(async () => {
        await chatRef.current.loadConversation("c-1");
      });
      expect(userRows()).toEqual(["Câu cũ"]);

      click(headerNewChat());

      expect(onNewChat).toHaveBeenCalledTimes(1);
      expect(userRows()).toEqual(["Câu cũ"]);
    });

    it("không có onNewChat: tự reset về màn chào (AC-04)", async () => {
      createBackend({
        conversations: { "c-1": { id: "c-1", messages: [{ role: "user", content: "Câu cũ" }] } },
      });
      await act(async () => {
        await chatRef.current.loadConversation("c-1");
      });
      expect(container.querySelector(".welcome")).toBeNull();

      click(headerNewChat());

      expect(container.querySelector(".welcome")).not.toBeNull();
      expect(userRows()).toEqual([]);
    });

    it("bị khoá khi đang trả lời (AC-03)", async () => {
      const { streams } = createBackend();
      expect(headerNewChat().title).toBe("Cuộc trò chuyện mới");
      expect(headerNewChat().disabled).toBe(false);

      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      expect(headerNewChat().disabled).toBe(true);

      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "done", answer: "Trả lời", sources: [], conversation_id: "c-1", steps: [] });
      await stream.close();
      await waitFor(() => !headerNewChat().disabled);
    });
  });

  describe("trạng thái máy chủ trên header", () => {
    function headerStatus() {
      return container.querySelector(".chat-header .title");
    }

    function headerDot() {
      return container.querySelector(".chat-header .status-dot");
    }

    /** Cửa sổ được focus lại: TanStack Query kiểm tra lại health ngay. */
    async function refocusWindow() {
      await act(async () => {
        focusManager.setFocused(false);
        focusManager.setFocused(true);
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    it("ok: Sẵn sàng hỗ trợ, chấm xanh, vùng role=status (AC-03, AC-05)", async () => {
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
      expect(headerStatus().getAttribute("role")).toBe("status");
      expect(headerStatus().getAttribute("aria-live")).toBe("polite");
      expect(headerDot().className).toBe("status-dot");
    });

    it("degraded: nhãn hạn chế, chấm cảnh báo (AC-02)", async () => {
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
      createBackend({ health: () => jsonResponse({ status: "degraded", database: "ok", embedding: "unconfigured" }) });

      await refocusWindow();

      await waitFor(() => headerStatus().textContent === "Đang hạn chế, câu trả lời có thể chậm hoặc lỗi");
      expect(headerDot().classList.contains("is-degraded")).toBe(true);
    });

    it.each([
      ["lỗi mạng", () => Promise.reject(new TypeError("Failed to fetch"))],
      ["503", () => jsonResponse({ detail: "Service Unavailable" }, 503)],
    ])("%s khi focus lại: Mất kết nối máy chủ, chấm đỏ; có lại thì về sẵn sàng (AC-01)", async (_, health) => {
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
      createBackend({ health });

      await refocusWindow();

      await waitFor(() => headerStatus().textContent === "Mất kết nối máy chủ");
      expect(headerDot().classList.contains("is-offline")).toBe(true);

      createBackend();
      await refocusWindow();
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
    });

    it("đang stream: Đang trả lời... rồi về trạng thái máy chủ (AC-03)", async () => {
      const { streams } = createBackend();
      await ask("Học phí?");
      const stream = await waitFor(() => streams[0]);
      expect(headerStatus().textContent).toBe("Đang trả lời...");
      expect(headerDot().classList.contains("is-busy")).toBe(true);

      await stream.send({ type: "start", conversation_id: "c-1" });
      await stream.send({ type: "done", answer: "Trả lời", sources: [], conversation_id: "c-1", steps: [] });
      await stream.close();
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
    });

    it("stream lỗi mạng: kiểm tra lại health ngay, header báo mất kết nối (AC-04)", async () => {
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
      const { healthCalls } = createBackend({
        chatResponse: () => Promise.reject(new TypeError("Failed to fetch")),
        health: () => Promise.reject(new TypeError("Failed to fetch")),
      });

      await ask("Học phí?");

      await waitFor(() => healthCalls.count === 1);
      await waitFor(() => headerStatus().textContent === "Mất kết nối máy chủ");
    });

    it("lỗi 4xx của chat không làm kiểm tra lại health", async () => {
      await waitFor(() => headerStatus().textContent === "Sẵn sàng hỗ trợ");
      const { healthCalls } = createBackend({ chatResponse: () => jsonResponse({ detail: "Bận" }, 429) });

      await ask("Học phí?");

      await waitFor(() => container.querySelector(".composer-alert"));
      expect(healthCalls.count).toBe(0);
    });
  });
});
