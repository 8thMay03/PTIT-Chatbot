import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Loader2, MessageSquare, Pencil, Trash2, X } from "lucide-react";
import { API_BASE_URL } from "../api";
import Modal from "./Modal";
import { useToast } from "./Toast";

const DAY = 24 * 60 * 60 * 1000;

/** Gom hội thoại theo mốc thời gian để danh sách dài vẫn đọc được. */
function groupByRecency(conversations) {
  const now = Date.now();
  const groups = { today: [], week: [], older: [] };
  conversations.forEach((item) => {
    const stamp = new Date(item.updated_at || item.created_at).getTime();
    const age = now - stamp;
    if (Number.isNaN(age) || age < DAY) groups.today.push(item);
    else if (age < 7 * DAY) groups.week.push(item);
    else groups.older.push(item);
  });
  return [
    { key: "today", label: "Hôm nay", items: groups.today },
    { key: "week", label: "7 ngày qua", items: groups.week },
    { key: "older", label: "Cũ hơn", items: groups.older },
  ].filter((group) => group.items.length > 0);
}

export default function ConversationList({ activeId, onOpen, reloadToken }) {
  const toast = useToast();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingDelete, setPendingDelete] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const editInputRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/conversations?limit=50`);
      if (!response.ok) throw new Error("Máy chủ trả về lỗi.");
      const payload = await response.json();
      setConversations(payload.conversations ?? []);
    } catch (err) {
      setConversations([]);
      setError(
        err instanceof TypeError ? "Không kết nối được máy chủ." : "Không tải được lịch sử hội thoại."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, reloadToken]);

  useEffect(() => {
    if (editingId) editInputRef.current?.focus();
  }, [editingId]);

  const groups = useMemo(() => groupByRecency(conversations), [conversations]);

  async function submitRename(id) {
    const title = editTitle.trim();
    if (!title) {
      setEditingId(null);
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) throw new Error("Không đổi được tên hội thoại.");
      setConversations((current) =>
        current.map((item) => (item.id === id ? { ...item, title } : item))
      );
      setEditingId(null);
    } catch (err) {
      toast.error(err.message || "Không đổi được tên hội thoại.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${pendingDelete.id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Không xóa được hội thoại.");
      setConversations((current) => current.filter((item) => item.id !== pendingDelete.id));
      if (activeId === pendingDelete.id) onOpen?.(null);
      toast.success("Đã xóa hội thoại.");
      setPendingDelete(null);
    } catch (err) {
      toast.error(err.message || "Không xóa được hội thoại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sidebar-section conversation-section">
      <span className="sidebar-label">Hội thoại gần đây</span>

      {loading ? (
        <div className="conv-loading" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="conv-skeleton" />
          ))}
        </div>
      ) : error ? (
        <p className="conv-empty">{error}</p>
      ) : conversations.length === 0 ? (
        <p className="conv-empty">Chưa có hội thoại nào được lưu. Hãy đặt câu hỏi đầu tiên.</p>
      ) : (
        <div className="conv-groups">
          {groups.map((group) => (
            <div key={group.key} className="conv-group">
              <span className="conv-group-label">{group.label}</span>
              <ul className="conv-list">
                {group.items.map((item) => {
                  const isActive = item.id === activeId;
                  const isEditing = editingId === item.id;
                  const label = item.title?.trim() || "Hội thoại không tiêu đề";

                  return (
                    <li key={item.id} className={`conv-item ${isActive ? "active" : ""}`}>
                      {isEditing ? (
                        <form
                          className="conv-rename-form"
                          onSubmit={(e) => {
                            e.preventDefault();
                            submitRename(item.id);
                          }}
                        >
                          <label className="sr-only" htmlFor={`conv-rename-${item.id}`}>
                            Tên hội thoại
                          </label>
                          <input
                            id={`conv-rename-${item.id}`}
                            ref={editInputRef}
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Escape") setEditingId(null);
                            }}
                            maxLength={200}
                          />
                          <button type="submit" className="conv-icon-btn" disabled={busy} aria-label="Lưu tên">
                            {busy ? <Loader2 size={13} className="spin" /> : <Check size={13} />}
                          </button>
                          <button
                            type="button"
                            className="conv-icon-btn"
                            onClick={() => setEditingId(null)}
                            aria-label="Hủy đổi tên"
                          >
                            <X size={13} />
                          </button>
                        </form>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="conv-open-btn"
                            onClick={() => onOpen?.(item.id)}
                            aria-current={isActive ? "true" : undefined}
                            title={label}
                          >
                            <MessageSquare size={13} aria-hidden="true" />
                            <span className="conv-title">{label}</span>
                          </button>
                          <span className="conv-actions">
                            <button
                              type="button"
                              className="conv-icon-btn"
                              onClick={() => {
                                setEditingId(item.id);
                                setEditTitle(item.title || "");
                              }}
                              aria-label={`Đổi tên hội thoại ${label}`}
                            >
                              <Pencil size={12} />
                            </button>
                            <button
                              type="button"
                              className="conv-icon-btn is-danger"
                              onClick={() => setPendingDelete(item)}
                              aria-label={`Xóa hội thoại ${label}`}
                            >
                              <Trash2 size={12} />
                            </button>
                          </span>
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => !busy && setPendingDelete(null)}
        title="Xóa hội thoại?"
        description={
          pendingDelete
            ? `“${pendingDelete.title?.trim() || "Hội thoại không tiêu đề"}” cùng toàn bộ tin nhắn sẽ bị xóa vĩnh viễn.`
            : ""
        }
        icon={<Trash2 size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setPendingDelete(null)} disabled={busy}>
              Hủy
            </button>
            <button type="button" className="danger-btn" onClick={confirmDelete} disabled={busy}>
              {busy ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
              Xóa
            </button>
          </>
        }
      />
    </div>
  );
}
