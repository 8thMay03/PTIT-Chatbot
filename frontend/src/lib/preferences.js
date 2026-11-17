import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Tùy chọn của sinh viên trên trang chat (nhóm "Chung" trong hộp thoại Cài đặt):
 * cỡ chữ, gửi bằng Enter, giữ mở quá trình suy luận. Lưu trên thiết bị bằng một
 * khoá localStorage dạng JSON có `version`; giá trị lạ hoặc storage bị chặn thì
 * dùng mặc định. Giao diện sáng/tối vẫn do `lib/theme.js` giữ.
 */
export const PREFERENCES_STORAGE_KEY = "ptit_chatbot_prefs";
export const PREFERENCES_VERSION = 1;

/** "sm" | "md" | "lg"; "md" là cỡ chữ trước khi có tùy chọn này. */
export const FONT_SCALES = ["sm", "md", "lg"];

export const DEFAULT_PREFERENCES = Object.freeze({
  fontScale: "md",
  enterToSend: true,
  keepReasoningOpen: false,
});

/** Giữ từng trường hợp lệ, trường thiếu/sai kiểu về mặc định. */
export function normalizePreferences(raw) {
  const value = raw && typeof raw === "object" ? raw : {};
  return {
    fontScale: FONT_SCALES.includes(value.fontScale) ? value.fontScale : DEFAULT_PREFERENCES.fontScale,
    enterToSend:
      typeof value.enterToSend === "boolean" ? value.enterToSend : DEFAULT_PREFERENCES.enterToSend,
    keepReasoningOpen:
      typeof value.keepReasoningOpen === "boolean"
        ? value.keepReasoningOpen
        : DEFAULT_PREFERENCES.keepReasoningOpen,
  };
}

export function readPreferences() {
  try {
    const saved = localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (!saved) return { ...DEFAULT_PREFERENCES };
    const parsed = JSON.parse(saved);
    // Bản lưu của phiên bản khác: chưa có cách chuyển đổi nên dùng mặc định.
    if (parsed?.version !== PREFERENCES_VERSION) return { ...DEFAULT_PREFERENCES };
    return normalizePreferences(parsed);
  } catch {
    // Storage bị chặn hoặc JSON hỏng — coi như chưa từng chọn.
    return { ...DEFAULT_PREFERENCES };
  }
}

/** Ghi tùy chọn; trả `false` khi không lưu được (vẫn áp dụng trong phiên hiện tại). */
export function writePreferences(preferences) {
  try {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ version: PREFERENCES_VERSION, ...normalizePreferences(preferences) })
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Gắn cỡ chữ vào `<html data-font-scale>`; CSS đổi `--chat-font-scale` theo thuộc
 * tính này. Cỡ mặc định không đặt thuộc tính để giữ nguyên CSS hiện có.
 */
export function applyFontScale(fontScale) {
  const root = document.documentElement;
  if (fontScale === DEFAULT_PREFERENCES.fontScale || !FONT_SCALES.includes(fontScale)) {
    root.removeAttribute("data-font-scale");
  } else {
    root.setAttribute("data-font-scale", fontScale);
  }
}

/**
 * Tùy chọn hiện tại và `setPreference(key, value)`. Mỗi thay đổi áp dụng ngay và
 * tự lưu; `setPreference` trả `false` khi không lưu được trên thiết bị.
 */
export function usePreferences() {
  const [preferences, setPreferences] = useState(readPreferences);

  useEffect(() => {
    applyFontScale(preferences.fontScale);
  }, [preferences.fontScale]);

  // Trang chat là nơi duy nhất dùng tùy chọn này: rời trang thì bỏ cỡ chữ đã gắn.
  useEffect(() => () => applyFontScale(DEFAULT_PREFERENCES.fontScale), []);

  // Bản mới nhất để ghi đồng bộ trong `setPreference` (updater của setState có thể
  // chạy muộn hoặc hai lần ở StrictMode nên không ghi storage trong đó).
  const latestRef = useRef(preferences);
  latestRef.current = preferences;

  const setPreference = useCallback((key, value) => {
    if (!(key in DEFAULT_PREFERENCES)) return false;
    const next = normalizePreferences({ ...latestRef.current, [key]: value });
    latestRef.current = next;
    setPreferences(next);
    return writePreferences(next);
  }, []);

  return { ...preferences, setPreference };
}
