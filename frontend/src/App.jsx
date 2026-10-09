import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Github,
  Home,
  Menu,
  Monitor,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Sliders,
  Sparkles,
  Sun,
} from "lucide-react";
import ChatView from "./ChatView";
import DatasetView from "./DatasetView";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";
import ConversationList from "./components/ConversationList";
import { ToastProvider } from "./components/Toast";
import { useTheme } from "./lib/theme";
import { API_BASE_URL } from "./api";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

const SIDEBAR_TIPS = [
  "Hỏi cụ thể một quy định, ví dụ \"điều kiện tốt nghiệp\".",
  "Có thể hỏi tiếp để làm rõ câu trả lời trước đó.",
  "Mỗi câu trả lời kèm nguồn trích từ sổ tay sinh viên.",
  "Tùy chỉnh LLM & Reranker trong màn Cấu hình hoặc Mô hình.",
];

const VALID_VIEWS = ["chat", "documents", "config", "models", "settings"];

const NAV_ITEMS = [
  { key: "documents", label: "Dataset" },
  { key: "chat", label: "Chat" },
  { key: "config", label: "Cấu hình" },
  { key: "models", label: "Mô hình" },
];

const THEME_LABELS = {
  light: "Đang dùng giao diện sáng. Chuyển sang tối.",
  dark: "Đang dùng giao diện tối. Chuyển sang sáng.",
};

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
  const [chatLoading, setChatLoading] = useState(false);
  const [desktopSidebarCollapsed, setDesktopSidebarCollapsed] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ptit_chatbot_sidebar_collapsed") === "true";
    }
    return false;
  });
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth <= 900;
    }
    return false;
  });
  const [activeConversationId, setActiveConversationId] = useState(null);
  // Tăng lên mỗi khi một lượt hỏi đáp kết thúc, để danh sách hội thoại tải lại.
  const [conversationsToken, setConversationsToken] = useState(0);
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  const chatRef = useRef(null);

  // Theo dõi kích thước màn hình
  useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth <= 900);
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isSidebarOpen = isMobile ? mobileSidebarOpen : !desktopSidebarCollapsed;

  const toggleSidebar = useCallback(() => {
    if (window.innerWidth <= 900) {
      setMobileSidebarOpen((open) => !open);
    } else {
      setDesktopSidebarCollapsed((collapsed) => {
        const next = !collapsed;
        localStorage.setItem("ptit_chatbot_sidebar_collapsed", String(next));
        return next;
      });
    }
  }, []);

  // Phím tắt Ctrl+B / Cmd+B bật/tắt thanh bên trong tab Chat
  useEffect(() => {
    function handleKeyDown(event) {
      if (view === "chat" && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        toggleSidebar();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [view, toggleSidebar]);

  // Đồng bộ view sang localStorage và hash trên URL
  useEffect(() => {
    localStorage.setItem("ptit_chatbot_view", view);
    if (window.location.hash.replace(/^#\/?/, "") !== view) {
      window.history.replaceState(null, "", `#${view}`);
    }
  }, [view]);

  // Theo dõi nút Back / Forward của trình duyệt
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

  // Chuyển màn thì đóng drawer trên mobile, tránh việc nó che nội dung vừa mở
  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [view]);

  // Esc đóng drawer trên khổ hẹp
  useEffect(() => {
    if (!mobileSidebarOpen) return undefined;
    function onKeyDown(event) {
      if (event.key === "Escape") setMobileSidebarOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileSidebarOpen]);

  const refreshDocCount = useCallback(() => {
    // Giữ lại để các màn con báo có thay đổi; số liệu hiển thị nằm trong DatasetView.
    fetch(`${API_BASE_URL}/documents`).catch(() => {});
  }, []);

  const startNewChat = useCallback(() => {
    chatRef.current?.reset();
    setActiveConversationId(null);
    setView("chat");
    setMobileSidebarOpen(false);
  }, []);

  const openConversation = useCallback((conversationId) => {
    if (!conversationId) {
      chatRef.current?.reset();
      setActiveConversationId(null);
      return;
    }
    setActiveConversationId(conversationId);
    chatRef.current?.loadConversation(conversationId);
    setView("chat");
    setMobileSidebarOpen(false);
  }, []);

  const handleConversationSaved = useCallback((conversationId) => {
    setActiveConversationId(conversationId);
    setConversationsToken((token) => token + 1);
  }, []);

  const isSettingsView = view === "config" || view === "models" || view === "settings";

  return (
    <ToastProvider>
      <a className="skip-link" href="#main-content">
        Tới nội dung chính
      </a>

      <main
        className={`app-shell ${view === "chat" ? "view-chat" : "view-full"} ${
          mobileSidebarOpen ? "sidebar-open" : ""
        } ${desktopSidebarCollapsed ? "sidebar-collapsed" : ""}`}
      >
        <header className="app-header">
          <div className="app-header-left">
            {view === "chat" && (
              <button
                type="button"
                className={`sidebar-toggle-btn ${isSidebarOpen ? "is-open" : "is-collapsed"}`}
                onClick={toggleSidebar}
                aria-label={isSidebarOpen ? "Thu gọn thanh bên (Ctrl+B)" : "Mở thanh bên (Ctrl+B)"}
                aria-expanded={isSidebarOpen}
                aria-controls="chat-sidebar"
                title={isSidebarOpen ? "Thu gọn thanh bên (Ctrl+B)" : "Mở thanh bên (Ctrl+B)"}
              >
                {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
              </button>
            )}

            <button className="brand header-brand" onClick={() => setView("chat")} type="button">
              <div className="brand-mark">
                <Sparkles size={18} />
              </div>
              <div>
                <h1>PTIT Chatbot</h1>
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
              <Home size={15} />
            </button>
            {NAV_ITEMS.map((item) => {
              const active =
                view === item.key || (item.key === "config" && view === "settings");
              return (
                <button
                  key={item.key}
                  type="button"
                  className={`top-nav-item ${active ? "active" : ""}`}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setView(item.key)}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="app-header-right">
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="header-icon-link"
              title="Mã nguồn trên GitHub"
              aria-label="Mã nguồn trên GitHub"
            >
              <Github size={16} />
            </a>

            {/* Nhãn tĩnh: hệ thống hiện chỉ phục vụ tiếng Việt, không hứa hẹn lựa chọn chưa có */}
            <span className="lang-selector" title="Ngôn ngữ giao diện">
              Tiếng Việt
            </span>

            <button
              type="button"
              className={`header-icon-btn ${isSettingsView ? "active" : ""}`}
              title="Cấu hình hệ thống"
              aria-label="Cấu hình hệ thống"
              aria-current={isSettingsView ? "page" : undefined}
              onClick={() => setView("config")}
            >
              <Sliders size={15} />
            </button>

            <button
              type="button"
              className="header-icon-btn"
              title={THEME_LABELS[resolvedTheme]}
              aria-label={THEME_LABELS[resolvedTheme]}
              onClick={toggleTheme}
            >
              {resolvedTheme === "dark" ? <Moon size={15} /> : <Sun size={15} />}
            </button>

            <button
              type="button"
              className={`header-icon-btn ${theme === "system" ? "active" : ""}`}
              title={
                theme === "system"
                  ? "Đang theo giao diện hệ điều hành"
                  : "Theo giao diện hệ điều hành"
              }
              aria-label={
                theme === "system"
                  ? "Đang theo giao diện hệ điều hành"
                  : "Theo giao diện hệ điều hành"
              }
              aria-pressed={theme === "system"}
              onClick={() => setTheme("system")}
            >
              <Monitor size={15} />
            </button>
          </div>
        </header>

        {view === "chat" && (
          <>
            {mobileSidebarOpen && (
              <button
                type="button"
                className="sidebar-scrim"
                aria-label="Đóng thanh bên"
                onClick={() => setMobileSidebarOpen(false)}
              />
            )}
            <aside
              className="sidebar"
              id="chat-sidebar"
              aria-label="Thanh bên hội thoại"
              aria-hidden={!isSidebarOpen}
            >
              <div className="sidebar-top-bar">
                <button className="new-chat-btn" onClick={startNewChat} disabled={chatLoading}>
                  <RefreshCw size={16} />
                  Cuộc trò chuyện mới
                </button>
                <button
                  type="button"
                  className="sidebar-collapse-btn"
                  onClick={toggleSidebar}
                  aria-label="Thu gọn thanh bên (Ctrl+B)"
                  title="Thu gọn thanh bên (Ctrl+B)"
                >
                  <PanelLeftClose size={18} />
                </button>
              </div>

              <ConversationList
                activeId={activeConversationId}
                onOpen={openConversation}
                reloadToken={conversationsToken}
              />

              <details className="sidebar-section sidebar-tips">
                <summary className="sidebar-label">Mẹo sử dụng</summary>
                <ul className="tip-list">
                  {SIDEBAR_TIPS.map((tip, index) => (
                    <li key={index}>
                      <span className="tip-dot" />
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </details>
            </aside>
          </>
        )}

        <div className="main-pane" id="main-content">
          <ChatView
            ref={chatRef}
            hidden={view !== "chat"}
            onLoadingChange={setChatLoading}
            onConversationSaved={handleConversationSaved}
            isSidebarCollapsed={!isSidebarOpen}
            onToggleSidebar={toggleSidebar}
          />
          {view === "documents" && <DatasetView onChanged={refreshDocCount} />}
          {(view === "config" || view === "settings") && <ConfigView />}
          {view === "models" && <ModelsView />}
        </div>
      </main>
    </ToastProvider>
  );
}
