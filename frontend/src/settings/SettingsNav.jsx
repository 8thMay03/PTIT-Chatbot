import React from "react";
import { ChevronRight } from "lucide-react";
import {
  ADMIN_ANSWER_SECTIONS,
  adminRouteHash,
} from "../lib/appRoute";

/**
 * Ba nhóm của trang Cài đặt quản trị. Nhóm "Hệ thống trả lời" là một form nhiều
 * anchor; "Mô hình" là ba trang riêng; "Cá nhân" là tùy chọn giao diện.
 */
export const SETTINGS_NAV_GROUPS = [
  {
    id: "answer",
    label: "Hệ thống trả lời",
    items: [
      {
        key: "retrieval",
        label: "Truy xuất",
        hint: "Top-K, tỷ trọng, mở rộng câu hỏi",
        anchor: true,
      },
      {
        key: "reranker",
        label: "Xếp hạng lại",
        hint: "Bật/tắt và mô hình xếp hạng",
        anchor: true,
      },
      {
        key: "gate",
        label: "Ngưỡng tin cậy",
        hint: "Khi nào trả lời hay từ chối",
        anchor: true,
      },
      {
        key: "generation",
        label: "Sinh câu trả lời",
        hint: "Temperature, thời gian chờ",
        anchor: true,
      },
    ],
  },
  {
    id: "models",
    label: "Mô hình",
    items: [
      { key: "models-llm", label: "Mô hình ngôn ngữ", hint: "LLM dùng để sinh câu trả lời" },
      { key: "models-embedding", label: "Mô hình nhúng", hint: "Embedding cho tìm kiếm ngữ nghĩa" },
      { key: "models-reranker", label: "Mô hình xếp hạng", hint: "Reranker cho danh sách đoạn" },
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

export function settingsHref(section) {
  return `#${adminRouteHash({ view: "settings", section })}`;
}

function DirtyDot() {
  return (
    <span
      className="settings-dirty-dot"
      role="img"
      aria-label="Có thay đổi chưa lưu"
      title="Có thay đổi chưa lưu"
    />
  );
}

/** Cột danh mục cố định bên trái (desktop ≥1024px). */
export function SettingsSidebar({ activeKey, dirtySections = [], onSelect }) {
  return (
    <nav className="settings-nav" aria-label="Danh mục cài đặt">
      <h1 className="settings-nav-title" id="settings-title">
        Cài đặt
      </h1>
      {SETTINGS_NAV_GROUPS.map((group) => (
        <div className="settings-nav-group" key={group.id}>
          <h2 className="settings-nav-group-title">{group.label}</h2>
          {group.items.map((item) => {
            const active = activeKey === item.key;
            const dirty = dirtySections.includes(item.key);
            return (
              <a
                key={item.key}
                className={`settings-nav-item ${item.anchor ? "is-sub" : ""} ${active ? "is-active" : ""}`}
                href={settingsHref(item.key)}
                aria-current={
                  active
                    ? ADMIN_ANSWER_SECTIONS.includes(item.key)
                      ? "location"
                      : "page"
                    : undefined
                }
                data-settings-nav={item.key}
                onClick={(event) => {
                  event.preventDefault();
                  onSelect?.(item.key);
                }}
              >
                <span className="settings-nav-label">{item.label}</span>
                {dirty && <DirtyDot />}
              </a>
            );
          })}
        </div>
      ))}
      <p className="settings-nav-hint">
        Mỗi mục có địa chỉ riêng, ví dụ <code>#settings/gate</code>.
      </p>
    </nav>
  );
}

/** Danh sách mục toàn màn hình (mobile &lt;1024px). */
export function SettingsIndex({ dirtySections = [], onSelect }) {
  return (
    <nav className="settings-index" aria-label="Danh sách mục cài đặt">
      <h2 className="settings-index-title">Cài đặt</h2>
      {SETTINGS_NAV_GROUPS.map((group) => (
        <section className="settings-index-group" key={group.id} aria-labelledby={`settings-index-${group.id}`}>
          <h3 className="settings-index-group-title" id={`settings-index-${group.id}`}>
            {group.label}
          </h3>
          <div className="settings-index-card">
            {group.items.map((item) => (
              <button
                key={item.key}
                type="button"
                className="settings-index-item"
                data-settings-index={item.key}
                onClick={() => onSelect?.(item.key)}
              >
                <span className="settings-index-copy">
                  <strong>{item.label}</strong>
                  <small>{item.hint}</small>
                </span>
                {dirtySections.includes(item.key) ? <DirtyDot /> : <ChevronRight size={16} aria-hidden="true" />}
              </button>
            ))}
          </div>
        </section>
      ))}
    </nav>
  );
}
