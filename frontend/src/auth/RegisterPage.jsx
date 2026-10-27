import React, { useEffect, useId } from "react";
import { Info, Loader2, UserPlus } from "lucide-react";
import { authApi } from "../api";
import { authPageHref, navigateTo, readNextParam } from "../lib/appRoute";
import AuthField from "./AuthField";
import AuthLayout from "./AuthLayout";
import FormAlert from "./FormAlert";
import { useApplySignedIn, useAuthSession } from "./session";
import { useAuthForm } from "./useAuthForm";
import {
  FULL_NAME_MAX_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  normalizeEmail,
  validateRegister,
} from "./validation";

/**
 * Trang `/register`: tạo tài khoản bằng họ tên + email + mật khẩu (chưa xác thực
 * email). Hội thoại ẩn danh của trình duyệt này được chuyển sang tài khoản mới.
 */
export default function RegisterPage() {
  const next = readNextParam(window.location.search);
  const session = useAuthSession();
  const applySignedIn = useApplySignedIn();
  const formErrorId = useId();
  const form = useAuthForm({
    initialValues: { fullName: "", email: "", password: "", confirmPassword: "" },
    fieldOrder: ["fullName", "email", "password", "confirmPassword"],
    validate: validateRegister,
    submit: ({ fullName, email, password }) =>
      authApi.register({
        fullName: fullName.trim().replace(/\s+/g, " "),
        email: normalizeEmail(email),
        password,
      }),
    mode: "register",
    onSuccess: (result) => {
      applySignedIn(result);
      navigateTo(next);
    },
  });

  useEffect(() => {
    if (session.isAuthenticated && !form.submitting) navigateTo(next);
  }, [session.isAuthenticated, form.submitting, next]);

  const closed = !session.registrationEnabled || form.registrationClosed;

  return (
    <AuthLayout
      title="Tạo tài khoản"
      subtitle="Lưu lịch sử hội thoại và xem lại trên mọi thiết bị."
      footer={
        <p>
          Đã có tài khoản? <a href={authPageHref("login", next)}>Đăng nhập</a>
        </p>
      }
    >
      {closed ? (
        <div className="auth-alert is-info" role="status">
          <Info size={16} aria-hidden="true" />
          <span>
            Hệ thống đang tạm dừng đăng ký tài khoản mới. Bạn vẫn có thể{" "}
            <a href="/chat">trò chuyện không cần tài khoản</a> hoặc{" "}
            <a href={authPageHref("login", next)}>đăng nhập</a> bằng tài khoản đã có.
          </span>
        </div>
      ) : (
        <form
          className="auth-form"
          onSubmit={form.handleSubmit}
          noValidate
          aria-describedby={form.formError ? formErrorId : undefined}
        >
          <AuthField
            label="Họ và tên"
            name="name"
            autoComplete="name"
            autoFocus
            maxLength={FULL_NAME_MAX_LENGTH}
            value={form.values.fullName}
            onChange={(value) => form.setField("fullName", value)}
            error={form.errors.fullName}
            inputRef={form.registerRef("fullName")}
          />
          <AuthField
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            value={form.values.email}
            onChange={(value) => form.setField("email", value)}
            error={form.errors.email}
            inputRef={form.registerRef("email")}
          />
          <AuthField
            label="Mật khẩu"
            name="new-password"
            type="password"
            autoComplete="new-password"
            hint={`Từ ${PASSWORD_MIN_LENGTH} đến ${PASSWORD_MAX_LENGTH} ký tự.`}
            value={form.values.password}
            onChange={(value) => form.setField("password", value)}
            error={form.errors.password}
            inputRef={form.registerRef("password")}
          />
          <AuthField
            label="Nhập lại mật khẩu"
            name="confirm-password"
            type="password"
            autoComplete="new-password"
            value={form.values.confirmPassword}
            onChange={(value) => form.setField("confirmPassword", value)}
            error={form.errors.confirmPassword}
            inputRef={form.registerRef("confirmPassword")}
          />
          <p className="auth-note">
            Hệ thống chưa xác thực email và chưa có chức năng quên mật khẩu — hãy dùng email của bạn
            và ghi nhớ mật khẩu.
          </p>
          <FormAlert id={formErrorId} message={form.formError} />
          <button type="submit" className="auth-submit" disabled={form.submitting}>
            {form.submitting ? (
              <Loader2 size={17} className="spin" aria-hidden="true" />
            ) : (
              <UserPlus size={17} aria-hidden="true" />
            )}
            {form.submitting ? "Đang tạo tài khoản…" : "Đăng ký"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
