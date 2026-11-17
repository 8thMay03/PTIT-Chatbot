import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronsUpDown, Loader2, LogIn, LogOut, Settings, X } from "lucide-react";
import { errorMessage } from "../api";
import { useAuthSession, useLogout, userInitial } from "../auth/session";
import { CHAT_PATH, authPageHref } from "../lib/appRoute";
import { useToast } from "./Toast";

export const GUEST_HINT_STORAGE_KEY = "ptit_chatbot_guest_hint_dismissed";

function readHintDismissed() {
  try {
    return localStorage.getItem(GUEST_HINT_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Khối tài khoản ở chân thanh bên (student-settings, Q-02): chip tên mở menu
 * "Cài đặt" / "Đăng xuất"; khách thấy link Đăng nhập. `onLoggedOut` để app chat
 * đưa màn về hội thoại mới, `onOpenSettings` mở hộp thoại Cài đặt; `compact` khi
 * thanh bên đang thu gọn (menu mở sang phải chip thay vì phía trên).
 *
 * Menu render qua portal vào `document.body`: thanh bên cắt phần tràn và hiệu ứng
 * vào trang (`animation … both`) biến chân thanh bên thành containing block và
 * stacking context riêng, nên menu nằm trong đó sẽ bị cắt hoặc bị nội dung chat đè.
 */
export default function UserMenu({ onLoggedOut, onOpenSettings, compact = false }) {
  const session = useAuthSession();
  const logout = useLogout();
  const toast = useToast();
  const [pending, setPending] = useState(false);
  const [open, setOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);
  const itemsRef = useRef([]);
  const menuId = `user-menu-${useId().replace(/:/g, "")}`;

  // Mở menu thì focus mục đầu; bấm ra ngoài hoặc đổi kích thước cửa sổ thì đóng.
  useEffect(() => {
    if (!open) return undefined;
    itemsRef.current[0]?.focus({ preventScroll: true });
    function onPointerDown(event) {
      if (!menuRef.current?.contains(event.target) && !triggerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    function onResize() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  if (session.isLoading) return null;

  if (!session.isAuthenticated) {
    return (
      <a
        className="sidebar-nav-item user-login-link"
        href={authPageHref("login", CHAT_PATH)}
        title="Đăng nhập"
        data-transition
      >
        <LogIn size={18} aria-hidden="true" />
        <span className="sidebar-nav-label">Đăng nhập</span>
      </a>
    );
  }

  function closeMenu() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  /** Vị trí cố định theo chip: phía trên (thanh bên mở) hoặc bên phải (thu gọn). */
  function toggleMenu() {
    if (open) {
      setOpen(false);
      return;
    }
    const rect = triggerRef.current.getBoundingClientRect();
    setMenuPosition(
      compact
        ? { left: rect.right + 8, bottom: window.innerHeight - rect.bottom, width: 240 }
        : { left: rect.left, bottom: window.innerHeight - rect.top + 6, width: rect.width }
    );
    setOpen(true);
  }

  function openSettings() {
    // Focus về nút chip trước để hộp thoại trả focus về đây khi đóng.
    closeMenu();
    onOpenSettings?.("general");
  }

  async function handleLogout() {
    if (pending) return;
    setPending(true);
    try {
      await logout();
      setOpen(false);
      onLoggedOut?.();
    } catch (error) {
      toast.error(errorMessage(error, "Không đăng xuất được."));
    } finally {
      setPending(false);
    }
  }

  function onMenuKeyDown(event) {
    const items = itemsRef.current.filter(Boolean);
    const index = items.indexOf(document.activeElement);
    if (event.key === "Escape") {
      // Không để Esc đóng luôn drawer thanh bên trên mobile.
      event.stopPropagation();
      closeMenu();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      items[(index + step + items.length) % items.length]?.focus({ preventScroll: true });
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      items[event.key === "Home" ? 0 : items.length - 1]?.focus({ preventScroll: true });
    } else if (event.key === "Tab") {
      // Menu nằm cuối <body> (portal): Tab tiếp sẽ rời trang, nên trả focus về chip.
      event.preventDefault();
      closeMenu();
    }
  }

  const { user } = session;
  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className="user-menu-list"
          id={menuId}
          role="menu"
          aria-label="Tài khoản"
          style={menuPosition ?? undefined}
          onKeyDown={onMenuKeyDown}
        >
          <div className="user-menu-head" aria-hidden="true">
            <strong>{user.full_name}</strong>
            <span>{user.email}</span>
          </div>
          <button
            ref={(node) => {
              itemsRef.current[0] = node;
            }}
            type="button"
            role="menuitem"
            className="user-menu-item"
            onClick={openSettings}
          >
            <Settings size={16} aria-hidden="true" />
            Cài đặt
          </button>
          <button
            ref={(node) => {
              itemsRef.current[1] = node;
            }}
            type="button"
            role="menuitem"
            className="user-menu-item"
            onClick={handleLogout}
            disabled={pending}
          >
            {pending ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <LogOut size={16} aria-hidden="true" />}
            Đăng xuất
          </button>
        </div>,
        document.body
      )
    : null;

  return (
    <div className="user-menu">
      {menu}
      <button
        ref={triggerRef}
        type="button"
        className="user-chip"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={`Tài khoản: ${user.full_name}`}
        title={user.email}
        onClick={toggleMenu}
        onKeyDown={(event) => {
          if ((event.key === "ArrowUp" || event.key === "ArrowDown") && !open) {
            event.preventDefault();
            toggleMenu();
          }
        }}
      >
        <span className="user-avatar" aria-hidden="true">
          {userInitial(user)}
        </span>
        <span className="user-chip-text sidebar-nav-label">
          <span className="user-name">{user.full_name}</span>
          <span className="user-email">{user.email}</span>
        </span>
        <ChevronsUpDown size={15} className="user-chip-caret sidebar-nav-label" aria-hidden="true" />
      </button>
    </div>
  );
}

/** Dòng nhắc nhẹ trong thanh bên cho khách; đóng được và nhớ bằng localStorage. */
export function GuestHint() {
  const session = useAuthSession();
  const [dismissed, setDismissed] = useState(readHintDismissed);

  if (session.isLoading || session.isAuthenticated || dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem(GUEST_HINT_STORAGE_KEY, "1");
    } catch {
      // Không lưu được thì chỉ ẩn trong phiên hiện tại.
    }
  }

  return (
    <div className="guest-hint">
      <p>
        <a href={authPageHref("login", CHAT_PATH)} data-transition>
          Đăng nhập
        </a>{" "}
        để lưu lịch sử trên mọi thiết bị.
      </p>
      <button type="button" className="guest-hint-close" onClick={dismiss} aria-label="Ẩn lời nhắc đăng nhập">
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}
