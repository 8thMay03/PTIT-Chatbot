/**
 * Phân tuyến app theo pathname và ánh xạ hash cũ (FE-06, landing-user-auth).
 *
 * `/` trang landing, `/chat` app chat sinh viên, `/login` và `/register` trang tài
 * khoản (nhận `?next=`), `/admin*` app quản trị. Mỗi trang là một chunk lazy-load.
 * Các hash cũ của thời còn một app duy nhất được chuyển sang `/admin` hoặc `/chat`.
 */

/** Chuyển trang thay cho mục lịch sử hiện tại (tách hàm để test thay thế được). */
export function navigateTo(url) {
  window.location.replace(url);
}

/** Chuyển trang và giữ mục lịch sử hiện tại (nút Back quay lại được). */
export function goTo(url) {
  window.location.assign(url);
}

export const CHAT_PATH = "/chat";

export function isAdminPath(pathname) {
  const value = String(pathname || "");
  return value === "/admin" || value.startsWith("/admin/");
}

/** Pathname → `landing | chat | login | register | admin`; đường dẫn lạ về landing. */
export function resolveAppRoute(pathname) {
  if (isAdminPath(pathname)) return "admin";
  const value = String(pathname || "/").replace(/\/+$/, "") || "/";
  if (value === CHAT_PATH) return "chat";
  if (value === "/login") return "login";
  if (value === "/register") return "register";
  return "landing";
}

/**
 * Chỉ nhận đường dẫn nội bộ cho tham số `next` (chống open redirect).
 *
 * Hợp lệ khi bắt đầu bằng đúng một `/`, không phải `//` hay `/\` (trình duyệt hiểu
 * là host khác) và không có ký tự điều khiển/khoảng trắng; ngược lại trả `fallback`.
 */
export function safeNextPath(value, fallback = CHAT_PATH) {
  if (typeof value !== "string" || value.length === 0 || value.length > 2000) return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f\s\\]/.test(value)) return fallback;
  return value;
}

/** `next` hợp lệ trong query string hiện tại (hoặc `fallback`). */
export function readNextParam(search, fallback = CHAT_PATH) {
  const params = new URLSearchParams(String(search || ""));
  return safeNextPath(params.get("next"), fallback);
}

/** Link tới trang tài khoản kèm `next` (bỏ `next` khi trùng mặc định `/chat`). */
export function authPageHref(page, next = CHAT_PATH) {
  const target = safeNextPath(next);
  const base = page === "register" ? "/register" : "/login";
  return target === CHAT_PATH ? base : `${base}?next=${encodeURIComponent(target)}`;
}

/**
 * Hash cũ của app sinh viên tại `/` → đường dẫn mới ở `/chat`.
 *
 * Trước task này app chat nằm ở `/`; link đã lưu `/#chat` hay
 * `/#settings/appearance` phải mở lại đúng màn chat. Trả về null nếu không cần chuyển.
 */
export function legacyRootHashToChat(pathname, hash) {
  if (resolveAppRoute(pathname) !== "landing") return null;
  const route = String(hash || "").replace(/^#\/?/, "");
  if (route === "chat") return CHAT_PATH;
  if (route === "settings/appearance") return `${CHAT_PATH}#settings/appearance`;
  return null;
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
