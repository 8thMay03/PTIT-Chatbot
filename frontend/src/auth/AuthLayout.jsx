import React from "react";
import { Sparkles } from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";

/** Khung chung của trang đăng nhập/đăng ký: header về trang chủ, thẻ form, footer. */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="auth-page">
      <a className="skip-link" href="#auth-main">
        Tới nội dung chính
      </a>
      <header className="auth-header">
        <a className="site-brand" href="/" aria-label="PTIT Chatbot — Trang chủ">
          <span className="site-brand-mark" aria-hidden="true">
            <Sparkles size={18} />
          </span>
          <span className="site-brand-name">PTIT Chatbot</span>
        </a>
        <ThemeToggle />
      </header>
      <main className="auth-main" id="auth-main" tabIndex={-1}>
        <section className="auth-card" aria-labelledby="auth-title">
          <div className="auth-card-heading">
            <h1 id="auth-title">{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {children}
        </section>
        {footer && <div className="auth-switch">{footer}</div>}
      </main>
      <footer className="auth-footer">
        <a href="/">← Về trang chủ</a>
        <a href="/chat">Trò chuyện không cần tài khoản</a>
      </footer>
    </div>
  );
}
