import React, { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Home, RefreshCw, Sparkles } from "lucide-react";
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
    <main className={`app-shell ${view === "documents" ? "view-documents" : "view-chat"}`}>
      <header className="app-header">
        <div className="app-header-left">
          <button className="brand header-brand" onClick={() => setView("chat")} type="button">
            <div className="brand-mark">
              <Sparkles size={18} />
            </div>
            <div>
              <h1>PTIT Chatbot</h1>
              <p>Trợ lý sổ tay sinh viên</p>
            </div>
          </button>
        </div>

        <nav className="top-nav" aria-label="Điều hướng chính">
          <button
            type="button"
            className="top-nav-home"
            onClick={() => setView("chat")}
            aria-label="Trang chủ"
            title="Trang chủ"
          >
            <Home size={16} />
          </button>
          <button
            type="button"
            className={`top-nav-item ${view === "documents" ? "active" : ""}`}
            onClick={() => setView("documents")}
          >
            Dataset
            {docCount != null && <span className="top-nav-count">{docCount}</span>}
          </button>
          <button
            type="button"
            className={`top-nav-item ${view === "chat" ? "active" : ""}`}
            onClick={() => setView("chat")}
          >
            Chat
          </button>
        </nav>

        <div className="app-header-right">
          {view === "chat" && (
            <button className="header-new-chat" onClick={startNewChat} disabled={chatLoading} type="button">
              <RefreshCw size={15} />
              Cuộc trò chuyện mới
            </button>
          )}
        </div>
      </header>

      <aside className="sidebar">
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

        <div className="sidebar-footer">
          Hệ thống <strong>RAG</strong> hybrid retrieval · trả lời kèm citation từ tài liệu chính thức.
        </div>
      </aside>

      <div className="main-pane">
        <ChatView
          ref={chatRef}
          hidden={view !== "chat"}
          onLoadingChange={setChatLoading}
        />
        {view === "documents" && <DocumentsView onChanged={refreshDocCount} />}
      </div>
    </main>
  );
}
