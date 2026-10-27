import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Database,
  Github,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import ChatView from "../ChatView";
import DatasetView from "../DatasetView";
import SettingsView from "../SettingsView";
import ConversationList from "../components/ConversationList";
import { queryKeys } from "../api";
import { adminRouteHash, readAdminRoute } from "../lib/appRoute";
import { useSidebar } from "../lib/useSidebar";
import { useTheme } from "../lib/theme";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";
const ADMIN_VIEW_KEY = "ptit_chatbot_admin_view";

function getInitialRoute() {
  let stored = null;
  try {
    stored = localStorage.getItem(ADMIN_VIEW_KEY);
  } catch {
    // Storage bị chặn: mở trang chat mặc định.
  }
  return (
    readAdminRoute(window.location.hash) ||
    readAdminRoute(stored) || { view: "chat", tab: "config" }
  );
}

/**
 * Khung trang quản trị: giữ bố cục đầy đủ như trước khi tách app — chat, lịch sử
 * hội thoại, Dataset, Settings — thêm nút đăng xuất. Hash `#chat`, `#documents`,
 * `#settings/<tab>`.
 */
export default function AdminShell({ onLogout, loggingOut = false, inert = false }) {
  const [route, setRoute] = useState(getInitialRoute);
  const [chatLoading, setChatLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const { theme, setTheme } = useTheme();
  const sidebar = useSidebar();
  const { isMobile, isOpen: isSidebarOpen, mobileOpen, setMobileOpen } = sidebar;
  const chatRef = useRef(null);
  const queryClient = useQueryClient();
  const { view, tab } = route;

  useEffect(() => {
    const hash = adminRouteHash(route);
    try {
      localStorage.setItem(ADMIN_VIEW_KEY, hash);
    } catch {
      // Không lưu được màn gần nhất cũng không ảnh hưởng chức năng.
    }
    if (window.location.hash.slice(1) !== hash) {
      window.history.replaceState(null, "", `#${hash}`);
    }
  }, [route]);

  useEffect(() => {
    function handleHashChange() {
      const next = readAdminRoute(window.location.hash);
      if (next) setRoute(next);
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Chuyển màn thì đóng drawer trên mobile, tránh việc nó che nội dung vừa mở.
  useEffect(() => {
    setMobileOpen(false);
  }, [view, setMobileOpen]);

  const goTo = useCallback(
    (nextView) => {
      setRoute((current) => ({ ...current, view: nextView }));
      setMobileOpen(false);
    },
    [setMobileOpen]
  );

  const startNewChat = useCallback(() => {
    chatRef.current?.reset();
    setActiveConversationId(null);
    goTo("chat");
  }, [goTo]);

  const openConversation = useCallback(
    (conversationId) => {
      if (!conversationId) {
        chatRef.current?.reset();
        setActiveConversationId(null);
        return;
      }
      setActiveConversationId(conversationId);
      chatRef.current?.loadConversation(conversationId);
      goTo("chat");
    },
    [goTo]
  );

  const handleConversationSaved = useCallback(
    (conversationId) => {
      setActiveConversationId(conversationId);
      queryClient.invalidateQueries({ queryKey: queryKeys.conversationList });
    },
    [queryClient]
  );

  return (
    <main
      className={`app-shell admin-shell ${view === "chat" ? "view-chat" : "view-full"} ${
        mobileOpen ? "sidebar-open" : ""
      } ${sidebar.desktopCollapsed ? "sidebar-collapsed" : ""}`}
      inert={inert ? "" : undefined}
      aria-hidden={inert || undefined}
    >
      {isMobile && mobileOpen && (
        <button
          type="button"
          className="sidebar-scrim"
          aria-label="Đóng thanh bên"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className="sidebar"
        id="app-sidebar"
        aria-label="Điều hướng và hội thoại"
        aria-hidden={isMobile && !mobileOpen}
        inert={isMobile && !mobileOpen ? "" : undefined}
      >
        <div className="sidebar-brand-row">
          <button
            className="brand sidebar-brand"
            onClick={() => goTo("chat")}
            type="button"
            aria-label="PTIT Chatbot — Chat"
          >
            <span className="brand-mark">
              <ShieldCheck size={19} />
            </span>
            <span className="sidebar-brand-copy">
              <strong>PTIT Chatbot</strong>
              <small>Quản trị</small>
            </span>
          </button>
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={sidebar.toggle}
            aria-label={
              isSidebarOpen ? "Thu gọn thanh bên (Ctrl+B)" : "Mở rộng thanh bên (Ctrl+B)"
            }
            title={isSidebarOpen ? "Thu gọn thanh bên (Ctrl+B)" : "Mở rộng thanh bên (Ctrl+B)"}
            aria-expanded={isSidebarOpen}
            aria-controls="app-sidebar"
          >
            {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
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
            onClick={() => goTo("documents")}
          >
            <Database size={18} />
            <span className="sidebar-nav-label">Dataset</span>
          </button>
        </nav>
        <div className="sidebar-chat-area">
          <ConversationList
            activeId={view === "chat" ? activeConversationId : null}
            onOpen={openConversation}
          />
        </div>
        <div className="sidebar-footer">
          <button
            type="button"
            className={`sidebar-nav-item ${view === "settings" ? "active" : ""}`}
            aria-current={view === "settings" ? "page" : undefined}
            title="Settings"
            onClick={() => goTo("settings")}
          >
            <Settings size={18} />
            <span className="sidebar-nav-label">Settings</span>
          </button>
          <button
            type="button"
            className="sidebar-nav-item"
            onClick={onLogout}
            disabled={loggingOut}
            title="Đăng xuất"
          >
            <LogOut size={18} />
            <span className="sidebar-nav-label">
              {loggingOut ? "Đang đăng xuất…" : "Đăng xuất"}
            </span>
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
        inert={isMobile && mobileOpen ? "" : undefined}
      >
        {isMobile && (
          <button
            type="button"
            className="mobile-menu-btn"
            onClick={sidebar.toggle}
            aria-label="Mở menu điều hướng"
            aria-expanded={mobileOpen}
            aria-controls="app-sidebar"
          >
            <Menu size={20} />
          </button>
        )}
        {/* Chat luôn mounted (chỉ ẩn) để không mất cuộc trò chuyện đang dở khi sang Dataset/Settings. */}
        <ChatView
          ref={chatRef}
          hidden={view !== "chat"}
          onLoadingChange={setChatLoading}
          onConversationSaved={handleConversationSaved}
        />
        {view === "documents" && <DatasetView />}
        {view === "settings" && (
          <SettingsView
            activeTab={tab}
            onTabChange={(nextTab) => setRoute({ view: "settings", tab: nextTab })}
            theme={theme}
            onThemeChange={setTheme}
          />
        )}
      </div>
    </main>
  );
}
