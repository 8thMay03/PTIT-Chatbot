import React from "react";
import { ArrowUpRight, Github, GraduationCap, Sparkles, Wallet } from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";
import { useAuthSession, userInitial } from "../auth/session";
import FaqList from "./FaqList";
import FeatureBento from "./FeatureBento";
import HeroComposer from "./HeroComposer";
import StepsCarousel from "./StepsCarousel";
import { BACKGROUND_TEXT, REPO_URL, TOPIC_STRIP } from "./content";
import "./fonts";

function BrandMark({ inverted = false }) {
  return (
    <span className={`lp-brand ${inverted ? "is-inverted" : ""}`.trim()}>
      <span className="lp-brand-tile" aria-hidden="true">
        <Sparkles size={24} />
      </span>
      <span className="lp-brand-name">PTIT Chatbot</span>
    </span>
  );
}

function PrimaryLink({ href, children, size = "lg", className = "" }) {
  return (
    <a className={`lp-btn is-${size} ${className}`.trim()} href={href}>
      {children}
      <ArrowUpRight size={size === "sm" ? 20 : 22} aria-hidden="true" />
    </a>
  );
}

/** Nền chữ mờ phía sau khung soạn/dải kêu gọi (trang trí). */
function BackgroundText({ className = "" }) {
  return (
    <p className={`lp-bgtext ${className}`.trim()} aria-hidden="true">
      {/* Lặp hai lần để phủ kín vùng nền như thiết kế. */}
      {[...BACKGROUND_TEXT, [" ", null], ...BACKGROUND_TEXT].map(([text, tone], index) =>
        tone ? (
          <span key={index} className={`lp-kw is-${tone}`}>
            {text}
          </span>
        ) : (
          <React.Fragment key={index}>{text}</React.Fragment>
        )
      )}
    </p>
  );
}

/** Hai thẻ nghiêng hai bên hero (Figma node 2002:535), chỉ để trang trí. */
function HeroFloatCards() {
  return (
    <div className="lp-float-cards" aria-hidden="true">
      <div className="lp-float-card is-left">
        <p className="lp-float-title">Câu hỏi gợi ý</p>
        <p className="lp-float-row">
          <span className="lp-float-icon">
            <Wallet size={13} />
          </span>
          Học phí kỳ này?
        </p>
        <p className="lp-float-title">Hỏi tiếp</p>
        <p className="lp-float-row">
          <span className="lp-float-icon">
            <GraduationCap size={13} />
          </span>
          Điều kiện tốt nghiệp
        </p>
      </div>
      <div className="lp-float-card is-right">
        <p className="lp-float-menu is-active">
          <span className="lp-cite">1</span>Quy chế đào tạo
        </p>
        <p className="lp-float-menu">Sổ tay sinh viên</p>
        <p className="lp-float-menu">Quy định học bổng</p>
        <span className="lp-float-divider" />
        <p className="lp-float-menu">Mở văn bản gốc…</p>
      </div>
    </div>
  );
}

/**
 * Trang giới thiệu tại `/`, dựng theo Figma "AI Chat landing page UI kit"
 * (frame 2002:456) với nội dung tiếng Việt trung thực về PTIT Chatbot.
 */
