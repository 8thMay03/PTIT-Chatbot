import { request } from "./client";

/**
 * API tài khoản người dùng (landing-user-auth).
 *
 * Mọi route đều công khai. `me()` không bao giờ trả 401: cookie sai/hết hạn được
 * coi là chưa đăng nhập. Register/login thành công đặt cookie `ptit_user`
 * HttpOnly và chuyển hội thoại ẩn danh của trình duyệt sang tài khoản.
 */

export function me({ signal } = {}) {
  return request("auth/me", { signal });
}

export function register({ fullName, email, password }) {
  return request("auth/register", {
    method: "POST",
    body: { full_name: fullName, email, password },
  });
}

export function login({ email, password }) {
  return request("auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function logout() {
  return request("auth/logout", { method: "POST" });
}
