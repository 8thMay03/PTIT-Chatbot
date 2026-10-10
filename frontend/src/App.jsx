import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Github,
  Database,
  Settings,
  Plus,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
} from "lucide-react";
import ChatView from "./ChatView";
import DatasetView from "./DatasetView";
import SettingsView from "./SettingsView";
import ConversationList from "./components/ConversationList";
import { ToastProvider } from "./components/Toast";
import { useTheme } from "./lib/theme";
import { API_BASE_URL } from "./api";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

function readRoute(value) {
  const route = String(value || "").replace(/^#\/?/, "");
  if (route === "config") return { view: "settings", tab: "config" };
  if (route === "models") return { view: "settings", tab: "models" };
  if (route === "settings" || route.startsWith("settings/")) {
    const tab = route.split("/")[1];
    return {
      view: "settings",
      tab: ["config", "models", "appearance"].includes(tab) ? tab : "config",
    };
  }
  if (route === "chat" || route === "documents")
    return { view: route, tab: "config" };
  return null;
}

function getInitialRoute() {
  return (
    readRoute(window.location.hash) ||
    readRoute(localStorage.getItem("ptit_chatbot_view")) || {
      view: "chat",
      tab: "config",
    }
  );
}

export default function App() {
  const [initialRoute] = useState(getInitialRoute);
  const [view, setView] = useState(initialRoute.view);
  const [settingsTab, setSettingsTab] = useState(initialRoute.tab);
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
  const { theme, setTheme } = useTheme();
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

  // Phím tắt Ctrl+B / Cmd+B bật/tắt thanh bên trên mọi trang
  useEffect(() => {
    function handleKeyDown(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        toggleSidebar();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  // Giữ URL cũ #config / #models tương thích với trang Settings mới.
  useEffect(() => {
    const route = view === "settings" ? `settings/${settingsTab}` : view;
    localStorage.setItem("ptit_chatbot_view", route);
    if (window.location.hash.slice(1) !== route) {
      window.history.replaceState(null, "", `#${route}`);
    }
  }, [view, settingsTab]);

  useEffect(() => {
    function handleHashChange() {
      const route = readRoute(window.location.hash);
      if (route) {
        setView(route.view);
        setSettingsTab(route.tab);
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
        {isMobile && mobileSidebarOpen && (
          <button
            type="button"
            className="sidebar-scrim"
            aria-label="Đóng thanh bên"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}
        <aside
          className="sidebar"
          id="app-sidebar"
          aria-label="Điều hướng và hội thoại"
          aria-hidden={isMobile && !mobileSidebarOpen}
          inert={isMobile && !mobileSidebarOpen ? "" : undefined}
        >
          <div className="sidebar-brand-row">
            <button
              className="brand sidebar-brand"
              onClick={() => setView("chat")}
              type="button"
              aria-label="PTIT Chatbot — Chat"
            >
              <span className="brand-mark">
                <Sparkles size={19} />
              </span>
              <span className="sidebar-brand-copy">
                <strong>PTIT Chatbot</strong>
                <small>Trợ lý học vụ</small>
              </span>
            </button>
            <button
              type="button"
              className="sidebar-collapse-btn"
              onClick={toggleSidebar}
              aria-label={
                isSidebarOpen
                  ? "Thu gọn thanh bên (Ctrl+B)"
                  : "Mở rộng thanh bên (Ctrl+B)"
              }
              title={
                isSidebarOpen
                  ? "Thu gọn thanh bên (Ctrl+B)"
                  : "Mở rộng thanh bên (Ctrl+B)"
              }
              aria-expanded={isSidebarOpen}
              aria-controls="app-sidebar"
            >
              {isSidebarOpen ? (
                <PanelLeftClose size={18} />
              ) : (
                <PanelLeftOpen size={18} />
              )}
            </button>
          </div>
          <nav className="sidebar-nav" aria-label="Điều hướng chính">
            <button
              type="button"
              className={`sidebar-nav-item ${view === "chat" && !activeConversationId ? "active" : ""}`}
              onClick={startNewChat}
              disabled={chatLoading}
              title="Cuộc trò chuyện mới"
              aria-label="Cuộc trò chuyện mới"
            >
              <Plus size={18} />
              <span className="sidebar-nav-label">Cuộc trò chuyện mới</span>
            </button>
            <button
              type="button"
              className={`sidebar-nav-item ${view === "documents" ? "active" : ""}`}
              aria-current={view === "documents" ? "page" : undefined}
              title="Dataset"
              onClick={() => {
                setView("documents");
                setMobileSidebarOpen(false);
              }}
            >
              <Database size={18} />
              <span className="sidebar-nav-label">Dataset</span>
            </button>
          </nav>
          <div className="sidebar-chat-area">
            <ConversationList
              activeId={view === "chat" ? activeConversationId : null}
              onOpen={openConversation}
              reloadToken={conversationsToken}
            />
          </div>
          <div className="sidebar-footer">
            <button
              type="button"
              className={`sidebar-nav-item ${view === "settings" ? "active" : ""}`}
              aria-current={view === "settings" ? "page" : undefined}
              onClick={() => {
                setView("settings");
                setMobileSidebarOpen(false);
              }}
              title="Settings"
            >
              <Settings size={18} />
              <span className="sidebar-nav-label">Settings</span>
            </button>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="sidebar-source-link"
              aria-label="Mã nguồn trên GitHub"
              title="Mã nguồn trên GitHub"
            >
              <Github size={15} />
              <span className="sidebar-nav-label">Mã nguồn · PTIT Chatbot</span>
            </a>
          </div>
        </aside>

        <div
          className="main-pane"
          id="main-content"
          tabIndex={-1}
          inert={isMobile && mobileSidebarOpen ? "" : undefined}
        >
          {isMobile && (
            <button
              type="button"
              className="mobile-menu-btn"
              onClick={toggleSidebar}
              aria-label="Mở menu điều hướng"
              aria-expanded={mobileSidebarOpen}
              aria-controls="app-sidebar"
            >
              <Menu size={20} />
            </button>
          )}
          <ChatView
            ref={chatRef}
            hidden={view !== "chat"}
            onLoadingChange={setChatLoading}
            onConversationSaved={handleConversationSaved}
          />
          {view === "documents" && <DatasetView onChanged={refreshDocCount} />}
          {view === "settings" && (
            <SettingsView
              activeTab={settingsTab}
              onTabChange={setSettingsTab}
              theme={theme}
              onThemeChange={setTheme}
            />
          )}
        </div>
      </main>
    </ToastProvider>
  );
}
