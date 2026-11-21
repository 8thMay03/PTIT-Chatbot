import React from "react";
import { navClick, settingsHref } from "../settings/SettingsNav";
import { activeModelSummary } from "./activeModels";
import { KIND_ORDER } from "./catalog";
import { KIND_ICONS, StatusPill } from "./fields";

export const KIND_STAGE_LABELS = {
  llm: "Sinh câu trả lời",
  embedding: "Nhúng văn bản",
  reranker: "Xếp hạng lại",
};

/**
 * Ba thẻ khâu đầu tab Mô hình: mỗi thẻ là link `#settings/models-<loại>`, hiện mô hình
 * đang dùng và trạng thái của khâu đó. Thay thanh Ngôn ngữ / Nhúng / Xếp hạng cũ.
 */
export default function ModelKindCards({ activeKind, registry, config, onSelect }) {
  return (
    <nav className="mdl-kinds" aria-label="Loại mô hình">
      {KIND_ORDER.map((kind) => {
        const section = `models-${kind}`;
        const active = kind === activeKind;
        const summary = activeModelSummary(kind, registry, config);
        const Icon = KIND_ICONS[kind];
        return (
          <a
            key={kind}
            className={`mdl-kind ${active ? "is-active" : ""}`}
            href={settingsHref(section)}
            aria-current={active ? "page" : undefined}
            data-settings-nav={section}
            onClick={navClick(onSelect, section)}
          >
            <span className="mdl-kind-label">
              <span className="mdl-kind-icon" aria-hidden="true">
                <Icon size={14} />
              </span>
              {KIND_STAGE_LABELS[kind]}
            </span>
            <span className="mdl-kind-head">
              <strong className="mdl-kind-name">{summary?.name ?? "—"}</strong>
              {summary && <StatusPill tone={summary.status.tone}>{summary.status.label}</StatusPill>}
            </span>
            <span className="mdl-kind-meta">{summary?.meta || " "}</span>
          </a>
        );
      })}
    </nav>
  );
}
