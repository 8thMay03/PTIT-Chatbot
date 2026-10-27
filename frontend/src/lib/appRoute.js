/**
 * Phân tuyến app theo pathname và ánh xạ hash cũ (FE-06).
 *
 * App sinh viên nằm ở `/`; app admin nằm ở `/admin` (lazy-load). Các hash cũ của
 * thời còn một app duy nhất được chuyển sang `/admin` tương ứng.
 */

/** Chuyển trang thay cho mục lịch sử hiện tại (tách hàm để test thay thế được). */
export function navigateTo(url) {
  window.location.replace(url);
}

export function isAdminPath(pathname) {
  const value = String(pathname || "");
  return value === "/admin" || value.startsWith("/admin/");
}

/**
 * Hash cũ của trang chat → đường dẫn admin tương ứng.
 *
 * Trả về null khi hash thuộc app sinh viên (`#chat`, `#settings/appearance`)
 * hoặc không phải hash đã biết; `#settings/appearance` mở bộ chọn giao diện
 * tại chỗ chứ không chuyển trang.
 */
export function legacyHashToAdmin(hash) {
  const route = String(hash || "").replace(/^#\/?/, "");
  if (!route) return null;
  if (route === "documents") return "/admin#documents";
  if (route === "config") return "/admin#settings/config";
  if (route === "models") return "/admin#settings/models";
  if (route === "settings" || route.startsWith("settings/")) {
    const tab = route.split("/")[1];
    if (tab === "appearance") return null;
    return `/admin#settings/${tab === "models" ? "models" : "config"}`;
  }
  return null;
}

export const ADMIN_SETTINGS_TABS = ["config", "models", "appearance"];

/**
 * Hash con trong app admin → `{ view, tab }`; null nếu hash không hợp lệ.
 *
 * `#chat` → Chat; `#documents` → Dataset; `#settings/<tab>` → Settings (tab lạ về `config`).
 * Chấp nhận cả `#config`/`#models` cũ cho link đã lưu trước khi tách app.
 */
export function readAdminRoute(hash) {
  const route = String(hash || "").replace(/^#\/?/, "");
  if (route === "chat" || route === "documents") return { view: route, tab: "config" };
  if (route === "config" || route === "models") return { view: "settings", tab: route };
  if (route === "settings" || route.startsWith("settings/")) {
    const tab = route.split("/")[1];
    return {
      view: "settings",
      tab: ADMIN_SETTINGS_TABS.includes(tab) ? tab : "config",
    };
  }
  return null;
}

/** Route admin → hash tương ứng (không có dấu `#`). */
export function adminRouteHash({ view, tab }) {
  if (view === "settings") return `settings/${tab}`;
  return view === "documents" ? "documents" : "chat";
}

/** Hash `#settings/appearance` (bộ chọn giao diện) mở tại app sinh viên. */
export function isAppearanceHash(hash) {
  const route = String(hash || "").replace(/^#\/?/, "");
  return route === "settings/appearance";
}
