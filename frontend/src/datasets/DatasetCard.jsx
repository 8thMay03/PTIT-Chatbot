import React, { useState } from "react";
import { Database, MoreVertical } from "lucide-react";
import { formatDate, formatSize } from "../lib/format";

export default function DatasetCard({ dataset, onOpen, onEdit, onDelete, onToggle, toggling }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const pending = dataset.pending_count ?? 0;

  return (
    <article className="dataset-card" aria-label={`Dataset ${dataset.name}`}>
      <button type="button" className="dataset-card-main" onClick={onOpen} title={`Mở ${dataset.name}`}>
        <span className="dataset-card-icon" aria-hidden="true">
          <Database size={18} />
        </span>
        <span className="dataset-card-body">
          <strong className="dataset-card-name">{dataset.name}</strong>
          {dataset.description && <small className="dataset-card-desc">{dataset.description}</small>}
          <span className="dataset-card-stats">
            {dataset.document_count ?? 0} tài liệu · {dataset.chunk_count ?? 0} đoạn
          </span>
          {dataset.size_bytes != null && (
            <span className="dataset-card-size">{formatSize(dataset.size_bytes)}</span>
          )}
          {pending > 0 && <span className="dataset-card-pending">{pending} chờ chia đoạn</span>}
          <span className="dataset-card-meta">
            <span className={`dataset-status-dot ${dataset.enabled ? "on" : "off"}`} aria-hidden="true" />
            {dataset.enabled ? "Đang dùng khi trả lời" : "Đã tắt"} · {formatDate(dataset.updated_at)}
          </span>
        </span>
      </button>
      <div className="dataset-card-menu">
        <button
          type="button"
          className="dataset-menu-btn"
          aria-label={`Tùy chọn cho ${dataset.name}`}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <MoreVertical size={16} />
        </button>
        {menuOpen && (
          <div className="dataset-menu-dropdown" role="menu">
            <button type="button" role="menuitem" onClick={() => { setMenuOpen(false); onEdit?.(); }}>
              Đổi tên &amp; mô tả
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => { setMenuOpen(false); onToggle?.(); }}
              disabled={toggling}
            >
              {dataset.enabled ? "Tắt" : "Bật"}
            </button>
            {!dataset.is_default && (
              <button
                type="button"
                role="menuitem"
                className="is-danger"
                onClick={() => { setMenuOpen(false); onDelete?.(); }}
              >
                Xóa
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
