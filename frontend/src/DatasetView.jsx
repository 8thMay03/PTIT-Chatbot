import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUpDown,
  Edit3,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  FileText,
  Folder,
  Info,
  List,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { apiError, EMPTY, formatDate, formatDateOnly, formatSize } from "./lib/format";
import DocumentView from "./DocumentView";
import Modal from "./components/Modal";
import { useToast } from "./components/Toast";

const ACCEPTED_TYPES = ".md,.txt,.pdf,text/markdown,text/plain,application/pdf";
const PAGE_SIZES = [10, 20, 50, 100];

const TABS = [
  { key: "files", label: "Tài liệu", icon: Folder },
  { key: "retrieval", label: "Thử nghiệm truy xuất", icon: SlidersHorizontal },
  { key: "logs", label: "Nhật ký", icon: List },
];

export default function DatasetView({ onChanged }) {
  const toast = useToast();

  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem("ptit_dataset_tab");
    return TABS.some((t) => t.key === saved) ? saved : "files";
  });
  const [selectedDocId, setSelectedDocId] = useState(null);

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  // Trạng thái bật/tắt và tiêu đề sửa tại chỗ: backend chưa có trường `enable`
  // lẫn endpoint đổi tiêu đề, nên cả hai chỉ tồn tại trong phiên làm việc này.
  const [enabledDocs, setEnabledDocs] = useState({});
  const [editingDoc, setEditingDoc] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [localTitles, setLocalTitles] = useState({});

  const [pageSize, setPageSize] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);

  const [pendingDelete, setPendingDelete] = useState(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [parsingDocId, setParsingDocId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Thử nghiệm truy xuất
  const [testQuery, setTestQuery] = useState("");
  const [testSimilarityThreshold, setTestSimilarityThreshold] = useState(0.2);
  const [testVectorWeight, setTestVectorWeight] = useState(0.3);
  const [testRerankModel, setTestRerankModel] = useState("");
  const [testTopK, setTestTopK] = useState(10);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState("");
  const [testResults, setTestResults] = useState(null);

  // Nhật ký: chỉ ghi các thao tác THẬT diễn ra trong phiên này.
  // Backend chưa có bảng log, nên không có gì để tải lại sau khi làm mới trang.
  const [logs, setLogs] = useState([]);

  const fileRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("ptit_dataset_tab", activeTab);
  }, [activeTab]);

  const addLog = useCallback((event, detail, status = "Thành công") => {
    setLogs((prev) => [
      { id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, timestamp: formatDate(new Date()), event, status, detail },
      ...prev,
    ]);
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) throw new Error("Máy chủ trả về lỗi khi lấy danh sách tài liệu.");
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
      setDocuments([]);
      setLoadError(
        err instanceof TypeError
          ? "Không kết nối được máy chủ. Kiểm tra server FastAPI đã chạy chưa."
          : err.message || "Không tải được danh sách tài liệu."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

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

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

  // Lọc hoặc đổi cỡ trang có thể khiến trang hiện tại vượt quá số trang thật
  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [currentPage, totalPages]);

  const paged = useMemo(
    () => filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    [filtered, currentPage, pageSize]
  );

  const totalSizeFormatted = useMemo(() => {
    if (!documents.length) return EMPTY;
    const totalBytes = documents.reduce((sum, doc) => sum + (doc.size_bytes || 0), 0);
    return totalBytes > 0 ? formatSize(totalBytes) : EMPTY;
  }, [documents]);

  const earliestCreatedDate = useMemo(() => {
    const dates = documents
      .map((d) => (d.created_at ? new Date(d.created_at).getTime() : null))
      .filter(Boolean);
    return dates.length ? formatDateOnly(Math.min(...dates)) : EMPTY;
  }, [documents]);

  const datasetTitle = useMemo(() => {
    if (!documents.length) return "Kho tài liệu PTIT";
    const first = documents[0];
    const raw = first.title || first.file_name || "Kho tài liệu PTIT";
    return raw.replace(/\.[^/.]+$/, "");
  }, [documents]);

  // Chọn theo TRANG HIỆN TẠI, không phải toàn bộ kết quả lọc: người dùng chỉ
  // nhìn thấy các dòng của trang này nên "chọn tất cả" phải khớp với thứ họ thấy.
  const pageIds = useMemo(() => paged.map((d) => d.id), [paged]);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allPageSelected) pageIds.forEach((id) => next.delete(id));
      else pageIds.forEach((id) => next.add(id));
      return next;
    });
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
    setEnabledDocs((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function saveDocTitle() {
    if (!editingDoc) return;
    const title = editTitle.trim();
    if (!title) return;
    setLocalTitles((prev) => ({ ...prev, [editingDoc.id]: title }));
    addLog("Đổi tiêu đề tài liệu", `${editingDoc.file_name} → “${title}” (chỉ trong phiên này)`);
    toast.warning(`Đã đổi tiêu đề thành “${title}”. Máy chủ chưa hỗ trợ lưu, tên sẽ trở lại sau khi tải lại trang.`);
    setEditingDoc(null);
  }

  function handleSort(field) {
    if (sortField === field) setSortAsc(!sortAsc);
    else {
      setSortField(field);
      setSortAsc(true);
    }
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length || uploading) return;

    setUploading(true);
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
          addLog("Tải lên tài liệu", `${file.name} — ${apiError(payload, "thất bại")}`, "Thất bại");
          continue;
        }
        uploaded += 1;
        addLog("Tải lên tài liệu", `${file.name} (${formatSize(file.size)})`);
      } catch {
        failures.push(`${file.name}: không kết nối được máy chủ`);
        addLog("Tải lên tài liệu", `${file.name} — không kết nối được máy chủ`, "Thất bại");
      }
    }

    await loadDocuments();
    onChanged?.();
    setUploading(false);

    if (uploaded && !failures.length) {
      toast.success(`Đã nạp ${uploaded} tài liệu vào kho.`);
    } else if (uploaded) {
      toast.warning(`Đã nạp ${uploaded} tài liệu. ${failures.length} file bị lỗi: ${failures.join(" · ")}`);
    } else {
      toast.error(failures.join(" · ") || "Không tải lên được tài liệu nào.");
    }
  }

  async function deleteDocument(doc) {
    const response = await fetch(`${API_BASE_URL}/documents/${doc.id}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(apiError(payload, `Không xóa được “${doc.title || doc.file_name}”.`));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete || deleting) return;
    setDeleting(true);
    const label = pendingDelete.title || pendingDelete.file_name;
    try {
      await deleteDocument(pendingDelete);
      if (selectedDocId === pendingDelete.id) setSelectedDocId(null);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(pendingDelete.id);
        return next;
      });
      addLog("Xóa tài liệu", label);
      toast.success(`Đã xóa “${label}”.`);
      setPendingDelete(null);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      addLog("Xóa tài liệu", `${label} — ${err.message}`, "Thất bại");
      toast.error(err.message);
    } finally {
      setDeleting(false);
    }
  }

  async function confirmBulkDelete() {
    if (deleting) return;
    setDeleting(true);
    const targets = documents.filter((d) => selectedIds.has(d.id));
    let done = 0;
    const failures = [];

    for (const doc of targets) {
      try {
        await deleteDocument(doc);
        done += 1;
      } catch (err) {
        failures.push(err.message);
      }
    }

    addLog(
      "Xóa nhiều tài liệu",
      `Đã xóa ${done}/${targets.length} tài liệu`,
      failures.length ? "Thất bại một phần" : "Thành công"
    );
    if (failures.length) toast.warning(`Đã xóa ${done}/${targets.length}. Lỗi: ${failures.join(" · ")}`);
    else toast.success(`Đã xóa ${done} tài liệu.`);

    setSelectedIds(new Set());
    setBulkDeleteOpen(false);
    setDeleting(false);
    await loadDocuments();
    onChanged?.();
  }

  async function reindexAll() {
    if (reindexing) return;
    setReindexing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/ingest`, { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload, "Không nạp lại được kho tri thức."));
      const detail = `${payload.documents ?? 0} tài liệu · ${payload.chunks ?? 0} đoạn`;
      addLog("Nạp lại toàn bộ kho", detail);
      toast.success(`Đã nạp lại ${detail}.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      addLog("Nạp lại toàn bộ kho", err.message, "Thất bại");
      toast.error(err.message || "Không nạp lại được kho tri thức.");
    } finally {
      setReindexing(false);
    }
  }

  async function parseDocument(doc) {
    if (!doc || parsingDocId || reindexing) return;
    setParsingDocId(doc.id);
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${doc.id}/parse`, { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload, "Không parse được tài liệu."));
      const label = payload.title || payload.file_name || doc.file_name;
      addLog("Parse tài liệu", `${label} → ${payload.chunk_count ?? 0} đoạn`);
      toast.success(`Đã parse “${label}” thành ${payload.chunk_count ?? 0} đoạn.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      addLog("Parse tài liệu", `${doc.file_name} — ${err.message}`, "Thất bại");
      toast.error(err.message || "Lỗi khi parse tài liệu.");
    } finally {
      setParsingDocId(null);
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
      link.download = doc.file_name || "tai-lieu";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.message || "Không tải được file nguồn.");
    }
  }

  async function handleRunRetrievalTest() {
    if (!testQuery.trim() || testLoading) return;
    setTestLoading(true);
    setTestError("");
    setTestResults(null);
    try {
      const response = await fetch(`${API_BASE_URL}/retrieval/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: testQuery,
          top_k: Number(testTopK) || 10,
          similarity_threshold: testSimilarityThreshold,
          vector_similarity_weight: testVectorWeight,
          rerank_model: testRerankModel || null,
        }),
      });
      if (!response.ok) throw new Error("Máy chủ trả về lỗi khi chạy truy vấn thử.");
      setTestResults(await response.json());
    } catch (err) {
      setTestError(
        err instanceof TypeError
          ? "Không kết nối được máy chủ."
          : err.message || "Lỗi khi kiểm tra truy xuất."
      );
    } finally {
      setTestLoading(false);
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDragOver(false);
    uploadFiles(event.dataTransfer.files);
  }

  // Màn chi tiết tài liệu, mở từ danh sách bên dưới
  if (selectedDocId) {
    return (
      <DocumentView
        documentId={selectedDocId}
        onBack={() => setSelectedDocId(null)}
        parsingDocId={parsingDocId}
        reindexing={reindexing}
        onParse={parseDocument}
      />
    );
  }

  const selectedCount = selectedIds.size;

  return (
    <div className="dataset-wrapper">
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

      <aside className="dataset-sidebar">
        <div className="dataset-info-card">
          <div className="dataset-card-avatar" title={datasetTitle} aria-hidden="true">
            <span>{datasetTitle.charAt(0).toUpperCase()}</span>
          </div>
          <div className="dataset-card-meta">
            <h3 className="dataset-card-name" title={datasetTitle}>
              {datasetTitle.length > 15 ? `${datasetTitle.slice(0, 14)}…` : datasetTitle}
            </h3>
            <div className="dataset-card-stat">
              <span>{documents.length} tài liệu</span>
              <span className="stat-separator">{totalSizeFormatted}</span>
            </div>
            <div className="dataset-card-date">Tạo ngày {earliestCreatedDate}</div>
          </div>
        </div>

        <nav className="dataset-nav-menu" aria-label="Điều hướng kho tài liệu">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                className={`dataset-nav-item ${active ? "active" : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={() => setActiveTab(tab.key)}
              >
                <Icon size={16} className="dataset-nav-icon" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main
        className={`dataset-main-content ${dragOver ? "is-drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        {/* ---------------------------------------------------------------
            TAB 1: DANH SÁCH TÀI LIỆU
            --------------------------------------------------------------- */}
        {activeTab === "files" && (
          <div className="dataset-files-view">
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Tài liệu</h2>
                <p>Hãy đợi tài liệu parse xong trước khi bắt đầu hỏi đáp.</p>
              </div>

              <div className="dataset-view-toolbar">
                <button
                  type="button"
                  className="btn-parse-dataset"
                  title="Chạy lại toàn bộ pipeline parse và nạp vector cho mọi tài liệu"
                  onClick={reindexAll}
                  disabled={reindexing || Boolean(parsingDocId)}
                >
                  {reindexing ? <Loader2 size={14} className="spin" /> : <Play size={13} fill="currentColor" />}
                  <span>{reindexing ? "Đang nạp lại..." : "Nạp lại toàn bộ"}</span>
                </button>

                <div className="dataset-search-field">
                  <Search size={14} className="search-icon" aria-hidden="true" />
                  <label className="sr-only" htmlFor="dataset-search">
                    Tìm tài liệu theo tên
                  </label>
                  <input
                    id="dataset-search"
                    type="text"
                    placeholder="Tìm tài liệu"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setCurrentPage(1);
                    }}
                  />
                  {query && (
                    <button
                      type="button"
                      className="search-clear-btn"
                      onClick={() => setQuery("")}
                      aria-label="Xóa từ khóa tìm kiếm"
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
                  {uploading ? <Loader2 size={14} className="spin" /> : <Plus size={15} strokeWidth={2.5} />}
                  <span>Thêm tài liệu</span>
                </button>
              </div>
            </header>

            {loadError && (
              <div className="inline-alert is-error" role="alert" style={{ marginBottom: 12 }}>
                <AlertTriangle size={16} />
                <span>{loadError}</span>
              </div>
            )}

            {selectedCount > 0 && (
              <div className="bulk-bar">
                <span className="bulk-bar-count">Đã chọn {selectedCount} tài liệu</span>
                <div className="bulk-bar-actions">
                  <button type="button" className="bulk-btn" onClick={() => setSelectedIds(new Set())}>
                    Bỏ chọn
                  </button>
                  <button
                    type="button"
                    className="bulk-btn is-danger"
                    onClick={() => setBulkDeleteOpen(true)}
                    disabled={deleting}
                  >
                    <Trash2 size={13} />
                    Xóa đã chọn
                  </button>
                </div>
              </div>
            )}

            <div className="dataset-table-card">
              {loading ? (
                <div className="state-block" aria-busy="true">
                  <div style={{ width: "100%", padding: "0 16px" }}>
                    {[0, 1, 2, 3, 4].map((i) => (
                      <div key={i} className="skeleton skeleton-row" />
                    ))}
                  </div>
                  <p>Đang tải danh sách tài liệu...</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="state-block">
                  <span className="state-icon">
                    <FileText size={24} />
                  </span>
                  <h3>{query ? "Không có tài liệu nào khớp" : "Kho tài liệu đang trống"}</h3>
                  <p>
                    {query
                      ? "Thử từ khóa khác, hoặc xóa ô tìm kiếm để xem toàn bộ."
                      : "Tải lên file .md, .txt hoặc .pdf để xây dựng kho tri thức cho trợ lý."}
                  </p>
                  {!query && (
                    <button type="button" className="btn-add-file" onClick={() => fileRef.current?.click()}>
                      <Plus size={15} />
                      <span>Thêm tài liệu</span>
                    </button>
                  )}
                </div>
              ) : (
                <table className="dataset-main-table">
                  <thead>
                    <tr>
                      <th className="th-checkbox">
                        <input
                          type="checkbox"
                          checked={allPageSelected}
                          onChange={toggleSelectAll}
                          aria-label="Chọn tất cả tài liệu trên trang này"
                        />
                      </th>
                      <th className="th-name sortable">
                        <button type="button" className="th-sort-wrapper" onClick={() => handleSort("file_name")}>
                          <span>Tên tài liệu</span>
                          <ArrowUpDown size={12} className="th-sort-icon" />
                        </button>
                      </th>
                      <th className="th-date sortable">
                        <button type="button" className="th-sort-wrapper" onClick={() => handleSort("created_at")}>
                          <span>Ngày tải lên</span>
                          <ArrowUpDown size={12} className="th-sort-icon" />
                        </button>
                      </th>
                      <th className="th-enable" title="Chỉ có tác dụng trong phiên làm việc này">
                        Bật/Tắt
                      </th>
                      <th className="th-status">Trạng thái</th>
                      <th className="th-chunks">Số đoạn</th>
                      <th className="th-size">Dung lượng</th>
                      <th className="th-action">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paged.map((doc) => {
                      const isSelected = selectedIds.has(doc.id);
                      const fileName = localTitles[doc.id] || doc.file_name || doc.title || "tài liệu";
                      const isParsing = parsingDocId === doc.id;
                      const isEnabled = enabledDocs[doc.id] !== false;

                      return (
                        <tr key={doc.id} className={isSelected ? "is-selected-row" : ""}>
                          <td className="td-checkbox">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(doc.id)}
                              aria-label={`Chọn ${fileName}`}
                            />
                          </td>

                          <td className="td-name">
                            <div className="file-entry">
                              <span className="file-type-icon" aria-hidden="true">
                                <FileText size={15} />
                              </span>
                              <button
                                type="button"
                                className="file-name-text"
                                onClick={() => setSelectedDocId(doc.id)}
                                title={`Mở ${fileName}`}
                              >
                                {fileName}
                              </button>
                            </div>
                          </td>

                          <td className="td-date" data-label="Ngày tải lên">
                            {formatDate(doc.created_at || doc.updated_at)}
                          </td>

                          <td className="td-enable" data-label="Bật/Tắt">
                            <button
                              type="button"
                              role="switch"
                              aria-checked={isEnabled}
                              className={`pill-switch ${isEnabled ? "on" : "off"}`}
                              onClick={() => toggleEnable(doc.id)}
                              title={`${isEnabled ? "Đang bật" : "Đang tắt"} — trạng thái này chưa được máy chủ lưu lại`}
                              aria-label={`Bật/tắt ${fileName}`}
                            >
                              <span className="pill-switch-thumb" />
                            </button>
                          </td>

                          <td className="td-status" data-label="Trạng thái">
                            <span className={`doc-status-badge is-${doc.status || "active"}`}>
                              {doc.status === "active" ? "Đã nạp" : doc.status || EMPTY}
                            </span>
                          </td>

                          <td className="td-chunks" data-label="Số đoạn">
                            {doc.chunk_count ?? 0}
                          </td>

                          <td className="td-size" data-label="Dung lượng">
                            {formatSize(doc.size_bytes)}
                          </td>

                          <td className="td-action" data-label="Thao tác">
                            <div className="action-button-group">
                              <button
                                type="button"
                                className="act-btn"
                                title={`Parse lại ${fileName}`}
                                aria-label={`Parse lại ${fileName}`}
                                onClick={() => parseDocument(doc)}
                                disabled={isParsing || reindexing}
                              >
                                {isParsing ? <Loader2 size={14} className="spin" /> : <Play size={13} fill="currentColor" />}
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title={`Xem các đoạn của ${fileName}`}
                                aria-label={`Xem các đoạn của ${fileName}`}
                                onClick={() => setSelectedDocId(doc.id)}
                              >
                                <Eye size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title={`Đổi tiêu đề ${fileName}`}
                                aria-label={`Đổi tiêu đề ${fileName}`}
                                onClick={() => {
                                  setEditingDoc(doc);
                                  setEditTitle(localTitles[doc.id] || doc.title || doc.file_name || "");
                                }}
                              >
                                <Edit3 size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn"
                                title={`Tải xuống ${fileName}`}
                                aria-label={`Tải xuống ${fileName}`}
                                onClick={() => downloadDocument(doc)}
                              >
                                <Download size={14} />
                              </button>
                              <button
                                type="button"
                                className="act-btn delete"
                                title={`Xóa ${fileName}`}
                                aria-label={`Xóa ${fileName}`}
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

            {filtered.length > 0 && (
              <div className="dataset-pagination-footer">
                <div className="pagination-info">
                  <span>
                    Hiển thị {(currentPage - 1) * pageSize + 1}–
                    {Math.min(currentPage * pageSize, filtered.length)} trên {filtered.length} tài liệu
                  </span>
                </div>

                <div className="pagination-controls">
                  <button
                    type="button"
                    className="page-nav-btn"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    aria-label="Trang trước"
                  >
                    <ChevronLeft size={14} />
                  </button>

                  <span className="page-current-badge" aria-live="polite">
                    {currentPage} / {totalPages}
                  </span>

                  <button
                    type="button"
                    className="page-nav-btn"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    aria-label="Trang sau"
                  >
                    <ChevronRight size={14} />
                  </button>

                  <label className="sr-only" htmlFor="dataset-page-size">
                    Số tài liệu mỗi trang
                  </label>
                  <select
                    id="dataset-page-size"
                    className="page-size-select"
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                  >
                    {PAGE_SIZES.map((size) => (
                      <option key={size} value={size}>
                        {size} / trang
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            TAB 2: THỬ NGHIỆM TRUY XUẤT
            --------------------------------------------------------------- */}
        {activeTab === "retrieval" && (
          <div className="dataset-retrieval-screen">
            <header className="retrieval-top-header">
              <h2>Thử nghiệm truy xuất</h2>
              <p>
                Chạy thử một câu hỏi để xem hệ thống lấy ra những đoạn văn bản nào trước khi đưa vào LLM.
                Các tham số dưới đây chỉ áp dụng cho lần chạy thử này và{" "}
                <strong>không được lưu</strong> — muốn đổi vĩnh viễn, hãy vào màn Cấu hình.
              </p>
            </header>

            <div className="retrieval-two-col-layout">
              <div className="retrieval-col-left">
                <div className="retrieval-settings-card">
                  <h3 className="retrieval-settings-title">Tham số</h3>

                  <div className="ret-form-group">
                    <label className="ret-field-label" htmlFor="ret-threshold">
                      <span>Ngưỡng tương đồng</span>
                      <span className="ret-info-icon" title="Điểm tương đồng tối thiểu để giữ lại một đoạn">
                        <Info size={13} />
                      </span>
                    </label>
                    <div className="ret-slider-row">
                      <input
                        id="ret-threshold"
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={testSimilarityThreshold}
                        onChange={(e) => setTestSimilarityThreshold(parseFloat(e.target.value))}
                        className="ret-cyan-slider"
                      />
                      <span className="ret-val-box">{testSimilarityThreshold.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="ret-form-group">
                    <label className="ret-field-label" htmlFor="ret-weight">
                      <span>Tỷ trọng vector</span>
                      <span className="ret-info-icon" title="Cân bằng giữa tìm kiếm ngữ nghĩa (vector) và khớp từ khóa (BM25)">
                        <Info size={13} />
                      </span>
                    </label>
                    <div className="ret-weight-indicators">
                      <span className="ret-ind-left">Vector {testVectorWeight.toFixed(2)}</span>
                      <span className="ret-ind-right">BM25 {(1 - testVectorWeight).toFixed(2)}</span>
                    </div>
                    <div className="ret-slider-row">
                      <input
                        id="ret-weight"
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={testVectorWeight}
                        onChange={(e) => setTestVectorWeight(parseFloat(e.target.value))}
                        className="ret-cyan-slider"
                      />
                      <span className="ret-val-box">{testVectorWeight.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="ret-form-group">
                    <label className="ret-field-label" htmlFor="ret-rerank">
                      <span>Mô hình tái xếp hạng</span>
                    </label>
                    <div className="ret-select-box">
                      <select
                        id="ret-rerank"
                        value={testRerankModel}
                        onChange={(e) => setTestRerankModel(e.target.value)}
                      >
                        <option value="">Dùng cấu hình mặc định</option>
                        <option value="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1">
                          cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
                        </option>
                        <option value="BAAI/bge-reranker-base">BAAI/bge-reranker-base</option>
                        <option value="BAAI/bge-reranker-large">BAAI/bge-reranker-large</option>
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" aria-hidden="true" />
                    </div>
                  </div>

                  <div className="ret-form-group">
                    <label className="ret-field-label" htmlFor="ret-topk">
                      <span>Số đoạn lấy ra</span>
                    </label>
                    <div className="ret-select-box">
                      <select id="ret-topk" value={testTopK} onChange={(e) => setTestTopK(Number(e.target.value))}>
                        {[5, 10, 15, 20, 30].map((n) => (
                          <option key={n} value={n}>
                            {n} đoạn
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" aria-hidden="true" />
                    </div>
                  </div>
                </div>

                <div className="ret-query-box">
                  <label className="sr-only" htmlFor="ret-query">
                    Câu hỏi thử nghiệm
                  </label>
                  <textarea
                    id="ret-query"
                    rows={4}
                    placeholder="Nhập câu hỏi để thử, ví dụ: điều kiện xét tốt nghiệp..."
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleRunRetrievalTest();
                      }
                    }}
                  />
                  <div className="ret-query-actions">
                    <button
                      type="button"
                      className="btn-run-retrieval"
                      onClick={handleRunRetrievalTest}
                      disabled={testLoading || !testQuery.trim()}
                    >
                      {testLoading ? <Loader2 size={13} className="spin" /> : <Play size={12} fill="currentColor" />}
                      <span>{testLoading ? "Đang chạy..." : "Chạy thử"}</span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="retrieval-col-right">
                <div className="ret-results-header">
                  <div className="ret-results-title">
                    <h3>Kết quả</h3>
                    <span className="ret-total-tag">
                      {testResults ? `${testResults.contexts?.length ?? 0} đoạn` : "Chưa chạy"}
                    </span>
                  </div>
                </div>

                <div className="ret-results-container" aria-busy={testLoading}>
                  {testError ? (
                    <div className="state-block is-error">
                      <span className="state-icon">
                        <AlertTriangle size={24} />
                      </span>
                      <h3>Không chạy được truy vấn</h3>
                      <p>{testError}</p>
                    </div>
                  ) : testLoading ? (
                    <div style={{ padding: 16 }}>
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="skeleton" style={{ height: 78, marginBottom: 12 }} />
                      ))}
                    </div>
                  ) : !testResults || (testResults.contexts?.length ?? 0) === 0 ? (
                    <div className="state-block">
                      <span className="state-icon">
                        <FileText size={24} />
                      </span>
                      <h3>{testResults ? "Không tìm thấy đoạn nào" : "Chưa có kết quả"}</h3>
                      <p>
                        {testResults
                          ? "Thử hạ ngưỡng tương đồng hoặc dùng từ khóa gần với nội dung tài liệu hơn."
                          : "Nhập câu hỏi bên trái và bấm “Chạy thử” để xem các đoạn được truy xuất."}
                      </p>
                    </div>
                  ) : (
                    <div className="ret-results-list">
                      {testResults.contexts.map((ctx, idx) => (
                        <div key={idx} className="ret-chunk-item">
                          <div className="ret-chunk-header">
                            <span className="ret-chunk-rank">#{idx + 1}</span>
                            <strong className="ret-chunk-title">
                              {ctx.heading || ctx.source_name || "Đoạn trích"}
                            </strong>
                            {ctx.section_path && <span className="ret-chunk-sec">· {ctx.section_path}</span>}
                            <div className="ret-chunk-badges">
                              {ctx.combined_score != null && (
                                <span className="ret-badge rerank">
                                  Xếp hạng lại: {(ctx.combined_score * 100).toFixed(1)}%
                                </span>
                              )}
                              {ctx.score != null && (
                                <span className="ret-badge sim">Tương đồng: {(ctx.score * 100).toFixed(1)}%</span>
                              )}
                            </div>
                          </div>
                          <div className="ret-chunk-content">
                            <p>{ctx.text || ctx.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------
            TAB 3: NHẬT KÝ
            --------------------------------------------------------------- */}
        {activeTab === "logs" && (
          <div className="dataset-sub-view">
            <header className="dataset-view-header">
              <div className="dataset-view-title">
                <h2>Nhật ký</h2>
                <p>Các thao tác trên kho tài liệu bạn đã thực hiện trong phiên làm việc này.</p>
              </div>
              <button
                type="button"
                className="tb-icon-btn"
                title="Xóa nhật ký"
                aria-label="Xóa nhật ký"
                onClick={() => setLogs([])}
                disabled={logs.length === 0}
              >
                <RefreshCw size={15} />
              </button>
            </header>

            <div className="inline-alert is-info" style={{ marginBottom: 12 }}>
              <Info size={16} />
              <span>
                Nhật ký chỉ tồn tại trong phiên hiện tại. Máy chủ chưa lưu lịch sử thao tác, nên
                danh sách sẽ trống lại sau khi tải lại trang.
              </span>
            </div>

            <div className="dataset-table-card">
              {logs.length === 0 ? (
                <div className="state-block">
                  <span className="state-icon">
                    <List size={24} />
                  </span>
                  <h3>Chưa có thao tác nào</h3>
                  <p>Tải lên, parse hoặc xóa tài liệu — mọi thao tác sẽ được ghi lại ở đây.</p>
                </div>
              ) : (
                <table className="dataset-main-table">
                  <thead>
                    <tr>
                      <th>Thời điểm</th>
                      <th>Sự kiện</th>
                      <th>Kết quả</th>
                      <th>Chi tiết</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td className="td-date" data-label="Thời điểm">
                          {log.timestamp}
                        </td>
                        <td data-label="Sự kiện">
                          <strong>{log.event}</strong>
                        </td>
                        <td data-label="Kết quả">
                          <span
                            className={`log-status-badge ${
                              log.status === "Thành công" ? "success" : "failure"
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td data-label="Chi tiết" className="td-log-detail">
                          {log.detail}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Xóa một tài liệu */}
      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => !deleting && setPendingDelete(null)}
        title="Xóa tài liệu?"
        description={
          pendingDelete
            ? `“${pendingDelete.title || pendingDelete.file_name}” và toàn bộ đoạn văn bản đã nhúng sẽ bị xóa khỏi kho. Không thể hoàn tác.`
            : ""
        }
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setPendingDelete(null)} disabled={deleting}>
              Hủy
            </button>
            <button type="button" className="danger-btn" onClick={confirmDelete} disabled={deleting}>
              {deleting ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
              Xóa
            </button>
          </>
        }
      />

      {/* Đổi tiêu đề tài liệu.
          Backend chưa có endpoint PATCH /documents/{id}, nên tên mới chỉ áp dụng
          trong phiên này. Hộp thoại nói thẳng điều đó thay vì im lặng như bản cũ. */}
      <Modal
        open={Boolean(editingDoc)}
        onClose={() => setEditingDoc(null)}
        title="Đổi tiêu đề tài liệu"
        icon={<Edit3 size={20} />}
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setEditingDoc(null)}>
              Hủy
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={saveDocTitle}
              disabled={!editTitle.trim()}
            >
              Áp dụng
            </button>
          </>
        }
      >
        <div className="edit-form-group">
          <label htmlFor="doc-title-input">Tiêu đề</label>
          <input
            id="doc-title-input"
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                saveDocTitle();
              }
            }}
          />
          <span className="field-hint">
            Máy chủ chưa hỗ trợ lưu tiêu đề. Tên mới chỉ hiển thị trong phiên làm việc này
            và sẽ trở lại như cũ sau khi tải lại trang.
          </span>
        </div>
      </Modal>

      {/* Xóa nhiều tài liệu */}
      <Modal
        open={bulkDeleteOpen}
        onClose={() => !deleting && setBulkDeleteOpen(false)}
        title={`Xóa ${selectedCount} tài liệu?`}
        description="Toàn bộ tài liệu đã chọn cùng các đoạn văn bản đã nhúng sẽ bị xóa khỏi kho. Không thể hoàn tác."
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setBulkDeleteOpen(false)} disabled={deleting}>
              Hủy
            </button>
            <button type="button" className="danger-btn" onClick={confirmBulkDelete} disabled={deleting}>
              {deleting ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
              Xóa {selectedCount} tài liệu
            </button>
          </>
        }
      />
    </div>
  );
}
