import React, { useId, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { STEPS } from "./content";
import SplitWords from "../lib/motion/SplitWords";

/**
 * Carousel "Cách hoạt động" theo bố cục khối lời chứng thực của thiết kế
 * (Figma node 2002:940): nút trước/sau, nội dung lớn kiểu trích dẫn, dải ô chọn
 * kèm chấm chỉ vị trí. Không tự chuyển slide. Đổi bước thì nội dung dựng lại
 * (`key`) để chữ trượt vào lại từng từ.
 */
export default function StepsCarousel() {
  const [index, setIndex] = useState(0);
  const slideId = useId();
  const step = STEPS[index];
  const StepIcon = step.icon;
  const total = STEPS.length;

  const go = (next) => setIndex((next + total) % total);

  return (
    <div
      className="lp-carousel"
      data-reveal="up"
      data-tilt="0.35"
      role="region"
      aria-roledescription="carousel"
      aria-label="Các bước PTIT Chatbot trả lời câu hỏi"
    >
      <button
        type="button"
        className="lp-carousel-arrow is-soft"
        data-magnetic
        data-pulse
        onClick={() => go(index - 1)}
        aria-label="Bước trước"
        aria-controls={slideId}
      >
        <ArrowLeft size={22} aria-hidden="true" />
      </button>

      <div className="lp-carousel-body">
        <div
          className="lp-carousel-slide"
          id={slideId}
          role="group"
          aria-roledescription="slide"
          aria-label={`Bước ${index + 1} trên ${total}`}
          aria-live="polite"
        >
          <p className="lp-carousel-quote" key={`quote-${index}`}>
            <span className="lp-quote-mark is-open" aria-hidden="true">
              “
            </span>
            <SplitWords text={step.text} />
            <span className="lp-quote-mark is-close" aria-hidden="true">
              ”
            </span>
          </p>
          <div className="lp-carousel-person" key={`person-${index}`}>
            <span className="lp-carousel-avatar" aria-hidden="true">
              <StepIcon size={26} />
            </span>
            <span className="lp-carousel-person-copy">
              <strong>{step.title}</strong>
              <span>
                Bước {index + 1} / {total}
              </span>
            </span>
          </div>
        </div>

        <div className="lp-carousel-thumbs" role="group" aria-label="Chọn bước">
          {STEPS.map(({ title, icon: Icon }, stepIndex) => (
            <button
              key={title}
              type="button"
              className={`lp-carousel-thumb ${stepIndex === index ? "is-active" : ""}`}
              onClick={() => setIndex(stepIndex)}
              aria-label={`Bước ${stepIndex + 1}: ${title}`}
              aria-current={stepIndex === index ? "step" : undefined}
              aria-controls={slideId}
            >
              <span className="lp-carousel-thumb-tile" aria-hidden="true">
                <Icon size={18} />
              </span>
              <span className="lp-carousel-dot" aria-hidden="true" />
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        className="lp-carousel-arrow is-solid"
        data-magnetic
        data-pulse
        onClick={() => go(index + 1)}
        aria-label="Bước tiếp theo"
        aria-controls={slideId}
      >
        <ArrowRight size={22} aria-hidden="true" />
      </button>
    </div>
  );
}
