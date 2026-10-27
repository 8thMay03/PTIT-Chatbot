/**
 * Lỗi chuẩn của lớp API.
 *
 * `status` là mã HTTP (0 khi không có phản hồi), `detail` là thông điệp đọc được
 * dành cho người dùng, `code` phân biệt lỗi mạng/timeout với lỗi HTTP.
 */
export class ApiError extends Error {
  constructor({ status = 0, detail = "", code = "http", url, cause } = {}) {
    const message = detail || "Đã xảy ra lỗi khi gọi máy chủ.";
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = message;
    this.code = code;
    this.url = url;
    if (cause !== undefined) this.cause = cause;
  }
}

const NETWORK_DETAIL =
  "Trình duyệt không gọi được API. Kiểm tra kết nối mạng, hoặc xem server FastAPI đã chạy chưa.";
const UNKNOWN_DETAIL =
  "Có lỗi ngoài dự kiến. Kiểm tra server FastAPI và thử lại.";

export function isAbortError(error) {
  return Boolean(error) && (error.name === "AbortError" || error.code === "ABORT_ERR");
}

export function isTimeoutError(error) {
  return error instanceof ApiError && error.code === "timeout";
}

/** Request bị từ chối vì thiếu/hết hạn phiên đăng nhập (401). */
export function isUnauthorized(error) {
  return error instanceof ApiError && error.status === 401;
}

function abortError() {
  if (typeof DOMException !== "undefined") {
    return new DOMException("Yêu cầu đã bị huỷ.", "AbortError");
  }
  const error = new Error("Yêu cầu đã bị huỷ.");
  error.name = "AbortError";
  return error;
}

/**
 * Phân loại một lỗi thành tiêu đề + mô tả dùng chung cho toast và màn lỗi.
 *
 * Các màn hình có thể đổi câu chữ theo ngữ cảnh bằng `options`, nhưng cách phân
 * loại (mất mạng, timeout, 4xx, 5xx, 429) chỉ nằm ở đây.
 */
export function describeError(error, options = {}) {
  const {
    fallbackTitle = "Không thực hiện được yêu cầu",
    fallbackDetail = UNKNOWN_DETAIL,
    notFoundTitle = "Không tìm thấy dữ liệu",
    notFoundDetail,
    serverTitle = "Máy chủ gặp sự cố",
    serverDetail = "Backend trả về lỗi khi xử lý yêu cầu. Kiểm tra log server rồi thử lại.",
    rateLimitTitle = "Vượt quá giới hạn gọi mô hình",
    rateLimitDetail = "Nhà cung cấp LLM đang chặn tạm thời. Thử lại sau ít phút.",
    unauthorizedTitle = "Cần đăng nhập quản trị",
  } = options;

  if (isAbortError(error)) {
    return {
      kind: "aborted",
      title: "Đã huỷ yêu cầu",
      detail: "Yêu cầu đã được huỷ.",
    };
  }

  if (error instanceof ApiError) {
    if (error.code === "timeout") {
      return {
        kind: "timeout",
        title: "Máy chủ phản hồi quá lâu",
        detail: error.detail,
      };
    }
    if (error.code === "network") {
      return {
        kind: "network",
        title: "Không kết nối được máy chủ",
        detail: error.detail || NETWORK_DETAIL,
      };
    }
    if (error.status === 401) {
      return {
        kind: "unauthorized",
        title: unauthorizedTitle,
        detail: error.detail || "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
      };
    }
    if (error.status === 403) {
      return {
        kind: "forbidden",
        title: "Không có quyền thực hiện",
        detail: error.detail || "Bạn không có quyền thực hiện thao tác này.",
      };
    }
    if (error.status === 404) {
      return {
        kind: "not_found",
        title: notFoundTitle,
        detail: notFoundDetail ?? error.detail,
      };
    }
    if (error.status === 429) {
      return {
        kind: "rate_limit",
        title: rateLimitTitle,
        detail: error.detail || rateLimitDetail,
      };
    }
    if (error.status >= 500) {
      const backendDetail =
        error.detail && !error.detail.startsWith("Máy chủ gặp lỗi (mã ")
          ? error.detail
          : "";
      return {
        kind: "server",
        title: serverTitle,
        detail: backendDetail
          ? `${serverDetail} Chi tiết từ máy chủ: ${backendDetail}`
          : serverDetail,
      };
    }
    if (error.status >= 400) {
      return {
        kind: "client",
        title: fallbackTitle,
        detail: error.detail || fallbackDetail,
      };
    }
    return {
      kind: "unknown",
      title: fallbackTitle,
      detail: error.detail || fallbackDetail,
    };
  }

  if (error instanceof TypeError) {
    return {
      kind: "network",
      title: "Không kết nối được máy chủ",
      detail: NETWORK_DETAIL,
    };
  }

  return {
    kind: "unknown",
    title: fallbackTitle,
    detail: error?.message || fallbackDetail,
  };
}

/** Chuỗi lỗi ngắn gọn cho toast; vẫn đi qua cùng một bộ phân loại. */
export function errorMessage(error, fallback = UNKNOWN_DETAIL) {
  const described = describeError(error, {
    fallbackTitle: fallback,
    fallbackDetail: fallback,
  });
  if (described.kind === "client" || described.kind === "unknown") {
    return described.detail || described.title;
  }
  if (!described.detail) return described.title;
  const separator = /[.!?]$/.test(described.title) ? " " : ". ";
  return `${described.title}${separator}${described.detail}`;
}

export { abortError, NETWORK_DETAIL, UNKNOWN_DETAIL };
