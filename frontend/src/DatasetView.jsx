import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUpDown,
  Edit3,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  FileText,
  Loader2,
  Play,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { apiError, EMPTY, formatDate, formatSize } from "./lib/format";
import DocumentView from "./DocumentView";
import ParserSelectionModal from "./components/ParserSelectionModal";
import Modal from "./components/Modal";
import { useToast } from "./components/Toast";

const ACCEPTED_TYPES =
  ".md,.txt,.pdf,.docx,text/markdown,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const PAGE_SIZES = [10, 20, 50, 100];

export default function DatasetView({ onChanged }) {
  const toast = useToast();

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
  const [parseTarget, setParseTarget] = useState(null);
  const parseResolve = useRef(null);
  const [parsingDocId, setParsingDocId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const fileRef = useRef(null);

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
      toast.success(`Đã xóa “${label}”.`);
      setPendingDelete(null);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
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
      toast.success(`Đã nạp lại ${detail}.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
      toast.error(err.message || "Không nạp lại được kho tri thức.");
    } finally {
      setReindexing(false);
    }
  }

  function requestParse(doc) {
    if (!doc || parsingDocId || reindexing || parseTarget) return Promise.resolve();
    setParseTarget(doc);
    return new Promise((resolve) => { parseResolve.current = resolve; });
  }

  function closeParserSelection() {
    setParseTarget(null);
    parseResolve.current?.();
    parseResolve.current = null;
  }

  async function parseDocument(doc, parserName) {
    if (!doc || parsingDocId || reindexing) return;
    setParsingDocId(doc.id);
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${doc.id}/parse?parser_name=${encodeURIComponent(parserName)}`, { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload, "Không parse được tài liệu."));
      const label = payload.title || payload.file_name || doc.file_name;
      toast.success(`Đã parse “${label}” thành ${payload.chunk_count ?? 0} đoạn.`);
      await loadDocuments();
      onChanged?.();
    } catch (err) {
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

  function onDrop(event) {
    event.preventDefault();
    setDragOver(false);
    uploadFiles(event.dataTransfer.files);
  }

  // Màn chi tiết tài liệu, mở từ danh sách bên dưới
  const parserDialog = parseTarget && <ParserSelectionModal document={parseTarget}
    busy={Boolean(parsingDocId)} onClose={closeParserSelection}
    onConfirm={async (name) => { await parseDocument(parseTarget, name); closeParserSelection(); }} />;

  if (selectedDocId) {
    return (
      <>
      {parserDialog}
      <DocumentView
        documentId={selectedDocId}
        onBack={() => setSelectedDocId(null)}
        parsingDocId={parsingDocId}
        reindexing={reindexing}
        onParse={requestParse}
      />
      </>
    );
  }

  const selectedCount = selectedIds.size;

  return (
    <div className="dataset-wrapper">
      {parserDialog}
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

      <main
        className={`dataset-main-content ${dragOver ? "is-drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
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
                    : "Tải lên file .md, .txt, .pdf hoặc .docx để xây dựng kho tri thức cho trợ lý."}
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
                              onClick={() => requestParse(doc)}
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
