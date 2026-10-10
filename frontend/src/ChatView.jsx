import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  ArrowDown,
  BookOpen,
  Check,
  Copy,
  GraduationCap,
  Lightbulb,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
  Square,
  WifiOff,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { renderMarkdownHtml } from "./lib/format";

const SUGGESTIONS = [
  {
    icon: GraduationCap,
    title: "Cảnh báo học tập",
    text: "Khi nào sinh viên bị cảnh báo kết quả học tập?",
  },
  {
    icon: BookOpen,
    title: "Học phí",
    text: "Học phí của sinh viên được quy định như thế nào?",
  },
  {
    icon: Lightbulb,
    title: "Tốt nghiệp",
    text: "Điều kiện xét tốt nghiệp đối với sinh viên là gì?",
  },
  {
    icon: Sparkles,
    title: "Khen thưởng",
    text: "Sinh viên được khen thưởng trong những trường hợp nào?",
  },
];

const GREETING =
  "Xin chào 👋 Mình là trợ lý ảo dựa trên **sổ tay sinh viên PTIT**. " +
  "Hỏi mình về học phí, quy chế, kế hoạch đào tạo hay điều kiện tốt nghiệp nhé!";

/**
 * Phân loại lỗi để báo đúng nguyên nhân.
 *
 * Trước đây mọi lỗi đều hiện chung một câu "Có lỗi khi gọi backend", khiến
 * người dùng không phân biệt được mất mạng với việc kho tài liệu chưa nạp.
 */
function describeError(error, status) {
  if (error instanceof TypeError) {
    return {
      title: "Không kết nối được máy chủ",
      detail:
        "Trình duyệt không gọi được API. Kiểm tra kết nối mạng, hoặc xem server FastAPI đã chạy chưa.",
    };
  }
  if (status === 404) {
    return {
      title: "Không tìm thấy API chat",
      detail: "Đường dẫn API không đúng. Kiểm tra biến VITE_API_BASE_URL của frontend.",
    };
  }
  if (status === 503 || status === 500) {
    return {
      title: "Máy chủ gặp sự cố",
      detail:
        "Backend trả về lỗi khi xử lý câu hỏi. Kiểm tra log server và cấu hình LLM trong màn Mô hình.",
    };
  }
  if (status === 429) {
    return {
      title: "Vượt quá giới hạn gọi mô hình",
      detail: "Nhà cung cấp LLM đang chặn tạm thời. Thử lại sau ít phút.",
    };
  }
  return {
    title: "Không lấy được câu trả lời",
    detail:
      error?.message ||
      "Có lỗi ngoài dự kiến. Kiểm tra server FastAPI và chắc chắn tài liệu đã được ingest.",
  };
}

function injectCitations(html, sources) {
  if (!sources || sources.length === 0) return html;
  return html.replace(/\[(\d+)\]/g, (match, num) => {
    const id = Number(num);
    const source = sources.find((item) => item.citation_id === id);
    if (!source) return match;
    const label = source.locator || source.section_path || source.heading || source.source_name || "";
    return (
      `<button type="button" class="citation-chip" data-citation-id="${id}" ` +
      `aria-label="Xem nguồn trích dẫn số ${id}${label ? `: ${label}` : ""}">${num}</button>`
    );
  });
}

