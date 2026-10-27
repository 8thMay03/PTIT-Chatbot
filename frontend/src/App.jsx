import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Github,
  Menu,
  Palette,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Sparkles,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import ChatView from "./ChatView";
import ConversationList from "./components/ConversationList";
import Modal from "./components/Modal";
import ThemePicker from "./components/ThemePicker";
import { ToastProvider } from "./components/Toast";
import { isAppearanceHash, legacyHashToAdmin, navigateTo } from "./lib/appRoute";
import { useSidebar } from "./lib/useSidebar";
import { useTheme } from "./lib/theme";
import { queryKeys } from "./api";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

/**
 * App sinh viên: chat, lịch sử hội thoại của phiên và bộ chọn giao diện.
 *
 * Không import bất kỳ màn quản trị nào (Dataset/Settings nằm trong chunk
 * `admin/` lazy-load tại `/admin`); hash cũ của các màn đó chuyển sang `/admin`.
 */
export default function App() {
  const [chatLoading, setChatLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [appearanceOpen, setAppearanceOpen] = useState(() =>
    isAppearanceHash(window.location.hash)
  );
  const { theme, setTheme } = useTheme();
  const sidebar = useSidebar();
  const { isMobile, isOpen: isSidebarOpen, mobileOpen, setMobileOpen } = sidebar;
  const chatRef = useRef(null);
  const queryClient = useQueryClient();

  // Link cũ (#documents, #settings/config…) bấm ngay trong trang cũng phải sang /admin.
  useEffect(() => {
    function handleHashChange() {
      const adminTarget = legacyHashToAdmin(window.location.hash);
      if (adminTarget) {
        navigateTo(adminTarget);
        return;
      }
      if (isAppearanceHash(window.location.hash)) setAppearanceOpen(true);
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const closeAppearance = useCallback(() => {
    setAppearanceOpen(false);
    if (isAppearanceHash(window.location.hash)) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  }, []);

  const startNewChat = useCallback(() => {
    chatRef.current?.reset();
    setActiveConversationId(null);
    setMobileOpen(false);
  }, [setMobileOpen]);

  const openConversation = useCallback(
    (conversationId) => {
      if (!conversationId) {
        chatRef.current?.reset();
        setActiveConversationId(null);
        return;
      }
      setActiveConversationId(conversationId);
      chatRef.current?.loadConversation(conversationId);
      setMobileOpen(false);
    },
    [setMobileOpen]
  );

  const handleConversationSaved = useCallback(
    (conversationId) => {
      setActiveConversationId(conversationId);
      queryClient.invalidateQueries({ queryKey: queryKeys.conversationList });
    },
    [queryClient]
  );

  return (
    <ToastProvider>
      <a className="skip-link" href="#main-content">
        Tới nội dung chính
      </a>

      <main
        className={`app-shell view-chat ${mobileOpen ? "sidebar-open" : ""} ${
          sidebar.desktopCollapsed ? "sidebar-collapsed" : ""
        }`}
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
            <div className="brand sidebar-brand is-static">
              <span className="brand-mark">
                <Sparkles size={19} />
              </span>
              <span className="sidebar-brand-copy">
                <strong>PTIT Chatbot</strong>
                <small>Trợ lý học vụ</small>
              </span>
            </div>
            <button
              type="button"
              className="sidebar-collapse-btn"
              onClick={sidebar.toggle}
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
              className={`sidebar-nav-item ${!activeConversationId ? "active" : ""}`}
              onClick={startNewChat}
              disabled={chatLoading}
              title="Cuộc trò chuyện mới"
              aria-label="Cuộc trò chuyện mới"
            >
              <Plus size={18} />
              <span className="sidebar-nav-label">Cuộc trò chuyện mới</span>
            </button>
          </nav>
          <div className="sidebar-chat-area">
            <ConversationList activeId={activeConversationId} onOpen={openConversation} />
          </div>
          <div className="sidebar-footer">
            <button
              type="button"
              className="sidebar-nav-item"
              onClick={() => {
                setAppearanceOpen(true);
                setMobileOpen(false);
              }}
              title="Giao diện"
              aria-haspopup="dialog"
            >
              <Palette size={18} />
              <span className="sidebar-nav-label">Giao diện</span>
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
          <ChatView
            ref={chatRef}
            onLoadingChange={setChatLoading}
            onConversationSaved={handleConversationSaved}
          />
        </div>
      </main>

      <Modal
        open={appearanceOpen}
        onClose={closeAppearance}
        title="Giao diện"
        description="Chọn chế độ hiển thị phù hợp với bạn."
        actions={
          <button type="button" className="ghost-btn" onClick={closeAppearance}>
            Đóng
          </button>
        }
      >
        <ThemePicker theme={theme} onThemeChange={setTheme} className="is-compact" />
      </Modal>
    </ToastProvider>
  );
}
