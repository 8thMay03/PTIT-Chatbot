import React from "react";
import {
  ArrowRight,
  BookOpenCheck,
  FileSearch,
  Github,
  History,
  LogIn,
  MessageSquareText,
  PenLine,
  Quote,
  SearchX,
  Sparkles,
  TriangleAlert,
  UserPlus,
} from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";
import { useAuthSession, userInitial } from "../auth/session";

const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

// Nội dung mô tả đúng khả năng hiện có của hệ thống (D-10): không số liệu/thống kê.
const FEATURES = [
  {
    icon: MessageSquareText,
    title: "Hỏi đáp quy chế, học vụ",
    text: "Đặt câu hỏi bằng tiếng Việt tự nhiên về quy chế đào tạo, học phí, thủ tục sinh viên — trong phạm vi các tài liệu đã được nạp vào hệ thống.",
  },
  {
    icon: Quote,
    title: "Trích dẫn nguồn rõ ràng",
    text: "Câu trả lời đánh số trích dẫn tới tài liệu và điều, khoản liên quan để bạn tự đối chiếu với văn bản gốc.",
  },
  {
    icon: BookOpenCheck,
    title: "Hiểu ngữ cảnh câu hỏi",
    text: "Hỏi tiếp dựa trên câu trước mà không cần nhắc lại toàn bộ; chatbot dùng các lượt gần nhất trong cùng hội thoại.",
  },
  {
    icon: History,
    title: "Lưu lịch sử hội thoại",
    text: "Không cần tài khoản vẫn hỏi được ngay. Đăng nhập để lịch sử theo bạn trên mọi thiết bị.",
  },
];

const STEPS = [
  {
    icon: PenLine,
    title: "Bạn đặt câu hỏi",
    text: "Gõ câu hỏi như khi hỏi phòng đào tạo hay cố vấn học tập.",
  },
  {
    icon: FileSearch,
    title: "Tìm trong tài liệu chính thức",
    text: "Hệ thống tìm các đoạn liên quan trong kho văn bản do quản trị viên nạp: quy chế, quy định, sổ tay sinh viên.",
  },
  {
    icon: Quote,
    title: "Trả lời kèm trích dẫn",
    text: "Mô hình ngôn ngữ soạn câu trả lời chỉ dựa trên các đoạn tìm được và gắn số trích dẫn tới nguồn.",
  },
  {
    icon: SearchX,
    title: "Nói rõ khi không biết",
    text: "Không tìm thấy thông tin phù hợp thì chatbot báo chưa có trong tài liệu thay vì tự đoán.",
  },
];

const LIMITS = [
  "Chatbot có thể trả lời sai, thiếu hoặc hiểu nhầm câu hỏi. Luôn mở trích dẫn để đối chiếu văn bản gốc trước khi làm thủ tục quan trọng.",
  "Chatbot chỉ biết nội dung các tài liệu đã được nạp; văn bản mới ban hành có thể chưa được cập nhật.",
  "Thông tin chính thức luôn là văn bản và thông báo do Học viện ban hành.",
  "Không nhập mật khẩu, số giấy tờ tuỳ thân hay thông tin nhạy cảm vào khung chat.",
];

function HeroActions({ session, size = "lg" }) {
  if (session.isAuthenticated) {
    return (
      <div className="landing-actions">
        <a className={`landing-btn is-primary is-${size}`} href="/chat">
          Vào trò chuyện
          <ArrowRight size={18} aria-hidden="true" />
        </a>
      </div>
    );
  }
  return (
    <div className="landing-actions">
      <a className={`landing-btn is-primary is-${size}`} href="/chat">
        Bắt đầu trò chuyện
        <ArrowRight size={18} aria-hidden="true" />
      </a>
      <a className={`landing-btn is-secondary is-${size}`} href="/register">
        <UserPlus size={18} aria-hidden="true" />
        Đăng ký
      </a>
      <a className={`landing-btn is-ghost is-${size}`} href="/login">
        <LogIn size={18} aria-hidden="true" />
        Đăng nhập
      </a>
    </div>
  );
}

/** Minh hoạ một lượt hỏi đáp có trích dẫn (trang trí, không phải dữ liệu thật). */
function ChatPreview() {
  return (
    <figure className="landing-preview">
      <div className="landing-preview-window" aria-hidden="true">
        <div className="landing-preview-bar">
          <span />
          <span />
          <span />
        </div>
        <div className="landing-preview-body">
          <p className="landing-bubble is-user">Điều kiện để được xét tốt nghiệp là gì?</p>
          <div className="landing-bubble is-bot">
            <p>
              Theo quy chế đào tạo, sinh viên được xét tốt nghiệp khi đáp ứng các điều kiện về tích
              luỹ tín chỉ và kết quả học tập <span className="landing-cite">[1]</span>…
            </p>
            <div className="landing-sources">
              <span className="landing-source">
                <span className="landing-cite">1</span>
                Quy chế đào tạo · Điều xét tốt nghiệp
              </span>
            </div>
          </div>
        </div>
      </div>
      <figcaption>Minh hoạ: câu trả lời luôn kèm trích dẫn tới văn bản nguồn.</figcaption>
    </figure>
  );
}

