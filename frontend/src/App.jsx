import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  Clock,
  Cpu,
  Disc,
  Github,
  Home,
  Moon,
  RefreshCw,
  Sliders,
  Sparkles,
  Sun,
  User,
} from "lucide-react";
import ChatView from "./ChatView";
import DocumentsView from "./DocumentsView";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";
import { API_BASE_URL } from "./api";

const SIDEBAR_TIPS = [
  "Hỏi cụ thể một quy định, ví dụ \"điều kiện tốt nghiệp\".",
  "Có thể hỏi tiếp để làm rõ câu trả lời trước đó.",
  "Mỗi câu trả lời kèm nguồn trích từ sổ tay sinh viên.",
  "Tùy chỉnh LLM & Reranker trong màn Cấu hình hoặc Mô hình.",
];

const VALID_VIEWS = ["chat", "documents", "config", "models", "settings"];

function getInitialView() {
  if (typeof window !== "undefined") {
    const hash = window.location.hash.replace(/^#\/?/, "");
    if (VALID_VIEWS.includes(hash)) {
      return hash;
    }
    const saved = localStorage.getItem("ptit_chatbot_view");
    if (VALID_VIEWS.includes(saved)) {
      return saved;
    }
  }
  return "chat";
}

export default function App() {
  const [view, setView] = useState(getInitialView);
  const [docCount, setDocCount] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [lang, setLang] = useState("Tiếng Việt");
  const [theme, setTheme] = useState("light");
  const chatRef = useRef(null);

  // Sync view state to localStorage and URL hash
  useEffect(() => {
    localStorage.setItem("ptit_chatbot_view", view);
    if (window.location.hash.replace(/^#\/?/, "") !== view) {
      window.history.replaceState(null, "", `#${view}`);
    }
  }, [view]);

  // Listen to browser hash changes (Back / Forward)
  useEffect(() => {
    function handleHashChange() {
      const hash = window.location.hash.replace(/^#\/?/, "");
      if (VALID_VIEWS.includes(hash)) {
        setView(hash);
      }
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

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

  const NAV_ITEMS = [
    { key: "documents", label: "Dataset" },
    { key: "chat", label: "Chat" },
    { key: "config", label: "Cấu hình" },
    { key: "models", label: "Mô hình" },
  ];

  return (
    <main className={`app-shell ${view === "chat" ? "view-chat" : "view-full"}`}>
      <header className="app-header">
        <div className="app-header-left">
          <button className="brand header-brand" onClick={() => setView("chat")} type="button">
            <div className="brand-mark">
              <Sparkles size={18} />
            </div>
            <div>
              <h1>PTIT Chatbot</h1>
            </div>
          </button>
        </div>

        {/* Center Pill Navigation Bar */}
        <nav className="top-nav" aria-label="Main Navigation">
          <button
            type="button"
            className="top-nav-home"
            onClick={() => setView("chat")}
            aria-label="Home"
            title="Trang chủ"
          >
            <Home size={15} />
          </button>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`top-nav-item ${
                view === item.key || (item.key === "config" && view === "settings") ? "active" : ""
              }`}
              onClick={() => setView(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Right Header Toolbar */}
        <div className="app-header-right">
          <a
            href="https://discord.com"
            target="_blank"
            rel="noreferrer"
            className="header-icon-link"
            title="Discord"
          >
            <Disc size={16} />
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="header-icon-link"
            title="GitHub"
          >
            <Github size={16} />
          </a>

          <div className="lang-selector" title="Ngôn ngữ">
            <span>{lang}</span>
            <ChevronDown size={13} />
          </div>

          <button
            type="button"
            className={`header-icon-btn ${
              view === "config" || view === "models" || view === "settings" ? "active" : ""
            }`}
            title="Cài đặt hệ thống"
            onClick={() => setView("config")}
          >
            <Sliders size={15} />
          </button>

          <button
            type="button"
            className="header-icon-btn"
            title="Giao diện sáng/tối"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          <button type="button" className="user-avatar-btn" title="Hồ sơ người dùng">
            <div className="avatar-gradient">
              <User size={15} />
            </div>
          </button>
        </div>
      </header>

      {view === "chat" && (
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
                    ? "Quản lý file PDF, MD và TXT"
                    : `${docCount} tài liệu trong chatbot`}
                </span>
              </div>
            </button>
          </div>

          <div className="sidebar-section">
            <span className="sidebar-label">Cấu hình & Mô hình</span>
            <button className="panel panel-button" onClick={() => setView("config")}>
              <div className="panel-icon">
                <Sliders size={18} />
              </div>
              <div>
                <strong>Cấu hình RAG</strong>
                <span>Temperature, Top-K, Threshold</span>
              </div>
            </button>

            <button className="panel panel-button" onClick={() => setView("models")} style={{ marginTop: "8px" }}>
              <div className="panel-icon">
                <Cpu size={18} />
              </div>
              <div>
                <strong>Quản lý Mô hình</strong>
                <span>Chọn LLM, Embedding, Rerank</span>
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
      )}

      <div className="main-pane">
        <ChatView
          ref={chatRef}
          hidden={view !== "chat"}
          onLoadingChange={setChatLoading}
        />
        {view === "documents" && <DocumentsView onChanged={refreshDocCount} />}
        {(view === "config" || view === "settings") && <ConfigView />}
        {view === "models" && <ModelsView />}
      </div>
    </main>
  );
}

