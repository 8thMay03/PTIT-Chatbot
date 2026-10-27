import { useCallback, useEffect, useState } from "react";

const SIDEBAR_COLLAPSE_BREAKPOINT = 900;
const SIDEBAR_COLLAPSED_KEY = "ptit_chatbot_sidebar_collapsed";

/**
 * State thanh bên dùng chung cho app sinh viên và app admin: thu gọn trên desktop,
 * drawer trên khổ hẹp, Ctrl/Cmd+B bật tắt, Esc đóng drawer.
 */
export function useSidebar() {
  const [desktopCollapsed, setDesktopCollapsed] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true";
    }
    return false;
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth <= SIDEBAR_COLLAPSE_BREAKPOINT;
    }
    return false;
  });

  useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth <= SIDEBAR_COLLAPSE_BREAKPOINT);
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggle = useCallback(() => {
    if (window.innerWidth <= SIDEBAR_COLLAPSE_BREAKPOINT) {
      setMobileOpen((open) => !open);
    } else {
      setDesktopCollapsed((collapsed) => {
        const next = !collapsed;
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
        return next;
      });
    }
  }, []);

  // Phím tắt Ctrl+B / Cmd+B bật/tắt thanh bên trên mọi trang.
  useEffect(() => {
    function handleKeyDown(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);

  // Esc đóng drawer trên khổ hẹp.
  useEffect(() => {
    if (!mobileOpen) return undefined;
    function onKeyDown(event) {
      if (event.key === "Escape") setMobileOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  const isOpen = isMobile ? mobileOpen : !desktopCollapsed;

  return {
    isMobile,
    isOpen,
    mobileOpen,
    setMobileOpen,
    desktopCollapsed,
    toggle,
  };
}
