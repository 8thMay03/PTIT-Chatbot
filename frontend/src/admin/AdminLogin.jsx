import React, { useId, useState } from "react";
import { AlertCircle, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { adminApi, describeError } from "../api";

/**
 * Form mật khẩu admin dùng cho cả màn đăng nhập đầy đủ lẫn lớp phủ khi phiên hết
 * hạn giữa chừng. `onSuccess` nhận body của `POST /admin/login`.
 */
export function AdminLoginForm({ configured = true, onSuccess, autoFocus = true }) {
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const inputId = useId();
  const errorId = useId();

  async function handleSubmit(event) {
    event.preventDefault();
    if (!password || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await adminApi.login(password);
      setPassword("");
      onSuccess?.(result);
    } catch (loginError) {
      // 401 sai mật khẩu, 429 dò quá ngưỡng, 503 chưa cấu hình: backend đã gửi
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

  const disabled = !configured || submitting;

  return (
    <form className="admin-login-form" onSubmit={handleSubmit} noValidate>
      {!configured && (
        <div className="admin-login-alert is-warning" role="status">
          <AlertCircle size={16} aria-hidden="true" />
          <span>
            Backend chưa cấu hình <code>ADMIN_PASSWORD</code>. Đặt biến môi trường này rồi khởi
            động lại backend để bật trang quản trị.
          </span>
        </div>
      )}
      <label className="admin-login-label" htmlFor={inputId}>
        Mật khẩu quản trị
      </label>
      <input
        id={inputId}
        className="admin-login-input"
        type="password"
        name="password"
        autoComplete="current-password"
        autoFocus={autoFocus}
        value={password}
        disabled={!configured}
        onChange={(event) => setPassword(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
      />
      {error && (
        <div className="admin-login-alert is-danger" id={errorId} role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{error.detail || error.title}</span>
        </div>
      )}
      <button type="submit" className="primary-btn admin-login-submit" disabled={disabled || !password}>
        {submitting ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <LogIn size={16} aria-hidden="true" />}
        {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
      </button>
    </form>
  );
}

/** Màn đăng nhập đầy đủ khi mở `/admin` mà chưa có phiên. */
export default function AdminLogin({ configured = true, onSuccess }) {
  return (
    <main className="admin-login-page">
      <section className="admin-login-card" aria-labelledby="admin-login-title">
        <div className="admin-login-heading">
          <span className="brand-mark" aria-hidden="true">
            <ShieldCheck size={19} />
          </span>
          <div>
            <h1 id="admin-login-title">Quản trị PTIT Chatbot</h1>
            <p>Đăng nhập để quản lý Dataset và cấu hình.</p>
          </div>
        </div>
        <AdminLoginForm configured={configured} onSuccess={onSuccess} />
        <a className="admin-login-back" href="/">
          ← Về trang chat
        </a>
      </section>
    </main>
  );
}
