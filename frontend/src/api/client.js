import { ApiError, abortError, isAbortError } from "./errors";

// Mặc định cùng origin qua proxy (Vite dev/nginx) để cookie phiên (ptit_sid,
// ptit_admin) luôn được gửi. Ai chạy frontend không qua proxy tự đặt biến này
// cho đúng địa chỉ backend.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "/api";

/** Thời gian chờ mặc định cho API thường. Tải/parse tài liệu truyền timeout riêng. */
export const DEFAULT_TIMEOUT_MS = 30_000;

const unauthorizedListeners = new Set();

/**
 * Đăng ký nghe mọi response 401 đi qua `request()`; trả về hàm huỷ đăng ký.
 *
 * App admin dùng để hiện lại form đăng nhập khi phiên hết hạn giữa chừng, kể cả
 * với request không đi qua TanStack Query. Listener nhận `{ path, error }`.
 */
export function onUnauthorized(listener) {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function notifyUnauthorized(path, error) {
  unauthorizedListeners.forEach((listener) => {
    try {
      listener({ path: String(path || "").replace(/^\/+/, ""), error });
    } catch {
      // Lỗi trong listener không được làm hỏng luồng lỗi của request.
    }
  });
}

function buildUrl(path, query) {
  const root = API_BASE_URL.replace(/\/+$/, "");
  const suffix = String(path || "").startsWith("/") ? String(path) : `/${path}`;
  let url = `${root}${suffix}`;

  if (query) {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      params.set(key, String(value));
    });
    const serialized = params.toString();
    if (serialized) url += (url.includes("?") ? "&" : "?") + serialized;
  }

  return url;
}

function formatDuration(milliseconds) {
  if (milliseconds >= 60_000 && milliseconds % 60_000 === 0) {
    return `${milliseconds / 60_000} phút`;
  }
  if (milliseconds >= 1_000 && milliseconds % 1_000 === 0) {
    return `${milliseconds / 1_000} giây`;
  }
  return `${milliseconds} ms`;
}

function timeoutError(milliseconds) {
  return new ApiError({
    status: 0,
    code: "timeout",
    detail:
      `Yêu cầu quá thời gian chờ (${formatDuration(milliseconds)}). ` +
      "Máy chủ có thể đang xử lý lâu hoặc mất kết nối.",
  });
}

function extractDetail(payload) {
  if (!payload) return "";
  if (typeof payload === "string") return payload.trim();
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => {
        if (typeof item === "string") return item;
        const location = Array.isArray(item?.loc)
          ? item.loc.filter((part) => part !== "body").join(".")
          : "";
        const message = item?.msg || item?.message || "";
        return [location, message].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof payload.message === "string") return payload.message;
  if (typeof payload.error === "string") return payload.error;
  return "";
}

async function responseToApiError(response) {
  let detail = "";
  const contentType = response.headers?.get?.("content-type") || "";

  try {
    if (contentType.includes("application/json")) {
      detail = extractDetail(await response.json());
    } else if (contentType) {
      const text = await response.text();
      // Không đưa nguyên trang HTML lỗi của proxy vào thông báo cho người dùng.
      if (text && text.length <= 500 && !text.trim().startsWith("<")) {
        detail = text.trim();
      }
    } else {
      // FastAPI luôn trả JSON; một số proxy/test double không gắn content-type.
      try {
        detail = extractDetail(await response.json());
      } catch {
        const text = await response.text();
        if (text && text.length <= 500 && !text.trim().startsWith("<")) {
          detail = text.trim();
        }
      }
    }
  } catch {
    // Body lỗi không đọc được: dùng thông điệp theo mã trạng thái bên dưới.
  }

  if (!detail) {
    detail =
      response.status >= 500
        ? `Máy chủ gặp lỗi (mã ${response.status}).`
        : `Máy chủ từ chối yêu cầu (mã ${response.status}).`;
  }

  return new ApiError({
    status: response.status,
    detail,
    code: "http",
    url: response.url,
  });
}

function prepareBody(body, headers) {
  if (body === undefined || body === null) return undefined;
  if (
    typeof body === "string" ||
    body instanceof FormData ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body) ||
    body instanceof URLSearchParams
  ) {
    return body;
  }
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return JSON.stringify(body);
}

async function parseResponse(response, responseType) {
  switch (responseType) {
    case "none":
      return null;
    case "text":
      return response.text();
    case "blob":
      return response.blob();
    case "arrayBuffer":
      return response.arrayBuffer();
    case "json":
    default:
      if (response.status === 204) return null;
      try {
        return await response.json();
      } catch (error) {
        throw new ApiError({
          status: response.status,
          code: "invalid_response",
          detail: "Máy chủ trả về dữ liệu không hợp lệ.",
          cause: error,
        });
      }
  }
}

/**
 * Gọi API với base URL, JSON, timeout và lỗi chuẩn hoá.
 *
 * `signal` của caller dùng để huỷ khi rời màn. Khi hết `timeout`, request ném
 * `ApiError` mã `timeout` thay vì `AbortError` để màn hình hiển thị đúng nguyên nhân.
 */
export async function request(path, options = {}) {
  const {
    method = "GET",
    query,
    body,
    headers,
    signal,
    timeout = DEFAULT_TIMEOUT_MS,
    responseType = "json",
    ...fetchOptions
  } = options;

  const controller = new AbortController();
  let timedOut = false;
  let callerAborted = false;
  let keepCallerListener = false;

  const onCallerAbort = () => {
    callerAborted = true;
    controller.abort();
  };

  if (signal) {
    if (signal.aborted) onCallerAbort();
    else signal.addEventListener("abort", onCallerAbort, { once: true });
  }

  const timer =
    timeout > 0
      ? setTimeout(() => {
          timedOut = true;
          controller.abort();
        }, timeout)
      : null;

  try {
    if (callerAborted) throw abortError();

    const requestHeaders = new Headers(headers);
    const payload = prepareBody(body, requestHeaders);
    const init = {
      ...fetchOptions,
      headers: requestHeaders,
      body: payload,
      // Gửi cookie phiên ẩn danh/admin theo mọi request (cùng origin qua proxy).
      credentials: "include",
      signal: controller.signal,
    };
    if (method && method !== "GET") init.method = method;

    const response = await fetch(buildUrl(path, query), init);

    if (!response.ok) {
      const apiError = await responseToApiError(response);
      if (apiError.status === 401) notifyUnauthorized(path, apiError);
      throw apiError;
    }

    // Stream/response được caller đọc tiếp; giữ listener để nút "Dừng" còn tác dụng
    // và chỉ giới hạn thời gian tới lúc nhận header.
    if (responseType === "stream" || responseType === "response") {
      if (timer) clearTimeout(timer);
      keepCallerListener = Boolean(signal);
      return response;
    }

    return await parseResponse(response, responseType);
  } catch (error) {
    if (callerAborted) throw abortError();
    if (timedOut) throw timeoutError(timeout);
    if (error instanceof ApiError) throw error;
    if (isAbortError(error)) throw error;
    if (error instanceof TypeError) {
      throw new ApiError({
        status: 0,
        code: "network",
        detail:
          "Trình duyệt không gọi được API. Kiểm tra kết nối mạng, hoặc xem server FastAPI đã chạy chưa.",
        cause: error,
      });
    }
    throw error;
  } finally {
    if (timer) clearTimeout(timer);
    if (signal && !keepCallerListener) {
      signal.removeEventListener("abort", onCallerAbort);
    }
  }
}
