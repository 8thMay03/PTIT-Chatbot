import React from "react";
import { ChevronRight, Cpu, Palette, SlidersHorizontal } from "lucide-react";
import {
  ADMIN_ANSWER_SECTIONS,
  ADMIN_MODEL_SECTIONS,
  adminRouteHash,
} from "../lib/appRoute";

/**
 * Ba nhóm của trang Cài đặt quản trị. Nhóm "Hệ thống trả lời" là một form chia
 * theo bước; "Mô hình" là ba trang riêng; "Cá nhân" là tùy chọn giao diện.
 */
export const SETTINGS_NAV_GROUPS = [
  {
    id: "answer",
    label: "Hệ thống trả lời",
    items: [
      { key: "retrieval", label: "Truy xuất", hint: "Top-K, tỷ trọng, mở rộng câu hỏi" },
      { key: "reranker", label: "Xếp hạng lại", hint: "Bật/tắt và mô hình xếp hạng" },
      { key: "gate", label: "Ngưỡng tin cậy", hint: "Khi nào trả lời hay từ chối" },
      { key: "generation", label: "Sinh câu trả lời", hint: "Temperature, thời gian chờ" },
    ],
  },
  {
    id: "models",
    label: "Mô hình",
    items: [
      { key: "models-llm", label: "Mô hình ngôn ngữ", short: "Ngôn ngữ", hint: "LLM dùng để sinh câu trả lời" },
      { key: "models-embedding", label: "Mô hình nhúng", short: "Nhúng", hint: "Embedding cho tìm kiếm ngữ nghĩa" },
      { key: "models-reranker", label: "Mô hình xếp hạng", short: "Xếp hạng", hint: "Reranker cho danh sách đoạn" },
    ],
  },
  {
    id: "personal",
    label: "Cá nhân",
    items: [{ key: "appearance", label: "Giao diện", hint: "Chế độ sáng, tối, theo hệ thống" }],
  },
];

export const SETTINGS_ITEM_LABELS = Object.fromEntries(
  SETTINGS_NAV_GROUPS.flatMap((group) => group.items.map((item) => [item.key, item.label]))
);

/** Tab trên cùng: mỗi tab mở mục đầu của nhóm. */
const SETTINGS_TABS = [
  { group: "answer", label: "Hệ thống trả lời", section: "retrieval", Icon: SlidersHorizontal },
  { group: "models", label: "Mô hình", section: "models-llm", Icon: Cpu },
  { group: "personal", label: "Giao diện", section: "appearance", Icon: Palette },
];

/** Nhóm của một mục; `null` (trang `#settings`) thuộc "Hệ thống trả lời". */
export function settingsGroupOf(section) {
  if (section === null || ADMIN_ANSWER_SECTIONS.includes(section)) return "answer";
  if (ADMIN_MODEL_SECTIONS.includes(section)) return "models";
  return "personal";
}

export function settingsHref(section) {
  return `#${adminRouteHash({ view: "settings", section })}`;
}

export function DirtyDot() {
  return (
    <span
      className="settings-dirty-dot"
      role="img"
      aria-label="Có thay đổi chưa lưu"
      title="Có thay đổi chưa lưu"
    />
  );
}

/** Link mục cài đặt: giữ `href` để mở tab mới được, bấm thường thì đổi route tại chỗ. */
function navClick(onSelect, key) {
  return (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1) return;
    event.preventDefault();
    onSelect?.(key);
  };
}

/** Tab ba nhóm (desktop ≥1024px). */
export function SettingsTabs({ group, dirty = false, onSelect }) {
  return (
    <nav className="settings-tabs" aria-label="Nhóm cài đặt">
      {SETTINGS_TABS.map(({ group: id, label, section, Icon }) => {
        const active = group === id;
        return (
          <a
            key={id}
            className={`settings-tab ${active ? "is-active" : ""}`}
            href={settingsHref(section)}
            aria-current={active ? "page" : undefined}
            data-settings-tab={id}
            onClick={navClick(onSelect, section)}
          >
            <Icon size={16} aria-hidden="true" />
            <span>{label}</span>
            {id === "answer" && dirty && <DirtyDot />}
          </a>
        );
      })}
    </nav>
  );
}

/** Thanh chọn loại mô hình trong tab "Mô hình" (desktop). */
export function ModelKindNav({ activeKey, onSelect }) {
  const items = SETTINGS_NAV_GROUPS.find((group) => group.id === "models").items;
  return (
    <nav className="settings-kind-nav" aria-label="Loại mô hình">
      {items.map((item) => {
        const active = activeKey === item.key;
        return (
          <a
            key={item.key}
            className={`settings-kind-item ${active ? "is-active" : ""}`}
            href={settingsHref(item.key)}
            aria-current={active ? "page" : undefined}
            data-settings-nav={item.key}
            title={item.hint}
            onClick={navClick(onSelect, item.key)}
          >
            {item.short}
          </a>
        );
      })}
    </nav>
  );
}

/**
 * Danh sách mục toàn màn hình (mobile &lt;1024px). `summaries[key]` (nhãn giá trị
 * đang dùng) thay cho dòng gợi ý khi có.
 */
export function SettingsIndex({ dirtySections = [], summaries = {}, onSelect }) {
  return (
    <nav className="settings-index" aria-label="Danh sách mục cài đặt">
      <h2 className="settings-index-title">Cài đặt</h2>
      {SETTINGS_NAV_GROUPS.map((group) => (
        <section className="settings-index-group" key={group.id} aria-labelledby={`settings-index-${group.id}`}>
          <h3 className="settings-index-group-title" id={`settings-index-${group.id}`}>
            {group.label}
          </h3>
          <div className="settings-index-card">
            {group.items.map((item) => {
              const summary = summaries[item.key];
              return (
                <button
                  key={item.key}
                  type="button"
                  className="settings-index-item"
                  data-settings-index={item.key}
                  onClick={() => onSelect?.(item.key)}
                >
                  <span className="settings-index-copy">
                    <strong>{item.label}</strong>
                    {summary?.length ? (
                      <small className="settings-index-summary">{summary.join(" · ")}</small>
                    ) : (
                      <small>{item.hint}</small>
                    )}
                  </span>
                  {dirtySections.includes(item.key) ? <DirtyDot /> : <ChevronRight size={16} aria-hidden="true" />}
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </nav>
  );
}