const ChatView = forwardRef(function ChatView(
  { hidden, onLoadingChange, onConversationSaved },
  ref
) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: GREETING, sources: [] },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [highlightedSource, setHighlightedSource] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [atBottom, setAtBottom] = useState(true);
  const [liveStatus, setLiveStatus] = useState("");

  const messagesRef = useRef(null);
  const textareaRef = useRef(null);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const lastQuestionRef = useRef("");

  // Chỉ hiện màn chào khi chưa có hội thoại nào được mở: một hội thoại cũ chỉ
  // gồm đúng một tin nhắn vẫn là hội thoại thật, không phải trạng thái ban đầu.
  const showWelcome = messages.length <= 1 && !conversationId;

  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  // Chỉ tự cuộn khi người dùng đang ở cuối danh sách. Nếu họ đang đọc lại đoạn
  // phía trên, kéo họ xuống giữa chừng là hành vi gây khó chịu.
  useEffect(() => {
    if (atBottom) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
  }, [messages, loading, atBottom]);

  useEffect(() => {
    const node = messagesRef.current;
    if (!node) return undefined;
    function onScroll() {
      const distance = node.scrollHeight - node.scrollTop - node.clientHeight;
      setAtBottom(distance < 80);
    }
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  const resetConversation = useCallback(() => {
    if (loading) return;
    setConversationId(null);
    setMessages([
      {
        role: "assistant",
        content: "Đã bắt đầu cuộc trò chuyện mới. Hỏi mình bất cứ điều gì về sổ tay sinh viên PTIT nhé!",
        sources: [],
      },
    ]);
    setInput("");
    setHighlightedSource(null);
    setAtBottom(true);
  }, [loading]);

  /** Mở lại một hội thoại đã lưu trên máy chủ. */
  const loadConversation = useCallback(
    async (id) => {
      if (!id || loading) return;
      setLiveStatus("Đang mở hội thoại...");
      setMessages([{ role: "assistant", content: "", sources: [], streaming: true }]);
      try {
        const response = await fetch(`${API_BASE_URL}/conversations/${id}`);
        if (!response.ok) throw new Error("Không mở được hội thoại này.");
        const payload = await response.json();
        const restored = (payload.messages ?? []).map((message) => ({
          role: message.role,
          content: message.content,
          sources: message.sources ?? [],
        }));
        setMessages(restored.length ? restored : [{ role: "assistant", content: GREETING, sources: [] }]);
        setConversationId(id);
        setAtBottom(true);
        setLiveStatus("Đã mở hội thoại.");
      } catch (error) {
        setMessages([
          {
            role: "assistant",
            content: "",
            sources: [],
            error: describeError(error, 0),
          },
        ]);
      }
    },
    [loading]
  );

  useImperativeHandle(ref, () => ({
    reset: resetConversation,
    loadConversation,
    isLoading: () => loading,
  }));

  function appendChunk(content) {
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? { ...message, content: message.content + content } : message
      )
    );
  }

  function failLastMessage(error, status) {
    const described = describeError(error, status);
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1
          ? { role: "assistant", content: "", sources: [], streaming: false, error: described }
          : message
      )
    );
    setLiveStatus(`Lỗi: ${described.title}`);
  }

  async function sendMessage(event, overrideText) {
    event?.preventDefault();
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    setInput("");
    lastQuestionRef.current = text;
    setAtBottom(true);
    setMessages((current) => [
      ...current,
      { role: "user", content: text, sources: [] },
      { role: "assistant", content: "", sources: [], streaming: true },
    ]);
    setLoading(true);
    setLiveStatus("Đang tìm trong tài liệu...");

    const controller = new AbortController();
    abortRef.current = controller;
    let status = 0;

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId, top_k: 4 }),
      });
      status = response.status;

      if (!response.ok) throw new Error("Máy chủ trả về lỗi.");
      if (!response.body) throw new Error("Trình duyệt không hỗ trợ streaming.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finished = false;
      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let eventData;
          try {
            eventData = JSON.parse(line);
          } catch {
            continue;
          }
          if (eventData.type === "start") {
            setConversationId(eventData.conversation_id);
          } else if (eventData.type === "delta") {
            appendChunk(eventData.content);
          } else if (eventData.type === "done") {
            setConversationId(eventData.conversation_id);
            setMessages((current) =>
              current.map((message, index) =>
                index === current.length - 1
                  ? {
                      ...message,
                      content: eventData.answer,
                      sources: eventData.sources ?? [],
                      streaming: false,
                    }
                  : message
              )
            );
            setLiveStatus("Đã có câu trả lời.");
            onConversationSaved?.(eventData.conversation_id);
          }
        }
      }
    } catch (error) {
      if (error?.name === "AbortError") return;
      failLastMessage(error, status);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function retryLastQuestion() {
    if (!lastQuestionRef.current || loading) return;
    // Bỏ cặp câu hỏi + câu trả lời lỗi rồi hỏi lại, tránh nhân đôi câu hỏi trong lịch sử.
    setMessages((current) => current.slice(0, -2));
    sendMessage(null, lastQuestionRef.current);
  }

  function stopStreaming() {
    abortRef.current?.abort();
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? { ...message, streaming: false } : message
      )
    );
    setLoading(false);
    setLiveStatus("Đã dừng tạo câu trả lời.");
  }

  async function copyMessage(index, content) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1800);
    } catch {
      /* clipboard không khả dụng (http hoặc bị chặn quyền) */
    }
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(event);
    }
  }

  function onMessageClick(event) {
    const chip = event.target.closest(".citation-chip");
    if (!chip) return;
    const id = chip.dataset.citationId;
    const root = chip.closest(".bubble-wrap");
    const target = root?.querySelector(`[data-citation="${id}"]`);
    setHighlightedSource(`${root?.dataset.msgIndex ?? ""}-${id}`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => setHighlightedSource(null), 2000);
  }

  return (
    <section className="chat" hidden={hidden} aria-hidden={hidden}>
      <header className="chat-header">
        <div className="title">
          <span className="status-dot" />
          <span>{loading ? "Đang trả lời..." : "Sẵn sàng hỗ trợ"}</span>
        </div>
        <div className="header-actions">
          <button
            className="icon-btn"
            onClick={resetConversation}
            disabled={loading}
            aria-label="Bắt đầu cuộc trò chuyện mới"
            title="Cuộc trò chuyện mới"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {/* Trình đọc màn hình cần biết trạng thái mà không cần nhìn vào bong bóng chat */}
      <p className="sr-only" role="status" aria-live="polite">
        {liveStatus}
      </p>

      <div
        className="messages"
        ref={messagesRef}
        onClick={onMessageClick}
        role="log"
        aria-label="Nội dung hội thoại"
        aria-busy={loading}
      >
        {showWelcome ? (
          <div className="welcome">
            <div className="welcome-icon">
              <GraduationCap size={32} />
            </div>
            <h2>Hỏi đáp về quy chế PTIT</h2>
            <p>
              Trợ lý tìm kiếm trong sổ tay sinh viên và trả lời bằng tiếng Việt kèm nguồn trích dẫn. Thử một câu hỏi
              gợi ý hoặc tự nhập câu của bạn.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((suggestion, index) => {
                const Icon = suggestion.icon;
                return (
                  <button
                    key={index}
                    className="suggestion"
                    onClick={(event) => sendMessage(event, suggestion.text)}
                    disabled={loading}
                  >
                    <span className="s-title">
                      <Icon size={16} />
                      {suggestion.title}
                    </span>
                    <span className="s-text">{suggestion.text}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((message, index) => {
            const showTypingPlaceholder =
              message.role === "assistant" && message.streaming && !message.content;
            const html = message.error
              ? ""
              : injectCitations(renderMarkdownHtml(message.content), message.sources);

            return (
              <div className={`message-row ${message.role}`} key={index}>
                <div className={`avatar ${message.role}`} aria-hidden="true">
                  {message.role === "assistant" ? <Sparkles size={18} /> : "B"}
                </div>
                <div className="bubble-wrap" data-msg-index={index}>
                  <span className="role-name">
                    {message.role === "assistant" ? "PTIT Assistant" : "Bạn"}
                  </span>

                  {message.error ? (
                    <div className="bubble is-error" role="alert">
                      <div className="chat-error">
                        <span className="chat-error-icon">
                          <WifiOff size={18} />
                        </span>
                        <div className="chat-error-body">
                          <strong>{message.error.title}</strong>
                          <p>{message.error.detail}</p>
                          <button
                            type="button"
                            className="chat-retry-btn"
                            onClick={retryLastQuestion}
                            disabled={loading}
                          >
                            <RotateCcw size={13} />
                            Thử lại
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className={`bubble ${showTypingPlaceholder ? "loading" : ""}`}>
                      {showTypingPlaceholder ? (
                        <>
                          <span className="thinking-dots" aria-hidden="true">
                            <span />
                            <span />
                            <span />
                          </span>
                          <span>Đang tìm trong tài liệu...</span>
                        </>
                      ) : (
                        <div className="md" dangerouslySetInnerHTML={{ __html: html }} />
                      )}
                      {message.streaming && !showTypingPlaceholder && (
                        <span className="typing-cursor" aria-hidden="true" />
                      )}
                    </div>
                  )}

                  {!message.streaming && message.content && (
                    <div className="bubble-actions">
                      <button
                        className={`copy-btn ${copiedIndex === index ? "copied" : ""}`}
                        onClick={() => copyMessage(index, message.content)}
                      >
                        {copiedIndex === index ? <Check size={13} /> : <Copy size={13} />}
                        {copiedIndex === index ? "Đã chép" : "Sao chép"}
                      </button>
                    </div>
                  )}

                  {message.role === "assistant" && !message.streaming && message.sources?.length > 0 && (
                    <div className="message-sources">
                      <span className="sources-label">
                        <BookOpen size={13} />
                        Nguồn trích dẫn
                      </span>
                      <div className="source-chips">
                        {message.sources.map((source, sourceIndex) => (
                          <article
                            className={`source-card ${
                              highlightedSource === `${index}-${source.citation_id}` ? "highlight" : ""
                            }`}
                            key={`${source.source_name}-${source.section_path}-${sourceIndex}`}
                            data-citation={source.citation_id}
                          >
                            <span className="source-badge">{source.citation_id}</span>
                            <div className="source-meta">
                              <div className="source-name">
                                {source.locator || source.heading || "Mục trong tài liệu"}
                              </div>
                              <div className="source-document">{source.source_name}</div>
                              {source.section_path && source.section_path !== source.locator && (
                                <div className="source-section">{source.section_path}</div>
                              )}
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      {!atBottom && !showWelcome && (
        <button
          type="button"
          className="scroll-bottom-btn"
          onClick={() => {
            setAtBottom(true);
            bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
          }}
          aria-label="Cuộn xuống tin nhắn mới nhất"
          title="Xuống tin nhắn mới nhất"
        >
          <ArrowDown size={16} />
        </button>
      )}

      <div className="composer-shell">
        <form className="composer" onSubmit={sendMessage}>
          <label className="sr-only" htmlFor="chat-input">
            Nhập câu hỏi của bạn
          </label>
          <textarea
            id="chat-input"
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Hỏi về học phí, quy chế, kế hoạch đào tạo..."
            rows={1}
          />
          {loading ? (
            <button
              type="button"
              className="send-btn"
              onClick={stopStreaming}
              aria-label="Dừng tạo câu trả lời"
              title="Dừng tạo câu trả lời"
            >
              <Square size={17} />
            </button>
          ) : (
            <button
              type="submit"
              className="send-btn"
              disabled={!input.trim()}
              aria-label="Gửi câu hỏi"
              title="Gửi"
            >
              <Send size={18} />
            </button>
          )}
        </form>
        <p className="composer-hint">
          Enter để gửi · Shift + Enter để xuống dòng · Trả lời có thể chưa hoàn toàn chính xác
        </p>
      </div>
    </section>
  );
});

export default ChatView;
