import React, { useEffect, useId, useState } from "react";
import { ChevronDown, Loader2, Save } from "lucide-react";

/**
 * Thanh lưu dính đáy vùng nội dung, chỉ hiện khi form có thay đổi chưa lưu.
 *
 * `changes`: [{ key, label, from, to }] (chuỗi đã định dạng). Hủy thay đổi do form xử lý
 * (`onDiscard`, không gọi API); `onSave` gửi lên máy chủ.
 */
export default function SaveBar({ changes, onDiscard, onSave, saving = false, disabled = false }) {
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  const count = changes.length;

  useEffect(() => {
    if (count === 0) setExpanded(false);
  }, [count]);

  if (count === 0) return null;

  const summary = changes.map((change) => `${change.label} ${change.from}→${change.to}`).join(" · ");

  return (
    <div className="save-bar" role="region" aria-label="Thay đổi chưa lưu">
      {expanded && (
        <ul className="save-bar-list" id={listId}>
          {changes.map((change) => (
            <li key={change.key}>
              <span>{change.label}</span>
              <code>
                {change.from} → {change.to}
              </code>
            </li>
          ))}
        </ul>
      )}
      <div className="save-bar-main">
        <button
          type="button"
          className="save-bar-summary"
          aria-expanded={expanded}
          aria-controls={expanded ? listId : undefined}
          onClick={() => setExpanded((value) => !value)}
          title={summary}
        >
          <span className="save-bar-count">{count} thay đổi chưa lưu</span>
          <span className="save-bar-diff">{summary}</span>
          <ChevronDown size={14} className={`save-bar-chevron ${expanded ? "open" : ""}`} aria-hidden="true" />
        </button>
        <div className="save-bar-actions">
          <button type="button" className="ghost-btn" onClick={onDiscard} disabled={saving || disabled}>
            Hủy thay đổi
          </button>
          <button
            type="button"
            className="btn-primary-save"
            onClick={onSave}
            disabled={saving || disabled}
          >
            {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
            <span>{saving ? "Đang lưu..." : "Lưu"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
