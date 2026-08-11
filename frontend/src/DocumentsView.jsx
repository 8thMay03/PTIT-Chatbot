import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Download,
  FileText,
  Files,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";

const ACCEPTED_TYPES = ".md,.txt,text/markdown,text/plain";

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function formatSize(bytes) {
  if (bytes == null || Number.isNaN(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  return fallback;
}

export default function DocumentsView({ onChanged }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [notice, setNotice] = useState("");
  const fileRef = useRef(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return documents;
    return documents.filter((doc) =>
      [doc.title, doc.file_name, doc.file_type].filter(Boolean).some((value) => value.toLowerCase().includes(needle))
    );
  }, [documents, query]);

  const selected = documents.find((doc) => doc.id === selectedId) || null;

  async function loadDocuments() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) throw new Error("Không tải được danh sách tài liệu.");
      const payload = await response.json();
      setDocuments(payload.documents ?? []);
    } catch (err) {
      setError(err.message || "Không tải được danh sách tài liệu.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    fetch(`${API_BASE_URL}/documents/${selectedId}`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length || uploading) return;

    setUploading(true);
    setError("");
    const failures = [];
    let uploaded = 0;

    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        const response = await fetch(`${API_BASE_URL}/documents`, { method: "POST", body: form });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          failures.push(`${file.name}: ${apiError(payload, "không tải lên được")}`);
          continue;
        }
        uploaded += 1;
        setSelectedId(payload.id);
      } catch {
        failures.push(`${file.name}: không kết nối được máy chủ`);
      }
    }

    await loadDocuments();
    onChanged?.();
    setUploading(false);

    if (uploaded && !failures.length) {
      setNotice(`Đã nạp ${uploaded} tài liệu vào kho tri thức.`);
    } else if (uploaded) {
      setNotice(`Đã nạp ${uploaded} tài liệu. Một số file bị bỏ qua.`);
      setError(failures.join(" · "));
    } else {
      setError(failures.join(" · ") || "Không tải lên được tài liệu.");
    }
  }

  async function confirmDelete() {
    if (!pendingDelete || deleting) return;
    setDeleting(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${pendingDelete.id}`, { method: "DELETE" });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(apiError(payload, "Không xóa được tài liệu."));
      }
      if (selectedId === pendingDelete.id) {
        setSelectedId(null);
        setDetail(null);
      }
      setPendingDelete(null);
      setNotice(`Đã xóa “${pendingDelete.title || pendingDelete.file_name}”.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      setError(err.message || "Không xóa được tài liệu.");
    } finally {
      setDeleting(false);
    }
  }

  async function reindexAll() {
    if (reindexing) return;
    setReindexing(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/ingest`, { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload, "Không nạp lại được kho tri thức."));
      setNotice(`Đã nạp lại ${payload.documents ?? 0} tài liệu · ${payload.chunks ?? 0} đoạn.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      setError(err.message || "Không nạp lại được kho tri thức.");
    } finally {
      setReindexing(false);
    }
  }

  async function downloadDocument(doc) {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${doc.id}/file`);
      if (!response.ok) throw new Error("Không tải được file nguồn.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = doc.file_name || "tai-lieu.txt";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Không tải được file nguồn.");
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDragOver(false);
    uploadFiles(event.dataTransfer.files);
  }

  return (
    <section className="docs-screen">
      <header className="docs-header">
        <div>
          <h2>Quản lý tài liệu</h2>
          <p>Tải lên, xem và xóa các file Markdown/TXT đã nạp vào chatbot.</p>
        </div>
        <div className="docs-header-actions">
          <button className="ghost-btn" onClick={reindexAll} disabled={reindexing || uploading}>
            {reindexing ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
            Nạp lại kho tri thức
          </button>
          <button className="primary-btn" onClick={() => fileRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 size={16} className="spin" /> : <Upload size={16} />}
            Tải lên
          </button>
        </div>
      </header>

      <div className={`docs-body ${selected ? "has-detail" : ""}`}>
        <div className="docs-main">
          <label
            className={`docs-dropzone ${dragOver ? "is-over" : ""} ${uploading ? "is-busy" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED_TYPES}
              multiple
              hidden
              onChange={(event) => {
                uploadFiles(event.target.files);
                event.target.value = "";
              }}
            />
            <span className="docs-drop-icon">
              <Upload size={20} />
            </span>
            <strong>Kéo thả tài liệu vào đây</strong>
            <span>Hỗ trợ .md và .txt · tối đa 10MB · file trùng tên sẽ được cập nhật</span>
          </label>

          <div className="docs-toolbar">
            <div className="docs-search">
              <Search size={16} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm theo tên tài liệu..."
              />
            </div>
            <span className="docs-count">
              {loading ? "Đang tải..." : `${filtered.length}/${documents.length} tài liệu`}
            </span>
          </div>

          {notice && (
            <div className="docs-banner success">
              <Files size={15} />
              <span>{notice}</span>
              <button className="text-btn" onClick={() => setNotice("")} aria-label="Đóng thông báo">
                <X size={14} />
              </button>
            </div>
          )}
          {error && (
            <div className="docs-banner error">
              <AlertTriangle size={15} />
              <span>{error}</span>
              <button className="text-btn" onClick={() => setError("")} aria-label="Đóng lỗi">
                <X size={14} />
              </button>
            </div>
          )}

          {loading ? (
            <div className="docs-empty">
              <Loader2 size={22} className="spin" />
              <p>Đang tải danh sách tài liệu...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="docs-empty">
              <FileText size={28} />
              <h3>{documents.length === 0 ? "Chưa có tài liệu nào" : "Không tìm thấy tài liệu"}</h3>
              <p>
                {documents.length === 0
                  ? "Tải lên file .md hoặc .txt để chatbot có thể trả lời dựa trên nội dung đó."
                  : "Thử từ khóa khác hoặc xóa bộ lọc tìm kiếm."}
              </p>
            </div>
          ) : (
            <div className="docs-list">
              {filtered.map((doc) => (
                <article
                  key={doc.id}
                  className={`doc-card ${selectedId === doc.id ? "is-active" : ""}`}
                  onClick={() => setSelectedId(doc.id)}
                >
                  <div className="doc-icon">
                    <FileText size={18} />
                  </div>
                  <div className="doc-meta">
                    <h3>{doc.title}</h3>
                    <p>
                      {doc.file_name}
                      <span className="dot" />
                      {(doc.file_type || "txt").toUpperCase()}
                      <span className="dot" />
                      {doc.chunk_count} đoạn
                      <span className="dot" />
                      {formatSize(doc.size_bytes)}
                    </p>
                    <span className="doc-time">Cập nhật {formatDate(doc.updated_at)}</span>
                  </div>
                  <div className="doc-actions">
                    <button
                      className="icon-btn"
                      title="Tải xuống"
                      aria-label={`Tải xuống ${doc.file_name}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        downloadDocument(doc);
                      }}
                    >
                      <Download size={16} />
                    </button>
                    <button
                      className="icon-btn danger"
                      title="Xóa"
                      aria-label={`Xóa ${doc.file_name}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        setPendingDelete(doc);
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <aside className="docs-detail">
            <div className="docs-detail-head">
              <div>
                <span className="docs-detail-label">Xem trước</span>
                <h3>{selected.title}</h3>
              </div>
              <button className="icon-btn" onClick={() => setSelectedId(null)} aria-label="Đóng xem trước">
                <X size={16} />
              </button>
            </div>
            <dl className="docs-facts">
              <div>
                <dt>File</dt>
                <dd>{selected.file_name}</dd>
              </div>
              <div>
                <dt>Đoạn đã chia</dt>
                <dd>{selected.chunk_count}</dd>
              </div>
              <div>
                <dt>Dung lượng</dt>
                <dd>{formatSize(selected.size_bytes)}</dd>
              </div>
              <div>
                <dt>Trạng thái</dt>
                <dd>
                  <span className="status-pill">{selected.status === "active" ? "Đang dùng" : selected.status}</span>
                </dd>
              </div>
            </dl>
            <div className="docs-preview">
              {detailLoading ? (
                <div className="docs-empty compact">
                  <Loader2 size={18} className="spin" />
                  <p>Đang tải nội dung...</p>
                </div>
              ) : (
                <pre>{detail?.preview || "Không đọc được nội dung tài liệu."}</pre>
              )}
            </div>
            <div className="docs-detail-actions">
              <button className="ghost-btn" onClick={() => downloadDocument(selected)}>
                <Download size={15} />
                Tải xuống
              </button>
              <button className="danger-btn" onClick={() => setPendingDelete(selected)}>
                <Trash2 size={15} />
                Xóa tài liệu
              </button>
            </div>
          </aside>
        )}
      </div>

      {pendingDelete && (
        <div className="modal-backdrop" onClick={() => !deleting && setPendingDelete(null)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-icon">
              <AlertTriangle size={20} />
            </div>
            <h3>Xóa tài liệu?</h3>
            <p>
              “{pendingDelete.title || pendingDelete.file_name}” sẽ bị gỡ khỏi kho tri thức và xóa file nguồn. Chatbot
              sẽ không còn dùng nội dung này để trả lời.
            </p>
            <div className="modal-actions">
              <button className="ghost-btn" onClick={() => setPendingDelete(null)} disabled={deleting}>
                Hủy
              </button>
              <button className="danger-btn" onClick={confirmDelete} disabled={deleting}>
                {deleting ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
                Xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
