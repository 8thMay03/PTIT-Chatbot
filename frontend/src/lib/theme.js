import { useCallback, useEffect, useState } from "react";

export const THEME_STORAGE_KEY = "ptit_chatbot_theme";

/** "light" | "dark" | "system" */
const VALID_THEMES = ["light", "dark", "system"];

export function readStoredTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return VALID_THEMES.includes(saved) ? saved : "system";
  } catch {
    // Trình duyệt chặn storage (cửa sổ ẩn danh) — coi như chưa từng chọn.
    return "system";
  }
}

/**
 * Gắn theme vào DOM.
 *
 * Ở chế độ "system" ta KHÔNG đặt data-theme, để CSS quyết định qua
 * @media (prefers-color-scheme). Đặt thuộc tính này sẽ khoá cứng giao diện
 * và làm người dùng không theo được thiết lập hệ điều hành nữa.
 */
export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
}

/** Theme đang thực sự hiển thị, sau khi phân giải "system". */
export function resolveTheme(theme) {
  if (theme !== "system") return theme;
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme() {
  const [theme, setThemeState] = useState(readStoredTheme);
  const [resolved, setResolved] = useState(() => resolveTheme(readStoredTheme()));

  useEffect(() => {
    applyTheme(theme);
    setResolved(resolveTheme(theme));
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Không lưu được thì thôi, giao diện vẫn đúng trong phiên hiện tại.
    }
  }, [theme]);

  // Khi đang ở "system", theo dõi thay đổi cài đặt của hệ điều hành.
  useEffect(() => {
    if (theme !== "system" || !window.matchMedia) return undefined;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolved(query.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next) => {
    if (VALID_THEMES.includes(next)) setThemeState(next);
  }, []);

  /** Đảo giữa sáng và tối dựa trên thứ đang hiển thị, không phải trên "system". */
  const toggleTheme = useCallback(() => {
    setThemeState((current) => (resolveTheme(current) === "dark" ? "light" : "dark"));
  }, []);

  return { theme, resolvedTheme: resolved, setTheme, toggleTheme };
}
