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
import { chatApi, conversationsApi, describeError, isAbortError } from "./api";
import MarkdownView, { preloadMarkdownView } from "./components/LazyMarkdownView";
import ReasoningPanel from "./components/ReasoningPanel";

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

/** Trạng thái đọc cho screen reader khi từng bước pipeline hoàn tất. */
const STEP_STATUS_TEXT = {
  guardrail: "Đang kiểm tra câu hỏi...",
  query_rewrite: "Đang chuẩn hóa truy vấn...",
  multi_query: "Đang sinh biến thể truy vấn...",
  retrieve: "Đang tìm kiếm trong tài liệu...",
  rerank: "Đang xếp hạng đoạn văn...",
  generate: "Đang soạn câu trả lời...",
};

/**
 * Ngữ cảnh câu chữ cho màn chat; cách phân loại lỗi nằm trong `api/errors.js`.
 */
const CHAT_ERROR_CONTEXT = {
  notFoundTitle: "Không tìm thấy API chat",
  notFoundDetail: "Đường dẫn API không đúng. Kiểm tra biến VITE_API_BASE_URL của frontend.",
  serverDetail:
    "Backend trả về lỗi khi xử lý câu hỏi. Kiểm tra log server và cấu hình LLM trong màn Mô hình.",
  fallbackTitle: "Không lấy được câu trả lời",
  fallbackDetail:
    "Có lỗi ngoài dự kiến. Kiểm tra server FastAPI và chắc chắn tài liệu đã được ingest.",
};

function describeChatError(error, overrides = {}) {
  return describeError(error, { ...CHAT_ERROR_CONTEXT, ...overrides });
}

// Renderer Markdown là chunk riêng: tải song song ngay khi module chat được nạp.
preloadMarkdownView().catch(() => {});

