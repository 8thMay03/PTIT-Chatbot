import React from "react";
import { ArrowUpDown, CheckCircle2, MessageSquareText, Search, ShieldCheck, UserRound } from "lucide-react";
import { DirtyDot, settingsHref } from "./SettingsNav";

const STEPS = [
  { key: "retrieval", label: "Truy xuất", Icon: Search },
  { key: "reranker", label: "Xếp hạng lại", Icon: ArrowUpDown },
  { key: "gate", label: "Ngưỡng tin cậy", Icon: ShieldCheck },
  { key: "generation", label: "Sinh câu trả lời", Icon: MessageSquareText },
];

/**
 * Dải bốn bước của "Hệ thống trả lời" theo đúng thứ tự xử lý câu hỏi. Mỗi bước
 * hiện giá trị nháp đang dùng; bấm bước nào thì form của bước đó hiện bên dưới.
 */
export default function PipelineSteps({ activeKey, summaries = {}, dirtySections = [], onSelect }) {
  return (
    <nav className="pipeline-steps" aria-label="Các bước trả lời câu hỏi">
      <span className="pipeline-end" aria-hidden="true">
        <span className="pipeline-end-dot">
          <UserRound size={15} />
        </span>
        Câu hỏi
      </span>
      <ol className="pipeline-list">
        {STEPS.map(({ key, label, Icon }, index) => {
          const active = activeKey === key;
          const dirty = dirtySections.includes(key);
          return (
            <li key={key} className="pipeline-item">
              <a
                className={`pipeline-step ${active ? "is-active" : ""}`}
                href={settingsHref(key)}
                aria-current={active ? "step" : undefined}
                data-settings-nav={key}
                onClick={(event) => {
                  if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1) return;
                  event.preventDefault();
                  onSelect?.(key);
                }}
              >
                <span className="pipeline-step-top">
                  <span className="pipeline-step-index">Bước {index + 1}</span>
                  {dirty && <DirtyDot />}
                </span>
                <span className="pipeline-step-title">
                  <span className="pipeline-step-icon" aria-hidden="true">
                    <Icon size={15} />
                  </span>
                  {label}
                </span>
                <span className="pipeline-step-chips">
                  {(summaries[key] ?? []).map((chip) => (
                    <span key={chip} className="pipeline-chip">
                      {chip}
                    </span>
                  ))}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
      <span className="pipeline-end" aria-hidden="true">
        <span className="pipeline-end-dot">
          <CheckCircle2 size={15} />
        </span>
        Câu trả lời
      </span>
    </nav>
  );
}
