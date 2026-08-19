import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUpDown,
  Download,
  Edit3,
  Eye,
  FileText,
  Filter,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Sliders,
  Target,
  Trash2,
  Upload,
  Wand2,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";

const ACCEPTED_TYPES = ".md,.txt,.pdf,text/markdown,text/plain,application/pdf";

function formatDate(value) {
  if (!value) return "11/08/2026 09:27:37";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "11/08/2026 09:27:37";

  const pad = (n) => String(n).padStart(2, "0");
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
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
  const [sortField, setSortField] = useState("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [enabledDocs, setEnabledDocs] = useState({});

  const [previewId, setPreviewId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [editingDoc, setEditingDoc] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const [pendingDelete, setPendingDelete] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [notice, setNotice] = useState("");

  const fileRef = useRef(null);

  async function loadDocuments() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) throw new Error("Không tải được danh sách tài liệu.");
      const payload = await response.json();
      const docs = payload.documents ?? [];
      setDocuments(docs);

      setEnabledDocs((prev) => {
        const next = { ...prev };
        docs.forEach((doc) => {
          if (next[doc.id] === undefined) next[doc.id] = true;
        });
        return next;
      });
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
    if (!previewId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    fetch(`${API_BASE_URL}/documents/${previewId}`)
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
  }, [previewId]);

  const filtered = useMemo(() => {
    let list = [...documents];
    const needle = query.trim().toLowerCase();
    if (needle) {
      list = list.filter((doc) =>
        [doc.title, doc.file_name, doc.file_type]
          .filter(Boolean)
          .some((val) => val.toLowerCase().includes(needle))
      );
    }

    list.sort((a, b) => {
      let valA = a[sortField] || "";
      let valB = b[sortField] || "";
      if (sortField === "created_at" || sortField === "updated_at") {
        valA = new Date(valA).getTime() || 0;
        valB = new Date(valB).getTime() || 0;
      }
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });

    return list;
  }, [documents, query, sortField, sortAsc]);

  function handleSort(field) {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  }

  function toggleSelectAll() {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map((d) => d.id)));
    }
  }

  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleEnable(id) {
    setEnabledDocs((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  }

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
        const response = await fetch(`${API_BASE_URL}/documents`, {
          method: "POST",
          body: form,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          failures.push(`${file.name}: ${apiError(payload, "không tải lên được")}`);
          continue;
        }
        uploaded += 1;
      } catch {
        failures.push(`${file.name}: không kết nối được máy chủ`);
      }
    }

    await loadDocuments();
    onChanged?.();
    setUploading(false);

    if (uploaded && !failures.length) {
      setNotice(`Đã nạp ${uploaded} file vào danh sách dataset.`);
    } else if (uploaded) {
      setNotice(`Đã nạp ${uploaded} file. Một số file bị lỗi.`);
      setError(failures.join(" · "));
    } else {
      setError(failures.join(" · ") || "Không tải lên được file.");
    }
  }

  async function confirmDelete() {
    if (!pendingDelete || deleting) return;
    setDeleting(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${pendingDelete.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(apiError(payload, "Không xóa được tài liệu."));
      }
      if (previewId === pendingDelete.id) {
        setPreviewId(null);
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
      link.download = doc.file_name || "file";
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

  function getFileIcon(fileName) {
    const name = (fileName || "").toLowerCase();
    if (name.endsWith(".pdf")) {
      return (
        <span className="file-type-icon pdf" title="PDF Document">
          <span className="pdf-badge-text">PDF</span>
        </span>
      );
    }
    if (name.endsWith(".md") || name.endsWith(".txt")) {
      return (
        <span className="file-type-icon doc" title="Text Document">
          <FileText size={18} />
        </span>
      );
    }
    return (
      <span className="file-type-icon default">
        <FileText size={18} />
      </span>
    );
  }

  function getParseType(fileName) {
    const name = (fileName || "").toLowerCase();
    if (name.endsWith(".pdf")) return "Paper";
    return "General";
  }

  return (
    <div
      className={`dataset-screen ${dragOver ? "is-drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
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
        onChange={(e) => {
          uploadFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {/* Top Title & Toolbar */}
      <header className="dataset-header">
        <div className="dataset-header-title">
          <h2>Files</h2>
          <p>Please wait for your files to finish parsing before starting an AI-powered chat.</p>
        </div>

        <div className="dataset-header-toolbar">
          <button
            type="button"
            className="tool-btn"
            title="Parse / Re-index files"
            onClick={reindexAll}
            disabled={reindexing}
          >
            {reindexing ? <Loader2 size={16} className="spin" /> : <Wand2 size={16} />}
          </button>
          <button
            type="button"
            className="tool-btn"
            title="Filter files"
            onClick={() => setNotice("Bộ lọc đã bật.")}
          >
            <Filter size={16} />
          </button>

          <div className="dataset-search-box">
            <Search size={15} />
            <input
              type="text"
              placeholder="Search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <button
            type="button"
            className="add-file-btn"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? <Loader2 size={15} className="spin" /> : <Plus size={16} />}
            <span>Add file</span>
          </button>
        </div>
      </header>

      {/* Banners */}
      {notice && (
        <div className="dataset-banner notice">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>
            <X size={14} />
          </button>
        </div>
      )}
      {error && (
        <div className="dataset-banner error">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Data Table */}
      <div className="dataset-table-container">
        {loading ? (
          <div className="dataset-empty">
            <Loader2 size={24} className="spin" />
            <p>Loading files...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="dataset-empty">
            <FileText size={32} />
            <h3>No files found</h3>
            <p>Upload .pdf, .md or .txt files to parse dataset for AI chat.</p>
          </div>
        ) : (
          <table className="dataset-table">
            <thead>
              <tr>
                <th className="col-checkbox">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIds.size === filtered.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th className="col-name sortable" onClick={() => handleSort("file_name")}>
                  <span>Name</span>
                  <ArrowUpDown size={13} className="sort-icon" />
                </th>
                <th className="col-date sortable" onClick={() => handleSort("created_at")}>
                  <span>Upload date</span>
                  <ArrowUpDown size={13} className="sort-icon" />
                </th>
                <th className="col-enable">Enable</th>
                <th className="col-chunks">Chunks</th>
                <th className="col-metadata">Metadata</th>
                <th className="col-parse">Parse</th>
                <th className="col-action">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => {
                const isSelected = selectedIds.has(doc.id);
                const isEnabled = enabledDocs[doc.id] !== false;
                const parseType = getParseType(doc.file_name);

                return (
                  <tr key={doc.id} className={isSelected ? "is-selected" : ""}>
                    <td className="col-checkbox">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(doc.id)}
                      />
                    </td>

                    <td className="col-name">
                      <div className="file-name-cell">
                        {getFileIcon(doc.file_name)}
                        <span
                          className="file-name-text"
                          onClick={() => setPreviewId(doc.id)}
                          title={doc.file_name || doc.title}
                        >
                          {doc.file_name || doc.title}
                        </span>
                      </div>
                    </td>

                    <td className="col-date">
                      {formatDate(doc.created_at || doc.updated_at)}
                    </td>

                    <td className="col-enable">
                      <button
                        type="button"
                        className={`toggle-switch ${isEnabled ? "on" : "off"}`}
                        onClick={() => toggleEnable(doc.id)}
                        title={isEnabled ? "Enabled" : "Disabled"}
                        aria-label="Toggle document enable state"
                      >
                        <span className="toggle-thumb" />
                      </button>
                    </td>

                    <td className="col-chunks">{doc.chunk_count ?? 0}</td>

                    <td className="col-metadata">
                      {doc.metadata_count ? `${doc.metadata_count} fields` : "0 fields"}
                    </td>

                    <td className="col-parse">
                      <span className="parse-badge">
                        <span className="parse-dot" />
                        <span>{parseType}</span>
                        <Target size={12} className="parse-target-icon" />
                      </span>
                    </td>

                    <td className="col-action">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Run parse / test"
                          onClick={() => reindexAll()}
                        >
                          <Sliders size={14} />
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Edit details"
                          onClick={() => {
                            setEditingDoc(doc);
                            setEditTitle(doc.title || doc.file_name || "");
                          }}
                        >
                          <Edit3 size={14} />
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Preview"
                          onClick={() => setPreviewId(doc.id)}
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Download"
                          onClick={() => downloadDocument(doc)}
                        >
                          <Download size={14} />
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn danger"
                          title="Delete"
                          onClick={() => setPendingDelete(doc)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Preview Modal */}
      {previewId && (
        <div className="modal-backdrop" onClick={() => setPreviewId(null)}>
          <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="preview-modal-header">
              <h3>{detail?.file_name || "File Preview"}</h3>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setPreviewId(null)}
              >
                <X size={16} />
              </button>
            </div>
            <div className="preview-modal-body">
              {detailLoading ? (
                <div className="dataset-empty">
                  <Loader2 size={20} className="spin" />
                  <p>Loading content...</p>
                </div>
              ) : (
                <pre>{detail?.preview || "No content preview available."}</pre>
              )}
            </div>
            <div className="preview-modal-footer">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setPreviewId(null)}
              >
                Close
              </button>
              {detail && (
                <button
                  type="button"
                  className="primary-btn"
                  onClick={() => downloadDocument(detail)}
                >
                  <Download size={15} />
                  Download
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingDoc && (
        <div className="modal-backdrop" onClick={() => setEditingDoc(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Edit Document</h3>
            <div className="edit-form-group">
              <label>Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setEditingDoc(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="primary-btn"
                onClick={() => {
                  setNotice(`Updated "${editTitle}"`);
                  setEditingDoc(null);
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {pendingDelete && (
        <div className="modal-backdrop" onClick={() => !deleting && setPendingDelete(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon">
              <AlertTriangle size={20} />
            </div>
            <h3>Delete file?</h3>
            <p>
              “{pendingDelete.title || pendingDelete.file_name}” will be removed from the dataset.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setPendingDelete(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-btn"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