const ChatView = forwardRef(function ChatView(
  { hidden, onLoadingChange, onConversationSaved, headerActions },
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
  const conversationAbortRef = useRef(null);
  const bottomRef = useRef(null);
  const lastQuestionRef = useRef("");

  // Chỉ hiện màn chào khi chưa có hội thoại nào được mở: một hội thoại cũ chỉ
  // gồm đúng một tin nhắn vẫn là hội thoại thật, không phải trạng thái ban đầu.
  const showWelcome = messages.length <= 1 && !conversationId;

  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  // Huỷ request mở hội thoại nếu ChatView bị gỡ khỏi cây React.
  useEffect(() => () => conversationAbortRef.current?.abort(), []);

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
    conversationAbortRef.current?.abort();
    conversationAbortRef.current = null;
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
      conversationAbortRef.current?.abort();
      const controller = new AbortController();
      conversationAbortRef.current = controller;
      setLiveStatus("Đang mở hội thoại...");
      setMessages([{ role: "assistant", content: "", sources: [], streaming: true }]);
      try {
        const payload = await conversationsApi.get(id, { signal: controller.signal });
        const restored = (payload.messages ?? []).map((message) => ({
          role: message.role,
          content: message.content,
          sources: message.sources ?? [],
          // Reasoning/steps lưu trong metadata: mở lại hội thoại vẫn xem được.
          reasoning: message.reasoning ?? "",
          steps: message.steps ?? [],
          reasoningOpen: false,
        }));
        setMessages(restored.length ? restored : [{ role: "assistant", content: GREETING, sources: [] }]);
        setConversationId(id);
        setAtBottom(true);
        setLiveStatus("Đã mở hội thoại.");
      } catch (error) {
        if (isAbortError(error)) return;
        setMessages([
          {
            role: "assistant",
            content: "",
            sources: [],
            error: describeChatError(error, {
              fallbackTitle: "Không mở được hội thoại",
              fallbackDetail: "Không mở được hội thoại này.",
              notFoundTitle: "Không tìm thấy hội thoại",
              notFoundDetail: "Hội thoại có thể đã bị xóa hoặc chưa được lưu.",
            }),
          },
        ]);
      } finally {
        if (conversationAbortRef.current === controller) {
          conversationAbortRef.current = null;
        }
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
      current.map((message, index) => {
        if (index !== current.length - 1) return message;
        const next = { ...message, content: message.content + content };
        // Phần câu trả lời bắt đầu stream: tự thu gọn panel suy luận đúng một
        // lần để người dùng tập trung vào câu trả lời; vẫn mở lại được.
        if (!next.reasoningAutoCollapsed) {
          next.reasoningOpen = false;
          next.reasoningAutoCollapsed = true;
        }
        return next;
      })
    );
  }

  function appendReasoning(content) {
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1
          ? { ...message, reasoning: (message.reasoning || "") + content }
          : message
      )
    );
  }

  function appendStep(step) {
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? { ...message, steps: [...(message.steps || []), step] } : message
      )
    );
  }

  function toggleReasoning(index) {
    setMessages((current) =>
      current.map((message, i) => (i === index ? { ...message, reasoningOpen: !message.reasoningOpen } : message))
    );
  }

  function failLastMessage(error, describedOverride) {
    const described = describedOverride ?? describeChatError(error);
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1
          ? { ...message, content: "", sources: [], streaming: false, error: described }
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
      {
        role: "assistant",
        content: "",
        sources: [],
        streaming: true,
        steps: [],
        reasoning: "",
        reasoningOpen: true,
      },
    ]);
    setLoading(true);
    setLiveStatus("Đang tìm trong tài liệu...");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const eventData of chatApi.streamChat({
        message: text,
        conversationId,
        topK: 4,
        signal: controller.signal,
      })) {
        if (eventData.type === "start") {
          setConversationId(eventData.conversation_id);
        } else if (eventData.type === "step") {
          appendStep(eventData);
          if (STEP_STATUS_TEXT[eventData.step]) {
            setLiveStatus(STEP_STATUS_TEXT[eventData.step]);
          }
        } else if (eventData.type === "reasoning") {
          appendReasoning(eventData.content);
        } else if (eventData.type === "delta") {
          appendChunk(eventData.content);
        } else if (eventData.type === "error") {
          // LLM lỗi sau khi đã stream một phần: backend không gửi `done` sau
          // event này, nên hiển thị lỗi kèm nút "Thử lại" để gửi lại câu hỏi.
          failLastMessage(new Error(eventData.message || "LLM streaming failed."), {
            title: "Tạo câu trả lời bị gián đoạn",
            detail:
              eventData.message ||
              "Mô hình gặp lỗi giữa chừng khi trả lời. Thử gửi lại câu hỏi.",
          });
        } else if (eventData.type === "done") {
          setConversationId(eventData.conversation_id);
          setMessages((current) =>
            current.map((message, index) =>
              index === current.length - 1
                ? {
                    ...message,
                    content: eventData.answer,
                    sources: eventData.sources ?? [],
                    // Bước generate hoàn tất và reasoning đầy đủ chỉ có ở done.
                    steps: eventData.steps ?? message.steps,
                    reasoning: eventData.reasoning ?? message.reasoning ?? "",
                    streaming: false,
                  }
                : message
            )
          );
          setLiveStatus("Đã có câu trả lời.");
          onConversationSaved?.(eventData.conversation_id);
        }
      }
    } catch (error) {
      if (isAbortError(error)) return;
      failLastMessage(error);
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
          {headerActions}
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
            const hasReasoning = (message.steps?.length ?? 0) > 0 || !!message.reasoning;
            // Placeholder chờ chỉ hiện khi chưa có event step/reasoning nào;
            // sau đó panel suy luận thay chỗ, thông tin hơn ba dấu chấm.
            const showTypingPlaceholder =
              message.role === "assistant" && message.streaming && !message.content && !hasReasoning;

            return (
              <div className={`message-row ${message.role}`} key={index}>
                <div className={`avatar ${message.role}`} aria-hidden="true">
                  {message.role === "assistant" ? <Sparkles size={18} /> : "B"}
                </div>
                <div className="bubble-wrap" data-msg-index={index}>
                  <span className="role-name">
                    {message.role === "assistant" ? "PTIT Assistant" : "Bạn"}
                  </span>

                  {message.role === "assistant" && hasReasoning && (
                    <ReasoningPanel
                      steps={message.steps}
                      reasoning={message.reasoning}
                      streaming={message.streaming}
                      open={message.reasoningOpen ?? !message.streaming}
                      onToggle={() => toggleReasoning(index)}
                    />
                  )}

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
                  ) : showTypingPlaceholder ? (
                    <div className="bubble loading">
                      <span className="thinking-dots" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                      </span>
                      <span>Đang tìm trong tài liệu...</span>
                    </div>
                  ) : message.content ? (
                    <div className="bubble">
                      <MarkdownView
                        className="md"
                        content={message.content}
                        sources={message.sources}
                      />
                      {message.streaming && <span className="typing-cursor" aria-hidden="true" />}
                    </div>
                  ) : null}

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
