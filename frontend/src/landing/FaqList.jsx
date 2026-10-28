import React, { useId, useState } from "react";
import { Plus } from "lucide-react";
import { FAQ } from "./content";

/** FAQ dạng accordion (Figma node 2002:996): mỗi câu là một nút mở/đóng câu trả lời. */
export default function FaqList() {
  const [openIndex, setOpenIndex] = useState(null);
  const baseId = useId();

  return (
    <ol className="lp-faq-list">
      {FAQ.map(({ question, answer }, index) => {
        const open = openIndex === index;
        const buttonId = `${baseId}-q${index}`;
        const panelId = `${baseId}-a${index}`;
        return (
          <li key={question} className={`lp-faq-item ${open ? "is-open" : ""}`}>
            <h3 className="lp-faq-question">
              <button
                type="button"
                id={buttonId}
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpenIndex(open ? null : index)}
              >
                <span>
                  {index + 1}. {question}
                </span>
                <Plus className="lp-faq-icon" size={28} strokeWidth={1.5} aria-hidden="true" />
              </button>
            </h3>
            <div
              className="lp-faq-answer"
              id={panelId}
              role="region"
              aria-labelledby={buttonId}
              hidden={!open}
            >
              <p>{answer}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
