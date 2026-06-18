import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { BookOpen, Loader2, Send, Sparkles } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Xin chào, mình có thể trả lời câu hỏi dựa trên sổ tay sinh viên PTIT.",
      sources: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);

  async function sendMessage(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((current) => [...current, { role: "user", content: text, sources: [] }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId, top_k: 4 }),
      });

      if (!response.ok) {
        throw new Error("Không gọi được API chat.");
      }

      const data = await response.json();
      setConversationId(data.conversation_id ?? conversationId);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.answer, sources: data.sources ?? [] },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Có lỗi khi gọi backend. Hãy kiểm tra server FastAPI và dữ liệu đã ingest.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={22} />
          </div>
          <div>
            <h1>PTIT Chatbot</h1>
            <p>RAG assistant</p>
          </div>
        </div>

        <div className="panel">
          <BookOpen size={18} />
          <div>
            <strong>Kho tri thức</strong>
            <span>data/so-tay-sinh-vien-d21.md</span>
          </div>
        </div>
      </aside>

      <section className="chat">
        <div className="messages">
          {messages.map((message, index) => (
            <article key={index} className={`message ${message.role}`}>
              <p>{message.content}</p>
              {message.sources.length > 0 && (
                <div className="sources">
                  {message.sources.map((source, sourceIndex) => (
                    <span key={`${source.source_name}-${source.section_path}-${sourceIndex}`}>
                      [{source.citation_id}] {source.source_name}
                      {(source.section_path || source.heading) &&
                        ` · ${source.section_path || source.heading}`}
                    </span>
                  ))}
                </div>
              )}
            </article>
          ))}
          {loading && (
            <article className="message assistant loading">
              <Loader2 size={18} />
              <span>Đang tìm trong tài liệu...</span>
            </article>
          )}
        </div>

        <form className="composer" onSubmit={sendMessage}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Hỏi về học phí, quy chế, kế hoạch đào tạo..."
          />
          <button type="submit" disabled={loading || !input.trim()} aria-label="Gửi">
            <Send size={20} />
          </button>
        </form>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
