import React, { useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

/**
 * Ô nhập của form tài khoản: nhãn, gợi ý, lỗi theo trường gắn `aria-describedby`,
 * và nút hiện/ẩn mật khẩu khi `type="password"`.
 */
export default function AuthField({
  label,
  name,
  type = "text",
  value,
  onChange,
  error,
  hint,
  autoComplete,
  autoFocus,
  inputRef,
  disabled,
  maxLength,
}) {
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ");

  return (
    <div className={`auth-field ${error ? "has-error" : ""}`.trim()}>
      <label className="auth-label" htmlFor={inputId}>
        {label}
      </label>
      <div className="auth-input-wrap">
        <input
          id={inputId}
          ref={inputRef}
          className="auth-input"
          name={name}
          type={isPassword && revealed ? "text" : type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          disabled={disabled}
          maxLength={maxLength}
          spellCheck={type === "email" || isPassword ? false : undefined}
          autoCapitalize={type === "email" || isPassword ? "none" : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
        />
        {isPassword && (
          <button
            type="button"
            className="auth-reveal"
            onClick={() => setRevealed((current) => !current)}
            aria-label={revealed ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            aria-pressed={revealed}
            aria-controls={inputId}
            title={revealed ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            disabled={disabled}
          >
            {revealed ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
          </button>
        )}
      </div>
      {hint && (
        <p className="auth-hint" id={hintId}>
          {hint}
        </p>
      )}
      {error && (
        <p className="auth-field-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}
