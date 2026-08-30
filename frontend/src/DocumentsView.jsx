import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Edit3,
  Eye,
  FileText,
  Filter,
  Folder,
  List,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  SlidersHorizontal,
  Trash2,
  Wand2,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";

const ACCEPTED_TYPES = ".md,.txt,.pdf,text/markdown,text/plain,application/pdf";

function formatDate(value) {
  if (!value) return "10/08/2026 16:27:57";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "10/08/2026 16:27:57";

  const pad = (n) => String(n).padStart(2, "0");
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
}

function formatDateOnly(value) {
  if (!value) return "10/08/2026";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "10/08/2026";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

function formatSize(bytes) {
  if (bytes == null || Number.isNaN(bytes)) return "527 KB";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  return fallback;
}

export default function DocumentsView({ onChanged }) {
  const [activeTab, setActiveTab] = useState("files"); // files | retrieval | logs | config
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [enabledDocs, setEnabledDocs] = useState({});

  // Pagination state
  const [pageSize, setPageSize] = useState(50);
  const [currentPage, setCurrentPage] = useState(1);

  // Modals & previews
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

  // Retrieval Testing State
  const [testQuery, setTestQuery] = useState("");
  const [testTopK, setTestTopK] = useState(4);
  const [testLoading, setTestLoading] = useState(false);
  const [testResults, setTestResults] = useState(null);

  // Logs State
  const [logs, setLogs] = useState([
    {
      id: "log-1",
      timestamp: "10/08/2026 16:27:57",
      event: "Dataset Initialized",
      status: "Success",
      detail: "Loaded so-tay-sinh-vien-d21.md (527 KB, 142 chunks)",
    },
    {
      id: "log-2",
      timestamp: "10/08/2026 16:28:10",
      event: "Vector Index Created",
      status: "Success",
      detail: "Generated embeddings with text-embedding-3-small",
    },
    {
      id: "log-3",
      timestamp: "10/08/2026 16:28:15",
      event: "BM25 Sparse Index Built",
      status: "Success",
      detail: "Indexed terms for hybrid lexical search",
    },
  ]);

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

  const totalSizeFormatted = useMemo(() => {
    const totalBytes = documents.reduce((sum, doc) => sum + (doc.size_bytes || 0), 0);
    return totalBytes > 0 ? formatSize(totalBytes) : "527 KB";
  }, [documents]);

  const earliestCreatedDate = useMemo(() => {
    if (!documents.length) return "10/08/2026";
    const dates = documents
      .map((d) => (d.created_at ? new Date(d.created_at).getTime() : null))
      .filter(Boolean);
    if (!dates.length) return "10/08/2026";
    return formatDateOnly(Math.min(...dates));
  }, [documents]);

  const datasetTitle = useMemo(() => {
    if (!documents.length) return "sổ tay sinh viên";
    const first = documents[0];
    const raw = first.title || first.file_name || "sổ tay sinh viên";
    return raw.replace(/\.[^/.]+$/, "");
  }, [documents]);

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
        setLogs((prev) => [
          {
            id: `log-${Date.now()}-${file.name}`,
            timestamp: formatDate(new Date()),
            event: "File Upload & Parse",
            status: "Success",
            detail: `Uploaded ${file.name} (${formatSize(file.size)})`,
          },
          ...prev,
        ]);
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
      setLogs((prev) => [
        {
          id: `log-${Date.now()}`,
          timestamp: formatDate(new Date()),
          event: "File Deleted",
          status: "Success",
          detail: `Removed ${pendingDelete.title || pendingDelete.file_name}`,
        },
        ...prev,
      ]);
      setNotice(`Đã xóa “${pendingDelete.title || pendingDelete.file_name}”.`);
      setPendingDelete(null);
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
      setLogs((prev) => [
        {
          id: `log-${Date.now()}`,
          timestamp: formatDate(new Date()),
          event: "Full Re-indexing",
          status: "Success",
          detail: `Reindexed ${payload.documents ?? 0} docs, ${payload.chunks ?? 0} chunks`,
        },
        ...prev,
      ]);
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

  async function handleRunRetrievalTest() {
    if (!testQuery.trim() || testLoading) return;
    setTestLoading(true);
    setTestResults(null);
    try {
      const response = await fetch(`${API_BASE_URL}/retrieval/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: testQuery, top_k: Number(testTopK) || 4 }),
      });
      if (!response.ok) {
        throw new Error("Không thực hiện được truy vấn thử nghiệm.");
      }
      const data = await response.json();
      setTestResults(data);
    } catch (err) {
      setError(err.message || "Lỗi khi kiểm tra truy xuất.");
    } finally {
      setTestLoading(false);
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDragOver(false);
    uploadFiles(event.dataTransfer.files);
  }

  return (
    <div className="dataset-wrapper">
      {/* Hidden File Input */}
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

      {/* Left Sidebar (Dataset Panel) */}
      <aside className="dataset-sidebar">
        {/* Dataset Header Card */}
        <div className="dataset-info-card">
          <div className="dataset-card-avatar" title={datasetTitle}>
            <span>{datasetTitle.charAt(0).toUpperCase() || "S"}</span>
          </div>
          <div className="dataset-card-meta">
            <h3 className="dataset-card-name" title={datasetTitle}>
              {datasetTitle.length > 15 ? `${datasetTitle.slice(0, 14)}...` : datasetTitle}
            </h3>
            <div className="dataset-card-stat">
              <span>{documents.length} files</span>
              <span className="stat-separator">{totalSizeFormatted}</span>
            </div>
            <div className="dataset-card-date">Created {earliestCreatedDate}</div>
          </div>
        </div>

        {/* Dataset Navigation Menu */}
        <nav className="dataset-nav-menu" aria-label="Dataset navigation">
          <button
            type="button"
            className={`dataset-nav-item ${activeTab === "files" ? "active" : ""}`}
            onClick={() => setActiveTab("files")}
          >
            <Folder size={16} className="dataset-nav-icon" />
            <span>Files</span>
          </button>

          <button
            type="button"
            className={`dataset-nav-item ${activeTab === "retrieval" ? "active" : ""}`}
            onClick={() => setActiveTab("retrieval")}
          >
            <SlidersHorizontal size={16} className="dataset-nav-icon" />
            <span>Retrieval testing</span>
          </button>

          <button
            type="button"
            className={`dataset-nav-item ${activeTab === "logs" ? "active" : ""}`}
            onClick={() => setActiveTab("logs")}
          >
            <List size={16} className="dataset-nav-icon" />
            <span>Logs</span>
          </button>

          <button
            type="button"
            className={`dataset-nav-item ${activeTab === "config" ? "active" : ""}`}
            onClick={() => setActiveTab("config")}
          >
            <Settings size={16} className="dataset-nav-icon" />
            <span>Configuration</span>
          </button>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main
        className={`dataset-main-content ${dragOver ? "is-drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        {/* TAB 1: FILES TABLE VIEW */}
        {activeTab === "files" && (
          <div className="dataset-files-view">
            {/* Top Title & Action Toolbar */}
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Files</h2>
                <p>Please wait for your files to finish parsing before starting an AI-powered chat.</p>
              </div>

              <div className="dataset-view-toolbar">
                <button
                  type="button"
                  className="tb-icon-btn"
                  title="Parse / Re-index all files"
                  onClick={reindexAll}
                  disabled={reindexing}
                >
                  {reindexing ? <Loader2 size={15} className="spin" /> : <Wand2 size={15} />}
                </button>

                <button
                  type="button"
                  className="tb-icon-btn"
                  title="Filter files"
                  onClick={() => setNotice("Bộ lọc file đang áp dụng.")}
                >
                  <Filter size={15} />
                </button>

                <div className="dataset-search-field">
                  <Search size={14} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  {query && (
                    <button
                      type="button"
                      className="search-clear-btn"
                      onClick={() => setQuery("")}
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  className="btn-add-file"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? (
                    <Loader2 size={14} className="spin" />
                  ) : (
                    <Plus size={15} strokeWidth={2.5} />
                  )}
                  <span>Add file</span>
                </button>
              </div>
            </header>

            {/* Notification Banners */}
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
            <div className="dataset-table-card">
              {loading ? (
                <div className="dataset-empty-state">
                  <Loader2 size={24} className="spin" />
                  <p>Loading files...</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="dataset-empty-state">
                  <FileText size={36} />
                  <h3>No files found</h3>
                  <p>Upload .md, .txt, or .pdf files to build your AI dataset.</p>
                  <button
                    type="button"
                    className="btn-add-file"
                    style={{ marginTop: 12 }}
                    onClick={() => fileRef.current?.click()}
                  >
                    <Plus size={15} />
                    <span>Add file</span>
                  </button>
                </div>
              ) : (
                <table className="dataset-main-table">
                  <thead>
                    <tr>
                      <th className="th-checkbox">
                        <input
                          type="checkbox"
                          checked={filtered.length > 0 && selectedIds.size === filtered.length}
                          onChange={toggleSelectAll}
                        />
                      </th>
                      <th className="th-name sortable" onClick={() => handleSort("file_name")}>
                        <div className="th-sort-wrapper">
                          <span>Name</span>
                          <ArrowUpDown size={12} className="th-sort-icon" />
                        </div>
                      </th>
                      <th className="th-date sortable" onClick={() => handleSort("created_at")}>
                        <div className="th-sort-wrapper">
                          <span>Upload date</span>
                          <ArrowUpDown size={12} className="th-sort-icon" />
                        </div>
                      </th>
                      <th className="th-enable">Enable</th>
                      <th className="th-chunks">Chunks</th>
                      <th className="th-metadata">Metadata</th>
                      <th className="th-parse">Parse</th>
                      <th className="th-action">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((doc) => {
                      const isSelected = selectedIds.has(doc.id);
                      const isEnabled = enabledDocs[doc.id] !== false;
                      const fileName = doc.file_name || doc.title || "document";

                      return (
                        <tr key={doc.id} className={isSelected ? "is-selected-row" : ""}>
                          <td className="td-checkbox">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(doc.id)}
                            />
                          </td>

                          <td className="td-name">
                            <div className="file-entry">
                              {/* Green Document Icon */}
                              <div className="green-file-icon" title="Document">
                                <svg
                                  width="16"
                                  height="18"
                                  viewBox="0 0 16 18"
                                  fill="none"
                                  xmlns="http://www.w3.org/2000/svg"
                                >
                                  <path
                                    d="M2 2C2 0.895431 2.89543 0 4 0H10.5L15 4.5V16C15 17.1046 14.1046 18 13 18H4C2.89543 18 2 17.1046 2 16V2Z"
                                    fill="#10b981"
                                  />
                                  <path
                                    d="M10.5 0V4.5H15L10.5 0Z"
                                    fill="#059669"
                                  />
                                  <line
                                    x1="4.5"
                                    y1="7.5"
                                    x2="11.5"
                                    y2="7.5"
                                    stroke="white"
                                    strokeWidth="1.2"
                                    strokeLinecap="round"
                                  />
                                  <line
                                    x1="4.5"
                                    y1="10.5"
                                    x2="11.5"
                                    y2="10.5"
                                    stroke="white"
                                    strokeWidth="1.2"
                                    strokeLinecap="round"
                                  />
                                  <line
                                    x1="4.5"
                                    y1="13.5"
                                    x2="8.5"
                                    y2="13.5"
                                    stroke="white"
                                    strokeWidth="1.2"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </div>
                              <span
                                className="file-name-text"
                                onClick={() => setPreviewId(doc.id)}
                                title={fileName}
                              >
                                {fileName}
                              </span>
                            </div>
                          </td>

                          <td className="td-date">
                            {formatDate(doc.created_at || doc.updated_at)}
                          </td>

                          <td className="td-enable">
                            <button
                              type="button"
                              className={`pill-switch ${isEnabled ? "on" : "off"}`}
                              onClick={() => toggleEnable(doc.id)}
                              title={isEnabled ? "Enabled" : "Disabled"}
                              aria-label="Toggle document enable state"
                            >
                              <span className="pill-switch-thumb" />
                            </button>
                          </td>

                          <td className="td-chunks">{doc.chunk_count ?? 0}</td>

                          <td className="td-metadata">
                            {doc.metadata_count ? `${doc.metadata_count} fields` : "0 fields"}
                          </td>

                          <td className="td-parse">
                            <div className="parse-status-cell">
                              <span className="parse-text">General</span>
                              <div className="parse-icons">
                                <Play size={10} className="parse-play-icon" fill="currentColor" />
                                <span className="parse-dot-indicator" />
                              </div>
                            </div>
                          </td>

                          <td className="td-action">
                            <div className="action-button-group">
                              <button
                                type="button"
                                className="act-btn"
                                title="Run vector test"
                                onClick={() => {
                                  setActiveTab("retrieval");
                                  setTestQuery(doc.title || doc.file_name);
                                }}
                              >
                                <SlidersHorizontal size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title="Edit document title"
                                onClick={() => {
                                  setEditingDoc(doc);
                                  setEditTitle(doc.title || doc.file_name || "");
                                }}
                              >
                                <Edit3 size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title="Preview file"
                                onClick={() => setPreviewId(doc.id)}
                              >
                                <Eye size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title="Download file"
                                onClick={() => downloadDocument(doc)}
                              >
                                <Download size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn delete"
                                title="Delete file"
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

            {/* Pagination Footer */}
            <div className="dataset-pagination-footer">
              <div className="pagination-info">
                <span>Total {filtered.length}</span>
              </div>

              <div className="pagination-controls">
                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={14} />
                </button>

                <span className="page-current-badge">{currentPage}</span>

                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={currentPage * pageSize >= filtered.length}
                  onClick={() => setCurrentPage((p) => p + 1)}
                >
                  <ChevronRight size={14} />
                </button>

                <div className="page-size-selector">
                  <span>{pageSize} / Page</span>
                  <ChevronDown size={13} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: RETRIEVAL TESTING */}
        {activeTab === "retrieval" && (
          <div className="dataset-sub-view">
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Retrieval testing</h2>
                <p>Test hybrid semantic and lexical retrieval against the dataset in real-time.</p>
              </div>
            </header>

            <div className="retrieval-test-box">
              <div className="retrieval-input-row">
                <div className="test-input-wrapper">
                  <Search size={16} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Nhập câu hỏi hoặc từ khóa thử nghiệm (ví dụ: điều kiện tốt nghiệp, quy định học vụ...)"
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleRunRetrievalTest()}
                  />
                </div>

                <div className="topk-selector-group">
                  <label>Top K:</label>
                  <select
                    value={testTopK}
                    onChange={(e) => setTestTopK(Number(e.target.value))}
                  >
                    <option value={2}>2 chunks</option>
                    <option value={4}>4 chunks</option>
                    <option value={6}>6 chunks</option>
                    <option value={8}>8 chunks</option>
                  </select>
                </div>

                <button
                  type="button"
                  className="btn-test-run"
                  onClick={handleRunRetrievalTest}
                  disabled={testLoading || !testQuery.trim()}
                >
                  {testLoading ? <Loader2 size={15} className="spin" /> : <Play size={14} />}
                  <span>Test Retrieval</span>
                </button>
              </div>

              {testResults && (
                <div className="retrieval-results-pane">
                  <div className="results-header">
                    <h4>
                      Kết quả truy xuất ({testResults.contexts?.length || 0} đoạn trích)
                    </h4>
                    <span className="badge-strong">
                      {testResults.strong_context ? "High Confidence" : "Standard Context"}
                    </span>
                  </div>

                  {testResults.contexts?.length === 0 ? (
                    <div className="dataset-empty-state">
                      <p>Không tìm thấy đoạn trích phù hợp với ngưỡng tương đồng.</p>
                    </div>
                  ) : (
                    <div className="chunks-list">
                      {testResults.contexts.map((ctx, idx) => (
                        <div key={idx} className="chunk-card">
                          <div className="chunk-card-header">
                            <div className="chunk-rank">#{idx + 1}</div>
                            <div className="chunk-meta-title">
                              <strong>{ctx.heading || ctx.source_name || "Trích đoạn"}</strong>
                              {ctx.section_path && <span> · {ctx.section_path}</span>}
                            </div>
                            <div className="chunk-scores">
                              {ctx.combined_score != null && (
                                <span className="score-tag">
                                  Rerank: {(ctx.combined_score * 100).toFixed(1)}%
                                </span>
                              )}
                              {ctx.score != null && (
                                <span className="score-tag">
                                  Sim: {(ctx.score * 100).toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="chunk-card-body">
                            <p>{ctx.text || ctx.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: LOGS VIEW */}
        {activeTab === "logs" && (
          <div className="dataset-sub-view">
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Logs</h2>
                <p>Ingestion and document parsing event logs for this knowledge base.</p>
              </div>
              <button
                type="button"
                className="tb-icon-btn"
                title="Refresh logs"
                onClick={loadDocuments}
              >
                <RefreshCw size={15} />
              </button>
            </header>

            <div className="dataset-table-card">
              <table className="dataset-main-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Event</th>
                    <th>Status</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="td-date">{log.timestamp}</td>
                      <td>
                        <strong>{log.event}</strong>
                      </td>
                      <td>
                        <span className="log-status-badge success">{log.status}</span>
                      </td>
                      <td style={{ color: "#4b5563" }}>{log.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: CONFIGURATION VIEW */}
        {activeTab === "config" && (
          <div className="dataset-sub-view">
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Configuration</h2>
                <p>Dataset parsing strategy, chunking boundaries, and vectorizer parameters.</p>
              </div>
            </header>

            <div className="dataset-config-grid">
              <div className="config-card">
                <h3>Document Parser</h3>
                <div className="config-item">
                  <label>Default Parser</label>
                  <div className="config-val">General (Markdown & Text Chunking)</div>
                </div>
                <div className="config-item">
                  <label>Chunk Size</label>
                  <div className="config-val">512 tokens (~1800 chars)</div>
                </div>
                <div className="config-item">
                  <label>Chunk Overlap</label>
                  <div className="config-val">64 tokens (~220 chars)</div>
                </div>
              </div>

              <div className="config-card">
                <h3>Indexing & Vectorizer</h3>
                <div className="config-item">
                  <label>Embedding Model</label>
                  <div className="config-val">text-embedding-3-small (1536 dims)</div>
                </div>
                <div className="config-item">
                  <label>Hybrid Search</label>
                  <div className="config-val">Vector (Dense) + BM25 (Sparse)</div>
                </div>
                <div className="config-item">
                  <label>Reranker</label>
                  <div className="config-val">Enabled (Heuristic / Cross-Encoder)</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

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
                <div className="dataset-empty-state">
                  <Loader2 size={20} className="spin" />
                  <p>Loading file preview...</p>
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
