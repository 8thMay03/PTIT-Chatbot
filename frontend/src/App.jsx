import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Github,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  Sparkles,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import ChatView from "./ChatView";
import ConversationList from "./components/ConversationList";
import { ToastProvider } from "./components/Toast";
import UserMenu, { GuestHint } from "./components/UserMenu";
import {
  isAppearanceHash,
  legacyHashToAdmin,
  navigateTo,
  readQuestionParam,
} from "./lib/appRoute";
import useChatMotion from "./lib/motion/useChatMotion";
import { usePreferences } from "./lib/preferences";
import { useSidebar } from "./lib/useSidebar";
import { useTheme } from "./lib/theme";
import { queryKeys, STUDENT_ERROR_CONTEXT } from "./api";
import StudentSettingsDialog from "./student-settings/StudentSettingsDialog";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

/**
 * App sinh viên tại `/chat`: chat, lịch sử hội thoại (của tài khoản khi đã đăng
 * nhập, ngược lại của phiên ẩn danh), khối tài khoản ở chân thanh bên và hộp thoại
 * Cài đặt (Chung, Tài khoản, Dữ liệu & lịch sử).
 *
 * Không import bất kỳ màn quản trị nào (Dataset/Settings nằm trong chunk
 * `admin/` lazy-load tại `/admin`); hash cũ của các màn đó chuyển sang `/admin`.
 */
export default function App() {
  const [chatLoading, setChatLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState(null);
  // Mục đang mở của hộp thoại Cài đặt (`general | account | data`), null khi đóng.
  // Hash cũ `#settings/appearance` mở thẳng mục Chung.
  const [settingsSection, setSettingsSection] = useState(() =>
    isAppearanceHash(window.location.hash) ? "general" : null
  );
  // Câu hỏi gửi từ khung soạn ở landing (`/chat?q=`): chỉ điền sẵn vào ô nhập.
  const [prefillQuestion] = useState(() => readQuestionParam(window.location.search));
  const { theme, setTheme } = useTheme();
  const preferences = usePreferences();
  const sidebar = useSidebar();
  const { isMobile, isOpen: isSidebarOpen, mobileOpen, setMobileOpen } = sidebar;
  const chatRef = useRef(null);
  const shellRef = useRef(null);
  const queryClient = useQueryClient();
  useChatMotion(shellRef);

  // Bỏ `q` khỏi URL sau khi đọc để tải lại trang không điền lại câu hỏi cũ.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("q")) return;
    params.delete("q");
    const search = params.toString();
    window.history.replaceState(
      null,
      "",
      window.location.pathname + (search ? `?${search}` : "") + window.location.hash
    );
  }, []);

  // Link cũ (#documents, #settings/config…) bấm ngay trong trang cũng phải sang /admin.
  useEffect(() => {
    function handleHashChange() {
      const adminTarget = legacyHashToAdmin(window.location.hash);
      if (adminTarget) {
        navigateTo(adminTarget);
        return;
      }
      if (isAppearanceHash(window.location.hash)) setSettingsSection("general");
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const closeSettings = useCallback(() => {
    setSettingsSection(null);
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

  // Đăng xuất (menu tài khoản hoặc Cài đặt): cache hội thoại đã bị xoá (useLogout);
  // đưa màn chat về hội thoại mới để không còn hiện hội thoại của tài khoản. Xoá
  // toàn bộ hội thoại trong Cài đặt cũng dùng đường này.
  const handleLoggedOut = useCallback(() => {
    chatRef.current?.reset();
    setActiveConversationId(null);
  }, []);

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
        ref={shellRef}
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
            <a
              className="brand sidebar-brand"
              href="/"
              aria-label="PTIT Chatbot — Trang chủ"
              data-transition
            >
              <span className="brand-mark">
                <Sparkles size={19} />
              </span>
              <span className="sidebar-brand-copy">
                <strong>PTIT Chatbot</strong>
                <small>Trợ lý học vụ</small>
              </span>
            </a>
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
              data-pulse
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
            <ConversationList
              activeId={activeConversationId}
              onOpen={openConversation}
              errorContext={STUDENT_ERROR_CONTEXT}
            />
          </div>
          <div className="sidebar-footer">
            <GuestHint />
            {/* Trên mobile giữ drawer mở: hộp thoại phủ toàn màn hình và khi đóng
                trả focus về đúng nút trong drawer (drawer đóng thì nút bị inert). */}
            <button
              type="button"
              className="sidebar-nav-item"
              onClick={() => setSettingsSection("general")}
              title="Cài đặt"
              aria-haspopup="dialog"
            >
              <Settings size={18} />
              <span className="sidebar-nav-label">Cài đặt</span>
            </button>
            <UserMenu
              onLoggedOut={handleLoggedOut}
              onOpenSettings={setSettingsSection}
              compact={!isMobile && sidebar.desktopCollapsed}
            />
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
            onNewChat={startNewChat}
            initialInput={prefillQuestion}
            errorContext={STUDENT_ERROR_CONTEXT}
            enterToSend={preferences.enterToSend}
            keepReasoningOpen={preferences.keepReasoningOpen}
          />
        </div>
      </main>

      <StudentSettingsDialog
        open={settingsSection !== null}
        initialSection={settingsSection ?? "general"}
        onClose={closeSettings}
        theme={theme}
        onThemeChange={setTheme}
        preferences={preferences}
        onLoggedOut={handleLoggedOut}
        onHistoryCleared={handleLoggedOut}
      />
    </ToastProvider>
  );
}