/** Trang giới thiệu tại `/`: CTA vào chat, đăng nhập, đăng ký; nội dung tiếng Việt. */
export default function LandingPage() {
  const session = useAuthSession();
  const { user } = session;

  return (
    <div className="landing-page">
      <a className="skip-link" href="#landing-main">
        Tới nội dung chính
      </a>
      <header className="landing-header">
        <div className="landing-container landing-header-inner">
          <a className="site-brand" href="/" aria-label="PTIT Chatbot — Trang chủ">
            <span className="site-brand-mark" aria-hidden="true">
              <Sparkles size={18} />
            </span>
            <span className="site-brand-name">PTIT Chatbot</span>
          </a>
          <nav className="landing-nav" aria-label="Các mục trên trang">
            <a href="#tinh-nang">Tính năng</a>
            <a href="#cach-hoat-dong">Cách hoạt động</a>
            <a href="#luu-y">Lưu ý</a>
          </nav>
          <div className="landing-header-actions">
            <ThemeToggle />
            {session.isAuthenticated ? (
              <>
                <span className="landing-user" title={user.email}>
                  <span className="landing-avatar" aria-hidden="true">
                    {userInitial(user)}
                  </span>
                  <span className="landing-user-name">{user.full_name}</span>
                </span>
                <a className="landing-btn is-primary is-sm" href="/chat">
                  Vào trò chuyện
                </a>
              </>
            ) : (
              <>
                <a className="landing-btn is-ghost is-sm landing-header-login" href="/login">
                  Đăng nhập
                </a>
                <a className="landing-btn is-primary is-sm" href="/register">
                  Đăng ký
                </a>
              </>
            )}
          </div>
        </div>
      </header>

      <main id="landing-main" tabIndex={-1}>
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-container landing-hero-grid">
            <div className="landing-hero-copy">
              <p className="landing-eyebrow">Trợ lý học vụ cho sinh viên PTIT</p>
              <h1 id="landing-title">Hỏi đáp quy chế và thủ tục, có trích dẫn nguồn</h1>
              <p className="landing-lead">
                PTIT Chatbot trả lời câu hỏi về quy chế đào tạo, học phí và thủ tục sinh viên dựa trên
                tài liệu chính thức đã được nạp vào hệ thống, kèm trích dẫn để bạn kiểm tra lại.
              </p>
              {session.isAuthenticated && (
                <p className="landing-greeting">
                  Xin chào, <strong>{user.full_name}</strong>. Lịch sử hội thoại của bạn đã sẵn sàng.
                </p>
              )}
              <HeroActions session={session} />
              {!session.isAuthenticated && (
                <p className="landing-hint">
                  Không cần tài khoản để hỏi. Đăng nhập để lưu lịch sử trên mọi thiết bị.
                </p>
              )}
            </div>
            <ChatPreview />
          </div>
        </section>

        <section className="landing-section" id="tinh-nang" aria-labelledby="features-title">
          <div className="landing-container">
            <div className="landing-section-head">
              <h2 id="features-title">Chatbot giúp được gì</h2>
              <p>Tra cứu nhanh thay vì lật từng trang quy chế — và vẫn biết câu trả lời lấy từ đâu.</p>
            </div>
            <ul className="landing-features">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="landing-card">
                  <span className="landing-card-icon" aria-hidden="true">
                    <Icon size={20} />
                  </span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section
          className="landing-section is-muted"
          id="cach-hoat-dong"
          aria-labelledby="how-title"
        >
          <div className="landing-container">
            <div className="landing-section-head">
              <h2 id="how-title">Cách hoạt động</h2>
              <p>
                Câu trả lời được xây dựng từ tài liệu, không phải từ trí nhớ chung của mô hình ngôn
                ngữ.
              </p>
            </div>
            <ol className="landing-steps">
              {STEPS.map(({ icon: Icon, title, text }, index) => (
                <li key={title} className="landing-step">
                  <span className="landing-step-index" aria-hidden="true">
                    {index + 1}
                  </span>
                  <div>
                    <h3>
                      <Icon size={18} aria-hidden="true" />
                      {title}
                    </h3>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="landing-source-note">
              <strong>Nguồn dữ liệu:</strong> các văn bản do quản trị viên hệ thống nạp vào kho tài
              liệu. Câu hỏi ngoài phạm vi học vụ có thể bị chatbot từ chối trả lời.
            </p>
          </div>
        </section>

        <section className="landing-section" id="luu-y" aria-labelledby="limits-title">
          <div className="landing-container">
            <div className="landing-limits">
              <div className="landing-limits-head">
                <span className="landing-card-icon is-warning" aria-hidden="true">
                  <TriangleAlert size={20} />
                </span>
                <h2 id="limits-title">Lưu ý khi sử dụng</h2>
              </div>
              <ul>
                {LIMITS.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="landing-section landing-final" aria-labelledby="final-title">
          <div className="landing-container landing-final-inner">
            <h2 id="final-title">
              {session.isAuthenticated ? "Tiếp tục cuộc trò chuyện" : "Sẵn sàng đặt câu hỏi?"}
            </h2>
            <HeroActions session={session} size="md" />
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <div className="landing-footer-brand">
            <strong>PTIT Chatbot</strong>
            <span>Trợ lý tra cứu học vụ dựa trên tài liệu, kèm trích dẫn nguồn.</span>
          </div>
          <nav className="landing-footer-links" aria-label="Liên kết cuối trang">
            <a href="/chat">Trò chuyện</a>
            {!session.isAuthenticated && <a href="/login">Đăng nhập</a>}
            {!session.isAuthenticated && <a href="/register">Đăng ký</a>}
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              <Github size={14} aria-hidden="true" />
              Mã nguồn
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
