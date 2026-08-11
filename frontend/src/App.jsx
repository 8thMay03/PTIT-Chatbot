import React, { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Files, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import ChatView from "./ChatView";
import DocumentsView from "./DocumentsView";
import { API_BASE_URL } from "./api";

const SIDEBAR_TIPS = [
  "Hỏi cụ thể một quy định, ví dụ \"điều kiện tốt nghiệp\".",
  "Có thể hỏi tiếp để làm rõ câu trả lời trước đó.",
  "Mỗi câu trả lời kèm nguồn trích từ sổ tay sinh viên.",
];

export default function App() {
  const [view, setView] = useState("chat");
  const [docCount, setDocCount] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const chatRef = useRef(null);

  const refreshDocCount = useCallback(() => {
    fetch(`${API_BASE_URL}/documents`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => setDocCount(payload.documents?.length ?? 0))
      .catch(() => setDocCount(null));
  }, []);

  useEffect(() => {
    refreshDocCount();
  }, [refreshDocCount, view]);

  function startNewChat() {
    chatRef.current?.reset();
    setView("chat");
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
            <p>Trợ lý sổ tay sinh viên</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className={`nav-item ${view === "chat" ? "active" : ""}`} onClick={() => setView("chat")}>
            <MessageSquare size={16} />
            Trò chuyện
          </button>
          <button className={`nav-item ${view === "documents" ? "active" : ""}`} onClick={() => setView("documents")}>
            <Files size={16} />
            Tài liệu
            {docCount != null && <span className="nav-badge">{docCount}</span>}
          </button>
        </nav>

        <button className="new-chat-btn" onClick={startNewChat} disabled={chatLoading}>
          <RefreshCw size={16} />
          Cuộc trò chuyện mới
        </button>

        <div className="sidebar-section">
          <span className="sidebar-label">Kho tri thức</span>
          <button className="panel panel-button" onClick={() => setView("documents")}>
            <div className="panel-icon">
              <BookOpen size={18} />
            </div>
            <div>
              <strong>Tài liệu đã nạp</strong>
              <span>
                {docCount == null
                  ? "Quản lý file Markdown và TXT"
                  : `${docCount} tài liệu trong chatbot`}
              </span>
            </div>
          </button>
        </div>

        {view === "chat" && (
          <div className="sidebar-section">
            <span className="sidebar-label">Mẹo sử dụng</span>
            <ul className="tip-list">
              {SIDEBAR_TIPS.map((tip, index) => (
                <li key={index}>
                  <span className="tip-dot" />
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="sidebar-footer">
          Hệ thống <strong>RAG</strong> hybrid retrieval · trả lời kèm citation từ tài liệu chính thức.
        </div>
      </aside>

      <div className="main-pane">
        <ChatView
          ref={chatRef}
          hidden={view !== "chat"}
          onOpenDocuments={() => setView("documents")}
          onLoadingChange={setChatLoading}
        />
        {view === "documents" && <DocumentsView onOpenChat={() => setView("chat")} onChanged={refreshDocCount} />}
      </div>
    </main>
  );
}
