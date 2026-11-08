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
