import React from "react";
import { Laptop, MessageSquare, Quote, SendHorizontal, Smartphone, Sparkles } from "lucide-react";
import { SCOPE_TAGS } from "./content";

/**
 * Khối tính năng dạng bento (Figma node 2002:669): 1 thẻ rộng, rồi 2 hàng 2 thẻ.
 * Phần minh hoạ chỉ để trang trí (aria-hidden); nội dung đọc được nằm ở tiêu đề và
 * mô tả mỗi thẻ.
 */

function CardCopy({ title, children }) {
  return (
    <div className="lp-card-copy">
      <h3 className="lp-card-title">{title}</h3>
      <p className="lp-card-text">{children}</p>
    </div>
  );
}

function AnswerIllustration() {
  return (
    <div className="lp-answer-art" aria-hidden="true">
      <div className="lp-panel lp-panel-answer">
        <div className="lp-panel-head">
          <span className="lp-panel-logo">
            <Sparkles size={14} />
          </span>
          PTIT Chatbot
        </div>
        <p className="lp-panel-lead">Theo quy chế đào tạo, sinh viên được xét tốt nghiệp khi:</p>
        <ul className="lp-panel-list">
          <li>
            Tích luỹ đủ học phần và số tín chỉ của chương trình <span className="lp-cite">1</span>
          </li>
          <li>
            Đạt yêu cầu về kết quả học tập <span className="lp-cite">1</span>
          </li>
          <li>
            Hoàn thành các điều kiện khác theo quy định <span className="lp-cite">2</span>
          </li>
        </ul>
      </div>
      <div className="lp-panel lp-panel-sources">
        <p className="lp-panel-step">Nguồn trích dẫn</p>
        <ul className="lp-source-list">
          <li>
            <span className="lp-cite">1</span>Quy chế đào tạo
          </li>
          <li>
            <span className="lp-cite">2</span>Sổ tay sinh viên
          </li>
        </ul>
        <div className="lp-doc-sketch">
          <span />
          <span />
          <span />
          <span />
        </div>
      </div>
      <div className="lp-prompt-bubble">
        <p>Điều kiện để được xét tốt nghiệp là gì?</p>
        <div className="lp-prompt-bar">
          <span>
            <Quote size={13} /> Kèm trích dẫn
          </span>
          <SendHorizontal size={18} />
        </div>
      </div>
      <p className="lp-art-caption">Minh hoạ</p>
    </div>
  );
}

function ScopeIllustration() {
  return (
    <div className="lp-tags-art" aria-hidden="true">
      <span className="lp-tags-shadow" />
      {SCOPE_TAGS.map(({ label, tone, style }) => (
        <span
          key={label}
          className={`lp-tag is-${tone}`}
          style={{ left: style.left, bottom: style.bottom, "--tag-rotate": style.rotate }}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function CitationIllustration() {
  return (
    <div className="lp-cite-art" aria-hidden="true">
      <span className="lp-cite-glow" />
      <span className="lp-cite-line" />
      <div className="lp-cite-stack">
        <span className="lp-cite-chip">
          <span className="lp-cite">1</span>Quy chế đào tạo
        </span>
        <span className="lp-cite-chip">
          <span className="lp-cite">2</span>Sổ tay sinh viên
        </span>
        <span className="lp-cite-chip is-faded">
          <span className="lp-cite">3</span>Văn bản đã nạp
        </span>
      </div>
    </div>
  );
}

function ContextIllustration() {
  return (
    <div className="lp-tray" aria-hidden="true">
      <div className="lp-tray-inner">
        <p className="lp-mini-bubble is-user">Học bổng khuyến khích xét theo tiêu chí nào?</p>
        <p className="lp-mini-bubble is-bot">
          Dựa trên kết quả học tập và rèn luyện của học kỳ <span className="lp-cite">1</span>
        </p>
        <p className="lp-mini-bubble is-user">Còn điều kiện rèn luyện thì sao?</p>
      </div>
    </div>
  );
}

function HistoryIllustration() {
  return (
    <div className="lp-history-art" aria-hidden="true">
      <div className="lp-history-panel">
        <div className="lp-history-devices">
          <span>
            <Laptop size={15} /> Máy tính
          </span>
          <span>
            <Smartphone size={15} /> Điện thoại
          </span>
        </div>
        <p className="lp-history-group">Hôm nay</p>
        <p className="lp-history-item">
          <MessageSquare size={14} /> Học phí học kỳ này
        </p>
        <p className="lp-history-item">
          <MessageSquare size={14} /> Điều kiện xét tốt nghiệp
        </p>
        <p className="lp-history-group">7 ngày qua</p>
        <p className="lp-history-item">
          <MessageSquare size={14} /> Đăng ký học phần
        </p>
      </div>
    </div>
  );
}

export default function FeatureBento() {
  return (
    <ul className="lp-bento">
      <li className="lp-card lp-card-wide">
        <CardCopy title="Hỏi gì về học vụ cũng được">
          Gõ câu hỏi như khi hỏi phòng đào tạo — chatbot tìm trong quy chế, sổ tay sinh viên và trả lời
          rõ từng ý.
        </CardCopy>
        <AnswerIllustration />
      </li>
      <li className="lp-card lp-card-scope">
        <CardCopy title="Đúng phạm vi học vụ">
          Tập trung vào quy chế, học phí, học bổng, thi cử, rèn luyện và thủ tục sinh viên. Câu hỏi ngoài
          phạm vi được từ chối thay vì trả lời bừa.
        </CardCopy>
        <ScopeIllustration />
      </li>
      <li className="lp-card lp-card-cite">
        <CardCopy title="Trích dẫn tới điều, khoản">
          Mỗi ý trong câu trả lời gắn số trích dẫn; bấm vào để xem đoạn văn bản gốc.
        </CardCopy>
        <CitationIllustration />
      </li>
      <li className="lp-card lp-card-context">
        <CardCopy title="Hiểu ngữ cảnh câu hỏi">
          Hỏi tiếp dựa trên câu trước mà không cần nhắc lại toàn bộ; chatbot dùng các lượt gần nhất trong
          cùng hội thoại.
        </CardCopy>
        <ContextIllustration />
      </li>
      <li className="lp-card lp-card-history">
        <CardCopy title="Lịch sử theo tài khoản">
          Không cần tài khoản vẫn hỏi được ngay. Đăng nhập để lịch sử hội thoại theo bạn trên mọi thiết
          bị.
        </CardCopy>
        <HistoryIllustration />
      </li>
    </ul>
  );
}
