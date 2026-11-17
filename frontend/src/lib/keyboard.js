/**
 * Enter đang dùng để chốt chữ của bộ gõ IME (Vietnamese Telex trên macOS/Windows,
 * IBus/Fcitx...). Chrome/Edge đặt `isComposing`; Safari phát `keydown` của Enter
 * chốt chữ sau `compositionend` (khi đó `isComposing` là `false`) với `keyCode` 229.
 */
export function isImeComposing(event) {
  const native = event?.nativeEvent ?? event;
  return Boolean(native?.isComposing) || native?.keyCode === 229;
}

/** Enter gửi tin: không kèm Shift và không phải Enter chốt chữ IME. */
export function isSubmitEnter(event) {
  return event.key === "Enter" && !event.shiftKey && !isImeComposing(event);
}

/** macOS/iOS dùng Cmd thay cho Ctrl trong phím tắt. */
export function isApplePlatform(nav = typeof navigator === "undefined" ? undefined : navigator) {
  const platform = nav?.userAgentData?.platform || nav?.platform || "";
  return /mac|iphone|ipad|ipod/i.test(platform);
}

/**
 * Phím gửi tin của ô nhập chat theo tùy chọn "Gửi bằng Enter".
 *
 * Bật (mặc định): như `isSubmitEnter`. Tắt: Enter xuống dòng, Ctrl+Enter
 * (Cmd+Enter trên macOS) gửi. Cả hai trường hợp đều bỏ qua Enter chốt chữ IME.
 */
export function isSubmitKey(event, { enterToSend = true } = {}) {
  if (enterToSend) return isSubmitEnter(event);
  return event.key === "Enter" && (event.ctrlKey || event.metaKey) && !isImeComposing(event);
}
