import React, { useRef } from "react";
import { ArrowUpRight, Github, GraduationCap, Sparkles, Wallet } from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";
import { useAuthSession, userInitial } from "../auth/session";
import FaqList from "./FaqList";
import FeatureBento from "./FeatureBento";
import HeroComposer from "./HeroComposer";
import StepsCarousel from "./StepsCarousel";
import TopicRing from "./TopicRing";
import { BACKGROUND_TEXT, REPO_URL, TOPIC_STRIP } from "./content";
import "./fonts";
import SplitWords, { wordCount } from "../lib/motion/SplitWords";
import useLandingMotion from "./motion/useLandingMotion";

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

/** Nút chính: hút theo chuột, sóng khi click và pixel transition khi rời trang. */
function PrimaryLink({ href, children, size = "lg", className = "", style }) {
  return (
    <a
      className={`lp-btn is-${size} ${className}`.trim()}
      href={href}
      style={style}
      data-magnetic
      data-pulse
      data-transition
    >
      {children}
      <ArrowUpRight className="lp-btn-arrow" size={size === "sm" ? 20 : 22} aria-hidden="true" />
    </a>
  );
}

/**
 * Các dòng của tiêu đề lớn, mỗi từ trượt lên từ mặt nạ (thẻ cha cần `data-reveal`).
 * `lines` là mảng `[chữ, mờ?]`; thứ tự từ nối tiếp giữa các dòng để độ trễ liền mạch.
 */
function DisplayLines({ lines }) {
  let start = 0;
  return lines.map(([text, muted]) => {
    const line = (
      <span key={text} className={`lp-display-line has-words ${muted ? "is-muted" : ""}`.trim()}>
        <SplitWords text={text} start={start} />
      </span>
    );
    start += wordCount(text);
    return line;
  });
}

/** Link điều hướng: chữ cuộn lên khi hover (bóng chữ đóng vai bản sao, không nhân đôi DOM). */
function RollLink({ href, children }) {
  return (
    <a className="lp-roll" href={href}>
      <span className="lp-roll-text">{children}</span>
    </a>
  );
}

function TopicMarquee() {
  const items = TOPIC_STRIP.map(({ label, icon: Icon }) => (
    <li key={label}>
      <Icon size={26} strokeWidth={1.75} aria-hidden="true" />
      {label}
    </li>
  ));
  return (
    <div className="lp-marquee" data-reveal="fade">
      <div className="lp-marquee-track">
        <ul className="lp-topic-strip" aria-label="Chủ đề chatbot hỗ trợ">
          {items}
        </ul>
        {/* Bản sao để vòng chạy liền mạch; chỉ hiện khi bật chuyển động. */}
        <ul className="lp-topic-strip is-clone" aria-hidden="true">
          {items}
        </ul>
      </div>
    </div>
  );
}

/** Nền chữ mờ phía sau khung soạn (trang trí); sáng dần theo từng dòng khi cuộn. */
function BackgroundText() {
  return (
    <p className="lp-bgtext" aria-hidden="true" data-scrub>
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
    <div className="lp-float-cards" aria-hidden="true" data-reveal="float">
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
  const rootRef = useRef(null);
  useLandingMotion(rootRef);

  return (
    <div className="landing-page" ref={rootRef}>
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
            <RollLink href="#tinh-nang">Tính năng</RollLink>
            <RollLink href="#cach-hoat-dong">Cách hoạt động</RollLink>
            <RollLink href="#cau-hoi">Câu hỏi thường gặp</RollLink>
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
                <a className="lp-nav-login" href="/login" data-transition>
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
            <h1 id="landing-title" className="lp-display" data-reveal="words">
              <DisplayLines
                lines={[
                  ["Hỏi đáp quy chế PTIT", false],
                  ["nhanh, có trích dẫn nguồn", true],
                ]}
              />
            </h1>
            <p className="lp-lead" data-reveal="up" style={{ "--d": "420ms" }}>
              Trả lời câu hỏi về quy chế đào tạo, học phí và thủ tục sinh viên dựa trên tài liệu chính
              thức, kèm trích dẫn để bạn tự kiểm tra.
            </p>
            {session.isAuthenticated && (
              <p className="lp-greeting">
                Xin chào, <strong>{user.full_name}</strong> — lịch sử hội thoại của bạn đã sẵn sàng.
              </p>
            )}
            <div className="lp-hero-cta" data-reveal="up" style={{ "--d": "560ms" }}>
              <PrimaryLink href="/chat">{chatLabel}</PrimaryLink>
            </div>
          </div>
          <HeroFloatCards />
          <div className="lp-hero-stage">
            <BackgroundText />
            <div className="lp-container lp-hero-composer" data-reveal="up" style={{ "--d": "700ms" }}>
              <HeroComposer />
              {!session.isAuthenticated && (
                <p className="lp-hero-note">
                  Không cần tài khoản để hỏi.{" "}
                  <a href="/login" data-transition>
                    Đăng nhập
                  </a>{" "}
                  để lưu lịch sử trên mọi thiết bị.
                </p>
              )}
            </div>
          </div>
          <div className="lp-container">
            <TopicMarquee />
          </div>
        </section>

        <section className="lp-section" id="tinh-nang" aria-labelledby="features-title">
          <div className="lp-container">
            <div className="lp-section-head">
              <h2 id="features-title" className="lp-display is-h2" data-reveal="words">
                <DisplayLines
                  lines={[
                    ["Hiểu câu hỏi tiếng Việt", false],
                    ["Chatbot giúp được gì", true],
                  ]}
                />
              </h2>
              <p data-reveal="up" style={{ "--d": "240ms" }}>
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
              <h2 id="faq-title" className="lp-display is-h2" data-reveal="words">
                <DisplayLines
                  lines={[
                    ["Câu hỏi", false],
                    ["thường gặp", true],
                  ]}
                />
              </h2>
              <p className="lp-faq-note" id="luu-y" data-reveal="up" style={{ "--d": "200ms" }}>
                Lưu ý khi sử dụng: chatbot có thể trả lời sai — luôn đối chiếu văn bản gốc qua trích dẫn
                trước khi làm thủ tục quan trọng.
              </p>
            </div>
            <FaqList />
          </div>
        </section>

        <section className="lp-cta" aria-labelledby="cta-title">
          <TopicRing />
          <div className="lp-cta-inner">
            <h2 id="cta-title" className="lp-display" data-reveal="words">
              <DisplayLines
                lines={[
                  [session.isAuthenticated ? "Tiếp tục cuộc trò chuyện" : "Sẵn sàng đặt câu hỏi?", false],
                  ["Hỏi PTIT Chatbot", true],
                ]}
              />
            </h2>
            <div data-reveal="up" style={{ "--d": "320ms" }}>
              <PrimaryLink href="/chat">{chatLabel}</PrimaryLink>
            </div>
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
                <a href="/chat" data-transition>
                  Trò chuyện
                </a>
                {!session.isAuthenticated && (
                  <a href="/login" data-transition>
                    Đăng nhập
                  </a>
                )}
                {!session.isAuthenticated && (
                  <a href="/register" data-transition>
                    Đăng ký
                  </a>
                )}
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
