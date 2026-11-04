import { request } from "./client";

/**
 * API phiên và dữ liệu quản trị (FE-06).
 *
 * Toàn bộ route trong module này (trừ login/logout/session) yêu cầu cookie
 * phiên admin; server trả 401 khi thiếu/hết hạn — dùng `isUnauthorized` để
 * hiện lại form đăng nhập.
 */

export function session({ signal } = {}) {
  return request("admin/session", { signal });
}

/** Đăng nhập lại ở lớp phủ hết phiên; trang đầy đủ dùng `authApi.login` tại `/login`. */
export function login({ email, password }) {
  return request("admin/login", {
    method: "POST",
    body: { email, password },
  });
}

export function logout() {
  return request("admin/logout", { method: "POST" });
}

/** Danh sách toàn bộ hội thoại (dùng cho công cụ debug RAG của admin, FE-13). */
export function conversations({ limit = 50, offset = 0, owner, signal } = {}) {
  return request("admin/conversations", {
    query: { limit, offset, owner },
    signal,
  });
}

export function conversation(conversationId, { signal } = {}) {
  return request(`admin/conversations/${conversationId}`, { signal });
}
