import { request } from "./client";

/**
 * Trạng thái máy chủ cho header chat: `{ status: "ok" | "degraded", ... }`.
 *
 * Route công khai, không trả lý do lỗi. Timeout ngắn để header báo mất kết nối
 * sớm thay vì chờ 30 giây mặc định.
 */
export function get({ signal } = {}) {
  return request("health", { signal, timeout: 10_000 });
}
