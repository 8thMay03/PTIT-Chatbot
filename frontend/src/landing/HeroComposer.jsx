import React, { useId, useState } from "react";
import { CornerUpRight, Quote, SendHorizontal } from "lucide-react";
import { CHAT_PATH, chatPathWithQuestion } from "../lib/appRoute";
import { transitionTo } from "./motion/pixelTransition";
import { COMPOSER_SUGGESTION, COMPOSER_TOPICS } from "./content";

/**
 * Khung soạn câu hỏi ở hero (Figma node 2002:475). Gửi mở trang chat với câu hỏi
 * điền sẵn (`/chat?q=`) qua pixel transition; trang chat không tự gửi để người dùng
 * xem lại trước.
 */
export default function HeroComposer() {
  const [question, setQuestion] = useState("");
  const inputId = useId();
  const hintId = useId();

  function submit(event) {
    event?.preventDefault();
    const text = question.trim();
    transitionTo(text ? chatPathWithQuestion(text) : CHAT_PATH);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) submit(event);
  }

  return (
    <form className="lp-composer" onSubmit={submit} aria-label="Đặt câu hỏi cho PTIT Chatbot">
      <span className="lp-composer-glow" aria-hidden="true" />
      <div className="lp-composer-chips" role="group" aria-label="Chủ đề gợi ý">
        {COMPOSER_TOPICS.map(({ label, icon: Icon, question: suggestion }) => (
          <button
            key={label}
            type="button"
            className="lp-chip"
            data-pulse
            onClick={() => setQuestion(suggestion)}
            aria-label={`Điền câu hỏi về ${label.toLowerCase()}`}
          >
            <Icon size={16} aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
      <div className="lp-composer-box">
        <button
          type="button"
          className="lp-composer-suggestion"
          onClick={() => setQuestion(COMPOSER_SUGGESTION)}
        >
          <span className="lp-composer-suggestion-text">{COMPOSER_SUGGESTION}</span>
          <CornerUpRight size={16} aria-hidden="true" />
        </button>
        <label className="sr-only" htmlFor={inputId}>
          Câu hỏi của bạn
        </label>
        <textarea
          id={inputId}
          className="lp-composer-input"
          rows={3}
          maxLength={1000}
          placeholder="Hỏi bất cứ điều gì về quy chế, học phí, thủ tục…"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-describedby={hintId}
        />
        <div className="lp-composer-bar">
          <span className="lp-composer-hint" id={hintId}>
            <Quote size={15} aria-hidden="true" />
            Trả lời kèm trích dẫn nguồn
          </span>
          <button
            type="submit"
            className="lp-composer-send"
            aria-label="Gửi câu hỏi và mở trang trò chuyện"
            data-magnetic
            data-pulse
          >
            <SendHorizontal size={20} aria-hidden="true" />
          </button>
        </div>
      </div>
    </form>
  );
}
