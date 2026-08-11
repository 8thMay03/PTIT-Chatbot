import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  Copy,
  Files,
  GraduationCap,
  Lightbulb,
  RefreshCw,
  Send,
  Sparkles,
  Square,
} from "lucide-react";
import { API_BASE_URL } from "./api";

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

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdown(text) {
  if (!text) return "";
  const escaped = escapeHtml(text);
  const lines = escaped.split(/\r?\n/);
  const out = [];
  let inList = false;
  let listType = null;

  const closeList = () => {
    if (inList) {
      out.push(`</${listType}>`);
    }
    inList = false;
    listType = null;
  };

  for (let raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      closeList();
      continue;
    }
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    const ulItem = /^\s*[-*]\s+(.*)$/.exec(line);
    const olItem = /^\s*\d+\.\s+(.*)$/.exec(line);

    if (heading) {
      closeList();
      const level = heading[1].length;
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    } else if (ulItem) {
      if (!inList || listType !== "ul") {
        closeList();
        out.push("<ul>");
        inList = true;
        listType = "ul";
      }
      out.push(`<li>${inline(ulItem[1])}</li>`);
    } else if (olItem) {
      if (!inList || listType !== "ol") {
        closeList();
        out.push("<ol>");
        inList = true;
        listType = "ol";
      }
      out.push(`<li>${inline(olItem[1])}</li>`);
    } else {
      closeList();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  closeList();
  return out.join("");
}

function inline(text) {
  let result = text;
  result = result.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');
  result = result.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  result = result.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  result = result.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer">$1</a>'
  );
  return result;
}

function injectCitations(html, sources) {
  if (!sources || sources.length === 0) return html;
  return html.replace(/\[(\d+)\]/g, (match, num) => {
    const id = Number(num);
    const source = sources.find((item) => item.citation_id === id);
    if (!source) return match;
    const meta = encodeURIComponent(
      JSON.stringify({
        id: source.citation_id,
        name: source.source_name,
        section: source.locator || source.section_path || source.heading || "",
      })
    );
    return `<button type="button" class="citation-chip" data-source="${meta}">${num}</button>`;
  });
}

const ChatView = forwardRef(function ChatView({ hidden, onOpenDocuments, onLoadingChange }, ref) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Xin chào 👋 Mình là trợ lý ảo dựa trên **sổ tay sinh viên PTIT**. Hỏi mình về học phí, quy chế, kế hoạch đào tạo hay điều kiện tốt nghiệp nhé!",
      sources: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [highlightedSource, setHighlightedSource] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const messagesRef = useRef(null);
  const textareaRef = useRef(null);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);

  const showWelcome = messages.length <= 1;

  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  function resetConversation() {
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
  }

  useImperativeHandle(ref, () => ({
    reset: resetConversation,
    isLoading: () => loading,
  }));

  function startNewQuestion(text) {
    setMessages((current) => [
      ...current,
      { role: "user", content: text, sources: [] },
      { role: "assistant", content: "", sources: [], streaming: true },
    ]);
    setLoading(true);
  }

  async function sendMessage(event, overrideText) {
    event?.preventDefault();
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    setInput("");
    startNewQuestion(text);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId, top_k: 4 }),
      });

      if (!response.ok) throw new Error("Không gọi được API chat.");
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
          }
        }
      }
    } catch (error) {
      if (error?.name === "AbortError") return;
      setMessages((current) =>
        current.map((message, index) =>
          index === current.length - 1
            ? {
                role: "assistant",
                content: "Có lỗi khi gọi backend. Hãy kiểm tra server FastAPI và dữ liệu đã ingest.",
                sources: [],
                streaming: false,
              }
            : message
        )
      );
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function appendChunk(content) {
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? { ...message, content: message.content + content } : message
      )
    );
  }

  function stopStreaming() {
    abortRef.current?.abort();
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? { ...message, streaming: false } : message
      )
    );
    setLoading(false);
  }

  async function copyMessage(index, content) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1800);
    } catch {
      /* clipboard không khả dụng */
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
    try {
      const data = JSON.parse(decodeURIComponent(chip.dataset.source));
      const root = chip.closest(".bubble-wrap");
      const targets = root ? Array.from(root.querySelectorAll(`[data-citation="${data.id}"]`)) : [];
      const target = targets[0];
      setHighlightedSource(`${root?.dataset.msgIndex ?? ""}-${data.id}`);
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => setHighlightedSource(null), 2000);
    } catch {
      /* bỏ qua chip lỗi */
    }
  }

  return (
    <section className="chat" hidden={hidden} aria-hidden={hidden}>
      <div className="mobile-topbar">
        <div className="brand-mark">
          <Sparkles size={18} />
        </div>
        <div>
          <h1>PTIT Chatbot</h1>
          <p>Trợ lý sổ tay sinh viên</p>
        </div>
        <button
          className="icon-btn mobile-nav-btn"
          onClick={onOpenDocuments}
          aria-label="Quản lý tài liệu"
          title="Quản lý tài liệu"
        >
          <Files size={17} />
        </button>
      </div>

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
            aria-label="Cuộc trò chuyện mới"
            title="Cuộc trò chuyện mới"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      <div className="messages" ref={messagesRef} onClick={onMessageClick}>
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
            const showTypingPlaceholder = message.role === "assistant" && message.streaming && !message.content;
            const html = injectCitations(renderMarkdown(message.content), message.sources);

            return (
              <div className={`message-row ${message.role}`} key={index}>
                <div className={`avatar ${message.role}`}>
                  {message.role === "assistant" ? <Sparkles size={18} /> : "B"}
                </div>
                <div className="bubble-wrap" data-msg-index={index}>
                  <span className="role-name">{message.role === "assistant" ? "PTIT Assistant" : "Bạn"}</span>
                  <div className={`bubble ${showTypingPlaceholder ? "loading" : ""}`}>
                    {showTypingPlaceholder ? (
                      <>
                        <span className="thinking-dots">
                          <span />
                          <span />
                          <span />
                        </span>
                        <span>Đang tìm trong tài liệu...</span>
                      </>
                    ) : (
                      <div className="md" dangerouslySetInnerHTML={{ __html: html }} />
                    )}
                    {message.streaming && !showTypingPlaceholder && <span className="typing-cursor" />}
                  </div>
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
                            className={`source-card ${highlightedSource === `${index}-${source.citation_id}` ? "highlight" : ""}`}
                            key={`${source.source_name}-${source.section_path}-${sourceIndex}`}
                            data-citation={source.citation_id}
                          >
                            <span className="source-badge">{source.citation_id}</span>
                            <div className="source-meta">
                              <div className="source-name">{source.locator || source.heading || "Mục trong tài liệu"}</div>
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

      <div className="composer-shell">
        <form className="composer" onSubmit={sendMessage}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Hỏi về học phí, quy chế, kế hoạch đào tạo..."
            rows={1}
          />
          {loading ? (
            <button type="button" className="send-btn" onClick={stopStreaming} aria-label="Dừng" title="Dừng tạo câu trả lời">
              <Square size={17} />
            </button>
          ) : (
            <button type="submit" className="send-btn" disabled={!input.trim()} aria-label="Gửi" title="Gửi">
              <Send size={18} />
            </button>
          )}
        </form>
        <p className="composer-hint">Enter để gửi · Shift + Enter để xuống dòng · Trả lời có thể chưa hoàn toàn chính xác</p>
      </div>
    </section>
  );
});

export default ChatView;
