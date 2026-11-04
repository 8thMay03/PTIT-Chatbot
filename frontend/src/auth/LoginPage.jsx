import React, { useEffect, useId } from "react";
import { Loader2, LogIn } from "lucide-react";
import { authApi } from "../api";
import { ADMIN_PATH, authPageHref, isAdminTarget, navigateTo, readNextParam } from "../lib/appRoute";
import AuthField from "./AuthField";
import AuthLayout from "./AuthLayout";
import FormAlert from "./FormAlert";
import { useApplySignedIn, useAuthSession } from "./session";
import { useAuthForm } from "./useAuthForm";
import { normalizeEmail, validateLogin } from "./validation";

/**
 * Trang `/login` dùng chung cho sinh viên và quản trị.
 *
 * Backend nhận diện email quản trị (`ADMIN_EMAIL`): phiên admin chuyển tới `?next=`
 * nếu đó là trang quản trị, ngược lại `/admin`; phiên sinh viên chuyển tới `?next=`
 * (chỉ đường dẫn nội bộ) hoặc `/chat`.
 */
export default function LoginPage() {
  const next = readNextParam(window.location.search);
  const session = useAuthSession();
  const applySignedIn = useApplySignedIn();
  const formErrorId = useId();
  const form = useAuthForm({
    initialValues: { email: "", password: "" },
    fieldOrder: ["email", "password"],
    validate: validateLogin,
    submit: ({ email, password }) => authApi.login({ email: normalizeEmail(email), password }),
    mode: "login",
    onSuccess: (result) => {
      if (result?.admin) {
        // Chỉ có cookie phiên quản trị, không phải phiên sinh viên: không ghi cache auth/me.
        navigateTo(isAdminTarget(next) ? next : ADMIN_PATH);
        return;
      }
      applySignedIn(result);
      navigateTo(next);
    },
  });

  // Đã đăng nhập mà mở /login: chuyển thẳng vào trang đích. Trừ khi đích là trang quản
  // trị: phiên sinh viên không mở được /admin, chuyển sang sẽ lặp /admin ↔ /login.
  const adminTarget = isAdminTarget(next);
  useEffect(() => {
    if (session.isAuthenticated && !form.submitting && !adminTarget) navigateTo(next);
  }, [session.isAuthenticated, form.submitting, adminTarget, next]);

  return (
    <AuthLayout
      title="Đăng nhập"
      subtitle={
        adminTarget
          ? "Đăng nhập bằng tài khoản quản trị để quản lý Dataset và cấu hình."
          : "Đăng nhập để xem lại lịch sử hội thoại trên mọi thiết bị."
      }
      footer={
        <p>
          Chưa có tài khoản? <a href={authPageHref("register", next)}>Đăng ký</a>
        </p>
      }
    >
      <form
        className="auth-form"
        onSubmit={form.handleSubmit}
        noValidate
        aria-describedby={form.formError ? formErrorId : undefined}
      >
        <AuthField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          autoFocus
          value={form.values.email}
          onChange={(value) => form.setField("email", value)}
          error={form.errors.email}
          inputRef={form.registerRef("email")}
        />
        <AuthField
          label="Mật khẩu"
          name="password"
          type="password"
          autoComplete="current-password"
          value={form.values.password}
          onChange={(value) => form.setField("password", value)}
          error={form.errors.password}
          inputRef={form.registerRef("password")}
        />
        <FormAlert id={formErrorId} message={form.formError} />
        <button type="submit" className="auth-submit" disabled={form.submitting}>
          {form.submitting ? (
            <Loader2 size={17} className="spin" aria-hidden="true" />
          ) : (
            <LogIn size={17} aria-hidden="true" />
          )}
          {form.submitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
      </form>
    </AuthLayout>
  );
}
