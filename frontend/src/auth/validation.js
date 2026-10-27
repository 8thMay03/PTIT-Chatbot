import { ApiError, describeError, fieldErrors as apiFieldErrors } from "../api";

/**
 * Kiểm tra phía client cho form tài khoản — cùng quy tắc với backend
 * (`backend/app/api/schemas.py`, `app/core/user_auth.py`) để lỗi hiện ngay khi
 * gõ sai, backend vẫn là nơi kiểm cuối cùng.
 */
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const FULL_NAME_MAX_LENGTH = 100;

const EMAIL_RE =
  /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$/;

export function normalizeEmail(value) {
  return String(value || "").trim().toLowerCase();
}

function emailError(value) {
  const email = normalizeEmail(value);
  if (!email) return "Vui lòng nhập email.";
  if (email.length > 254 || !EMAIL_RE.test(email)) return "Email không đúng định dạng.";
  return null;
}

function compact(errors) {
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => Boolean(message)));
}

export function validateLogin({ email, password }) {
  return compact({
    email: emailError(email),
    password: password ? null : "Vui lòng nhập mật khẩu.",
  });
}

export function validateRegister({ fullName, email, password, confirmPassword }) {
  const name = String(fullName || "").trim().replace(/\s+/g, " ");
  let passwordError = null;
  if (!password) passwordError = "Vui lòng nhập mật khẩu.";
  else if (password.length < PASSWORD_MIN_LENGTH)
    passwordError = `Mật khẩu phải có ít nhất ${PASSWORD_MIN_LENGTH} ký tự.`;
  else if (password.length > PASSWORD_MAX_LENGTH)
    passwordError = `Mật khẩu tối đa ${PASSWORD_MAX_LENGTH} ký tự.`;

  let confirmError = null;
  if (!confirmPassword) confirmError = "Vui lòng nhập lại mật khẩu.";
  else if (confirmPassword !== password) confirmError = "Mật khẩu nhập lại không khớp.";

  return compact({
    fullName: !name
      ? "Vui lòng nhập họ tên."
      : name.length > FULL_NAME_MAX_LENGTH
        ? `Họ tên tối đa ${FULL_NAME_MAX_LENGTH} ký tự.`
        : null,
    email: emailError(email),
    password: passwordError,
    confirmPassword: confirmError,
  });
}

// Tên trường của API (snake_case) → tên trường trong form.
const API_FIELD_TO_FORM = { full_name: "fullName", email: "email", password: "password" };

/**
 * Lỗi từ `POST /auth/login|register` → `{ message, fields }` để hiện cạnh form.
 *
 * `message` là lỗi chung (null nếu đã gắn hết vào trường), `fields` gắn vào ô
 * tương ứng. `registrationClosed` báo trang đăng ký ẩn form (503).
 */
export function describeAuthError(error, mode = "login") {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return { message: error.detail || "Email hoặc mật khẩu không đúng.", fields: {} };
    }
    if (error.status === 409) {
      return {
        message: "Email này đã có tài khoản. Hãy đăng nhập hoặc dùng email khác.",
        fields: { email: "Email đã được đăng ký." },
      };
    }
    if (error.status === 422) {
      const fields = {};
      for (const [field, message] of Object.entries(apiFieldErrors(error))) {
        fields[API_FIELD_TO_FORM[field] ?? field] = message;
      }
      return {
        message: Object.keys(fields).length
          ? "Vui lòng kiểm tra lại các ô được đánh dấu."
          : error.detail || "Dữ liệu không hợp lệ.",
        fields,
      };
    }
    if (error.status === 429) {
      return {
        message: "Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại.",
        fields: {},
      };
    }
    if (error.status === 503 && mode === "register") {
      return {
        message: error.detail || "Hệ thống đang tạm dừng đăng ký tài khoản mới.",
        fields: {},
        registrationClosed: true,
      };
    }
  }
  const described = describeError(error, {
    fallbackTitle: mode === "register" ? "Không đăng ký được" : "Không đăng nhập được",
  });
  const separator = /[.!?…]$/.test(described.title) ? " " : ". ";
  return {
    message: described.detail ? `${described.title}${separator}${described.detail}` : described.title,
    fields: {},
  };
}
