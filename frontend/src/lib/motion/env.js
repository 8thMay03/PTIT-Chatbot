/**
 * Điều kiện bật chuyển động của trang landing. Thiếu `matchMedia` (jsdom, trình
 * duyệt rất cũ) hoặc người dùng bật "giảm chuyển động" → tắt hẳn: nội dung hiện
 * ngay và điều hướng không chờ hiệu ứng.
 */
function matches(query) {
  try {
    return Boolean(window.matchMedia(query).matches);
  } catch {
    return false;
  }
}

export function motionEnabled() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return !matches("(prefers-reduced-motion: reduce)");
}

/** Con trỏ chính hover được (chuột/bút) — điều kiện cho tilt và nút hút theo chuột. */
export function canHover() {
  return matches("(hover: hover) and (pointer: fine)");
}

export function clamp01(value) {
  return value < 0 ? 0 : value > 1 ? 1 : value;
}