export default function LandingPage() {
  const session = useAuthSession();
  const { user } = session;
  const chatLabel = session.isAuthenticated ? "Vào trò chuyện" : "Bắt đầu trò chuyện";

  return (
    <div className="landing-page">
      <a className="skip-link" href="#landing-main">
        Tới nội dung chính
      </a>

      <header className="lp-nav">
        <div className="lp-container lp-nav-inner">
          <a className="lp-nav-brand" href="/" aria-label="PTIT Chatbot — Trang chủ">
            <BrandMark />
            <span className="lp-nav-divider" aria-hidden="true" />
            <span className="lp-nav-tagline">Trợ lý học vụ</span>
          </a>
          <nav className="lp-nav-links" aria-label="Các mục trên trang">
            <a href="#tinh-nang">Tính năng</a>
            <a href="#cach-hoat-dong">Cách hoạt động</a>
            <a href="#cau-hoi">Câu hỏi thường gặp</a>
          </nav>
          <div className="lp-nav-actions">
            <ThemeToggle className="lp-theme-toggle" />
            {session.isAuthenticated ? (
              <>
                <span className="lp-nav-user" title={user.email}>
                  <span className="lp-avatar" aria-hidden="true">
                    {userInitial(user)}
                  </span>
                  <span className="lp-nav-user-name">{user.full_name}</span>
                </span>
                <PrimaryLink href="/chat" size="sm">
                  Vào trò chuyện
                </PrimaryLink>
              </>
            ) : (
              <>
                <a className="lp-nav-login" href="/login">
                  Đăng nhập
                </a>
                <PrimaryLink href="/register" size="sm">
                  Đăng ký
                </PrimaryLink>
              </>
            )}
          </div>
        </div>
      </header>

      <main id="landing-main" tabIndex={-1}>
        <section className="lp-hero" aria-labelledby="landing-title">
          <span className="lp-haze" aria-hidden="true" />
          <div className="lp-container lp-hero-copy">
            <h1 id="landing-title" className="lp-display">
              <span className="lp-display-line">Hỏi đáp quy chế PTIT</span>
              <span className="lp-display-line is-muted">nhanh, có trích dẫn nguồn</span>
            </h1>
            <p className="lp-lead">
              Trả lời câu hỏi về quy chế đào tạo, học phí và thủ tục sinh viên dựa trên tài liệu chính
              thức, kèm trích dẫn để bạn tự kiểm tra.
            </p>
            {session.isAuthenticated && (
              <p className="lp-greeting">
                Xin chào, <strong>{user.full_name}</strong> — lịch sử hội thoại của bạn đã sẵn sàng.
              </p>
            )}
            <PrimaryLink href="/chat">{chatLabel}</PrimaryLink>
          </div>
          <HeroFloatCards />
          <div className="lp-hero-stage">
            <BackgroundText />
            <div className="lp-container lp-hero-composer">
              <HeroComposer />
              {!session.isAuthenticated && (
                <p className="lp-hero-note">
                  Không cần tài khoản để hỏi. <a href="/login">Đăng nhập</a> để lưu lịch sử trên mọi thiết
                  bị.
                </p>
              )}
            </div>
          </div>
          <div className="lp-container">
            <ul className="lp-topic-strip" aria-label="Chủ đề chatbot hỗ trợ">
              {TOPIC_STRIP.map(({ label, icon: Icon }) => (
                <li key={label}>
                  <Icon size={26} strokeWidth={1.75} aria-hidden="true" />
                  {label}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="lp-section" id="tinh-nang" aria-labelledby="features-title">
          <div className="lp-container">
            <div className="lp-section-head">
              <h2 id="features-title" className="lp-display is-h2">
                <span className="lp-display-line">Hiểu câu hỏi tiếng Việt</span>
                <span className="lp-display-line is-muted">Chatbot giúp được gì</span>
              </h2>
              <p>
                Tra cứu nhanh thay vì lật từng trang quy chế, và vẫn biết câu trả lời lấy từ đâu.
              </p>
            </div>
            <FeatureBento />
          </div>
        </section>

        <section className="lp-section is-tight" id="cach-hoat-dong" aria-labelledby="how-title">
          <div className="lp-container">
            <h2 id="how-title" className="sr-only">
              Cách hoạt động
            </h2>
            <StepsCarousel />
          </div>
        </section>

        <section className="lp-section" id="cau-hoi" aria-labelledby="faq-title">
          <div className="lp-container">
            <div className="lp-section-head">
              <h2 id="faq-title" className="lp-display is-h2">
                <span className="lp-display-line">Câu hỏi</span>
                <span className="lp-display-line is-muted">thường gặp</span>
              </h2>
              <p className="lp-faq-note" id="luu-y">
                Lưu ý khi sử dụng: chatbot có thể trả lời sai — luôn đối chiếu văn bản gốc qua trích dẫn
                trước khi làm thủ tục quan trọng.
              </p>
            </div>
            <FaqList />
          </div>
        </section>

        <section className="lp-cta" aria-labelledby="cta-title">
          <BackgroundText className="is-cta" />
          <div className="lp-cta-inner">
            <h2 id="cta-title" className="lp-display">
              <span className="lp-display-line">
                {session.isAuthenticated ? "Tiếp tục cuộc trò chuyện" : "Sẵn sàng đặt câu hỏi?"}
              </span>
              <span className="lp-display-line is-muted">Hỏi PTIT Chatbot</span>
            </h2>
            <PrimaryLink href="/chat">{chatLabel}</PrimaryLink>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-container">
          <div className="lp-footer-top">
            <div className="lp-footer-brand">
              <BrandMark inverted />
              <p>Trợ lý tra cứu học vụ dựa trên tài liệu, kèm trích dẫn nguồn.</p>
            </div>
            <nav className="lp-footer-cols" aria-label="Liên kết cuối trang">
              <div className="lp-footer-col">
                <p className="lp-footer-heading">Sản phẩm</p>
                <a href="/chat">Trò chuyện</a>
                {!session.isAuthenticated && <a href="/login">Đăng nhập</a>}
                {!session.isAuthenticated && <a href="/register">Đăng ký</a>}
              </div>
              <div className="lp-footer-col">
                <p className="lp-footer-heading">Tìm hiểu</p>
                <a href="#tinh-nang">Tính năng</a>
                <a href="#cach-hoat-dong">Cách hoạt động</a>
                <a href="#cau-hoi">Câu hỏi thường gặp</a>
              </div>
              <div className="lp-footer-col">
                <p className="lp-footer-heading">Dự án</p>
                <a href={REPO_URL} target="_blank" rel="noreferrer">
                  <Github size={15} aria-hidden="true" />
                  Mã nguồn
                </a>
              </div>
            </nav>
          </div>
          <div className="lp-footer-bottom">
            <p>© {new Date().getFullYear()} PTIT Chatbot</p>
            <p>Thông tin chính thức luôn là văn bản do Học viện ban hành.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
