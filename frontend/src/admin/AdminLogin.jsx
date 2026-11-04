import React, { useId, useState } from "react";
import { AlertCircle, Loader2, LogIn } from "lucide-react";
import { adminApi, describeError } from "../api";
import { normalizeEmail, validateLogin } from "../auth/validation";

/**
 * Form email + mật khẩu quản trị cho lớp phủ khi phiên hết hạn giữa chừng (giữ bản
 * nháp đang sửa). Đăng nhập lần đầu dùng trang `/login` chung. `onSuccess` nhận body
 * của `POST /admin/login`.
 */
export function AdminLoginForm({ onSuccess, autoFocus = true }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const emailId = useId();
  const passwordId = useId();
  const errorId = useId();

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    const fieldErrors = validateLogin({ email, password });
    const firstError = fieldErrors.email || fieldErrors.password;
    if (firstError) {
      setError({ title: firstError });
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await adminApi.login({ email: normalizeEmail(email), password });
      setPassword("");
      onSuccess?.(result);
    } catch (loginError) {
      // 401 sai thông tin, 429 dò quá ngưỡng, 503 chưa cấu hình: backend đã gửi
      // chi tiết tiếng Việt, describeError giữ nguyên chi tiết đó.
      setError(
        describeError(loginError, {
          unauthorizedTitle: "Không đăng nhập được",
          rateLimitTitle: "Tạm khoá đăng nhập",
        })
      );
    } finally {
      setSubmitting(false);
    }
  }

  const describedBy = error ? errorId : undefined;

  return (
    <form className="admin-login-form" onSubmit={handleSubmit} noValidate>
      <label className="admin-login-label" htmlFor={emailId}>
        Email
      </label>
      <input
        id={emailId}
        className="admin-login-input"
        type="email"
        name="email"
        autoComplete="username"
        autoFocus={autoFocus}
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
      <label className="admin-login-label" htmlFor={passwordId}>
        Mật khẩu
      </label>
      <input
        id={passwordId}
        className="admin-login-input"
        type="password"
        name="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
      {error && (
        <div className="admin-login-alert is-danger" id={errorId} role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{error.detail || error.title}</span>
        </div>
      )}
      <button
        type="submit"
        className="primary-btn admin-login-submit"
        disabled={submitting || !email || !password}
      >
        {submitting ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <LogIn size={16} aria-hidden="true" />}
        {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
      </button>
    </form>
  );
}
