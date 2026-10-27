import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpDown,
  Edit3,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  FilePenLine,
  FileText,
  Loader2,
  Play,
  Plus,
  Scissors,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { describeError, documentsApi, errorMessage, queryKeys } from "./api";
import { formatDate, formatSize } from "./lib/format";
import { canEditMarkdown, documentStatus, needsChunking, NO_MARKDOWN_HINT } from "./lib/documentStatus";
import { isActiveParseJob, parseJobLabel } from "./lib/parseJobs";
import useParseJobs from "./lib/useParseJobs";
import DocumentView from "./DocumentView";
import ParserSelectionModal, { parserTitle } from "./components/ParserSelectionModal";
import MarkdownEditorView from "./components/MarkdownEditorView";
import Modal from "./components/Modal";
import ParseProgress from "./components/ParseProgress";
import { useToast } from "./components/Toast";

const ACCEPTED_TYPES =
  ".md,.txt,.pdf,.docx,text/markdown,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const PAGE_SIZES = [10, 20, 50, 100];
const NO_DOCUMENTS = [];

function fileExtension(name) {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot).toLowerCase() : "";
}

/** Parser khả dụng theo đuôi file, hỏi backend một lần cho mỗi đuôi. */
async function loadParsersByExtension(files) {
  const samples = new Map(files.map((file) => [fileExtension(file.name), file.name]));
  const entries = await Promise.all([...samples].map(async ([ext, name]) => {
    const payload = await documentsApi.parsersForFile(name);
    return [ext, payload.parsers || []];
  }));
  return Object.fromEntries(entries);
}

export default function DatasetView() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedDocId, setSelectedDocId] = useState(null);
  // Tài liệu đang mở màn sửa Markdown trực tiếp từ danh sách.
  const [markdownDoc, setMarkdownDoc] = useState(null);

  const documentsQuery = useQuery({
    queryKey: queryKeys.documentList,
    queryFn: ({ signal }) => documentsApi.list({ signal }),
  });
  const documents = documentsQuery.data?.documents ?? NO_DOCUMENTS;
  const loading = documentsQuery.isPending;
  const loadError = documentsQuery.error
    ? describeError(documentsQuery.error, {
        fallbackTitle: "Không tải được danh sách tài liệu",
        fallbackDetail: "Máy chủ trả về lỗi khi lấy danh sách tài liệu.",
      })
    : null;
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
  const [uploadTarget, setUploadTarget] = useState(null);
  const [uploadProgress, setUploadProgress] = useState("");
  const [reindexing, setReindexing] = useState(false);
  const [rechunking, setRechunking] = useState(false);
  const [parseTarget, setParseTarget] = useState(null);
  const parseResolve = useRef(null);
  const [parseSubmitting, setParseSubmitting] = useState(false);
  const [chunkingDocId, setChunkingDocId] = useState(null);
  // Parse chạy nền không còn khóa màn hình; chỉ nạp lại/chia đoạn đồng bộ vẫn
  // giữ khóa để tránh hai thao tác cùng ghi vào kho.
  const pipelineBusy = reindexing || rechunking || Boolean(chunkingDocId);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const fileRef = useRef(null);

  // Danh sách, chi tiết và các đoạn đều nằm dưới tiền tố `["documents"]`, nên một
  // lần invalidate sau thao tác ghi là mọi màn đang mở cùng cập nhật.
  const refreshDocuments = useCallback(
    () => queryClient.invalidateQueries({ queryKey: queryKeys.documents }),
    [queryClient]
  );

  const handleParseJobFinished = useCallback(
    (job) => {
      const label = parseJobLabel(job);
      if (job.status === "succeeded") {
        if (job.kind === "upload" || needsChunking(job.result)) {
          toast.success(`Đã parse “${label}”. Bấm “Chia đoạn” để kho tri thức dùng bản mới.`);
        } else {
          toast.success(`Đã parse “${label}”; nội dung không đổi nên các đoạn hiện có vẫn khớp.`);
        }
        refreshDocuments();
      } else if (job.status === "failed") {
        toast.error(`Parse “${label}” thất bại: ${job.error || "lỗi không xác định"}`);
      }
    },
    [toast, refreshDocuments]
  );

  // Job nền nằm ở backend; hook tự nạp lại và poll khi còn job đang chạy.
  const { jobs: parseJobs, track: trackParseJobs } = useParseJobs({
    onFinished: handleParseJobFinished,
  });
  const activeParseJobs = useMemo(() => parseJobs.filter(isActiveParseJob), [parseJobs]);
  const parseJobByDocument = useMemo(() => {
    const map = new Map();
    for (const job of activeParseJobs) {
      if (job.document_id) map.set(job.document_id, job);
    }
    return map;
  }, [activeParseJobs]);
  const activeParseSummary = useMemo(() => {
    const labels = activeParseJobs.slice(0, 3).map(parseJobLabel);
    const extra = activeParseJobs.length - labels.length;
    return `${labels.join(", ")}${extra > 0 ? ` và ${extra} tài liệu khác` : ""}`;
  }, [activeParseJobs]);
  const runningParseJob = useMemo(
    () => activeParseJobs.find((job) => job.status === "running") ?? activeParseJobs[0] ?? null,
    [activeParseJobs]
  );

  useEffect(() => {
    setEnabledDocs((prev) => {
      const next = { ...prev };
      documents.forEach((doc) => {
        if (next[doc.id] === undefined) next[doc.id] = true;
      });
      return next;
    });
  }, [documents]);

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

  // Chỉ hỏi chọn parser khi có tệp nhận được hơn một parser (vd. PDF/Word khi bật
  // LlamaParse); còn lại tải lên ngay với parser mặc định như trước.
  async function requestUpload(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length || uploading || uploadTarget) return;

    setUploading(true);
    let parsersByExt = {};
    try {
      parsersByExt = await loadParsersByExtension(files);
    } catch {
      // Không lấy được danh sách: để backend dùng parser mặc định và báo lỗi theo từng tệp.
    }
    const choosable = files.filter((file) => (parsersByExt[fileExtension(file.name)] || []).length > 1);
    if (!choosable.length) {
      await uploadFiles(files);
      return;
    }

    const parsers = [];
    for (const file of choosable) {
      for (const parser of parsersByExt[fileExtension(file.name)]) {
        const existing = parsers.find((item) => item.name === parser.name);
        if (existing) existing.is_default ||= parser.is_default;
        else parsers.push({ ...parser });
      }
    }
    setUploading(false);
    setUploadTarget({ files, parsers, parsersByExt, choiceCount: choosable.length });
  }

  async function confirmUpload(parserName) {
    const { files, parsersByExt } = uploadTarget;
    await uploadFiles(files, parserName, parsersByExt);
    setUploadTarget(null);
  }

  async function uploadFiles(files, parserName = null, parsersByExt = {}) {
    setUploading(true);
    const failures = [];
    const jobs = [];

    for (const [index, file] of files.entries()) {
      setUploadProgress(files.length > 1 ? `${index + 1}/${files.length}` : "");
      // Tệp không hỗ trợ parser đã chọn (vd. .md khi chọn LlamaParse) giữ parser mặc định.
      const chosenParser =
        parserName &&
        (parsersByExt[fileExtension(file.name)] || []).some((item) => item.name === parserName)
          ? parserName
          : null;
      try {
        const job = await documentsApi.upload(file, { parserName: chosenParser });
        jobs.push(job);
      } catch (err) {
        failures.push(`${file.name}: ${errorMessage(err, "không tải lên được")}`);
      }
    }

    setUploading(false);
    setUploadProgress("");

    if (jobs.length) {
      trackParseJobs(jobs);
      toast.info(
        `Đã đưa ${jobs.length} tài liệu${parserName ? ` (${parserTitle(parserName)})` : ""} vào hàng đợi parse nền. ` +
          "Bạn có thể tiếp tục làm việc khác; tài liệu sẽ xuất hiện khi parse xong."
      );
    }
    if (failures.length) {
      toast.warning(
        `${jobs.length ? `Đã đưa ${jobs.length} tài liệu vào hàng đợi. ` : ""}` +
          `${failures.length} file bị lỗi: ${failures.join(" · ")}`
      );
    } else if (!jobs.length) {
      toast.error("Không tải lên được tài liệu nào.");
    }
  }

  async function deleteDocument(doc) {
    await documentsApi.remove(doc.id);
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
      await refreshDocuments();
    } catch (err) {
      toast.error(errorMessage(err, `Không xóa được “${label}”.`));
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
        failures.push(
          `${doc.title || doc.file_name}: ${errorMessage(err, "không xóa được")}`
        );
      }
    }

    if (failures.length) toast.warning(`Đã xóa ${done}/${targets.length}. Lỗi: ${failures.join(" · ")}`);
    else toast.success(`Đã xóa ${done} tài liệu.`);

    setSelectedIds(new Set());
    setBulkDeleteOpen(false);
    setDeleting(false);
    await refreshDocuments();
  }

  async function reindexAll() {
    if (pipelineBusy || activeParseJobs.length > 0) return;
    setReindexing(true);
    try {
      const payload = await documentsApi.reindex();
      const detail = `${payload.documents ?? 0} tài liệu · ${payload.chunks ?? 0} đoạn`;
      toast.success(`Đã nạp lại ${detail}.`);
      await refreshDocuments();
    } catch (err) {
      toast.error(errorMessage(err, "Không nạp lại được kho tri thức."));
    } finally {
      setReindexing(false);
    }
  }

  async function rechunkAll() {
    if (pipelineBusy || activeParseJobs.length > 0) return;
    setRechunking(true);
    try {
      const payload = await documentsApi.rechunk();
      const detail = `${payload.documents ?? 0} tài liệu · ${payload.chunks ?? 0} đoạn`;
      if (payload.skipped) {
        toast.warning(
          `Đã chia đoạn lại ${detail}. Bỏ qua ${payload.skipped} tài liệu chưa có bản parse đã lưu — hãy parse lại chúng.`
        );
      } else {
        toast.success(`Đã chia đoạn lại ${detail}.`);
      }
      await refreshDocuments();
    } catch (err) {
      toast.error(errorMessage(err, "Không chia đoạn lại được kho tri thức."));
    } finally {
      setRechunking(false);
    }
  }

  function requestParse(doc) {
    if (!doc || pipelineBusy || parseTarget || parseJobByDocument.has(doc.id)) return Promise.resolve();
    setParseTarget(doc);
    return new Promise((resolve) => { parseResolve.current = resolve; });
  }

  function closeParserSelection() {
    setParseTarget(null);
    parseResolve.current?.();
    parseResolve.current = null;
  }

  async function parseDocument(doc, parserName) {
    if (!doc || pipelineBusy || parseJobByDocument.has(doc.id)) return;
    setParseSubmitting(true);
    try {
      const job = await documentsApi.parse(doc.id, parserName);
      trackParseJobs(job);
      toast.info(
        `Đang parse lại “${parseJobLabel(job)}” ở chế độ nền. Bạn có thể tiếp tục làm việc khác.`
      );
    } catch (err) {
      toast.error(errorMessage(err, "Không bắt đầu được job parse."));
    } finally {
      setParseSubmitting(false);
    }
  }

  async function chunkDocument(doc) {
    if (!doc || pipelineBusy || parseJobByDocument.has(doc.id)) return;
    setChunkingDocId(doc.id);
    try {
      const payload = await documentsApi.chunk(doc.id);
      const label = payload.title || payload.file_name || doc.file_name;
      toast.success(`Đã chia “${label}” thành ${payload.chunk_count ?? 0} đoạn.`);
      await refreshDocuments();
    } catch (err) {
      toast.error(errorMessage(err, "Lỗi khi chia đoạn tài liệu."));
    } finally {
      setChunkingDocId(null);
    }
  }

  async function downloadDocument(doc) {
    try {
      const blob = await documentsApi.file(doc.id, { responseType: "blob" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = doc.file_name || "tai-lieu";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(errorMessage(err, "Không tải được file nguồn."));
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDragOver(false);
    requestUpload(event.dataTransfer.files);
  }

  // Màn chi tiết tài liệu, mở từ danh sách bên dưới
  const parserDialog = parseTarget && <ParserSelectionModal document={parseTarget}
    busy={parseSubmitting} onClose={closeParserSelection}
    onConfirm={async (name) => { await parseDocument(parseTarget, name); closeParserSelection(); }} />;

  const uploadDialog = uploadTarget && <ParserSelectionModal upload={uploadTarget}
    busy={uploading} progress={uploadProgress} onClose={() => setUploadTarget(null)} onConfirm={confirmUpload} />;

  if (markdownDoc) {
    return (
      <MarkdownEditorView
        documentId={markdownDoc.id}
        fileName={markdownDoc.file_name || markdownDoc.title}
        fileType={markdownDoc.file_type}
        backLabel="Quay lại kho tài liệu"
        onClose={(saved) => {
          setMarkdownDoc(null);
          if (saved) refreshDocuments();
        }}
      />
    );
  }

  if (selectedDocId) {
    return (
      <>
      {parserDialog}
      <DocumentView
        documentId={selectedDocId}
        onBack={() => setSelectedDocId(null)}
        busy={pipelineBusy}
        parseJob={parseJobByDocument.get(selectedDocId) ?? null}
        chunkingDocId={chunkingDocId}
        onParse={requestParse}
        onChunk={chunkDocument}
      />
      </>
    );
  }

  const selectedCount = selectedIds.size;

  return (
    <div className="dataset-wrapper">
      {parserDialog}
      {uploadDialog}
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED_TYPES}
        multiple
        hidden
        onChange={(e) => {
          requestUpload(e.target.files);
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
              <p>Tài liệu được parse khi tải lên; chỉ dùng được khi hỏi đáp sau khi đã chia đoạn.</p>
            </div>

            <div className="dataset-view-toolbar">
              <button
                type="button"
                className="btn-outline-dataset"
                title={
                  activeParseJobs.length > 0
                    ? "Chờ các job parse nền đang chạy xong trước khi chia đoạn lại toàn bộ"
                    : "Chia đoạn và nhúng vector lại mọi tài liệu từ bản Markdown đã lưu, không parse lại (dùng sau khi đổi cấu hình chia đoạn)"
                }
                onClick={rechunkAll}
                disabled={pipelineBusy || activeParseJobs.length > 0}
              >
                {rechunking ? <Loader2 size={14} className="spin" /> : <Scissors size={14} />}
                <span>{rechunking ? "Đang chia đoạn..." : "Chia đoạn lại toàn bộ"}</span>
              </button>

              <button
                type="button"
                className="btn-parse-dataset"
                title={
                  activeParseJobs.length > 0
                    ? "Chờ các job parse nền đang chạy xong trước khi nạp lại toàn bộ"
                    : "Parse lại mọi file gốc rồi chia đoạn và nhúng vector; bản Markdown đã sửa tay được giữ nguyên"
                }
                onClick={reindexAll}
                disabled={pipelineBusy || activeParseJobs.length > 0}
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

          {activeParseJobs.length > 0 && (
            <div className="inline-alert is-info parse-jobs-banner" role="status" style={{ marginBottom: 12 }}>
              <Loader2 size={16} className="spin" />
              <div className="parse-jobs-banner-body">
                <span>
                  Đang xử lý nền {activeParseJobs.length} tài liệu
                  {activeParseSummary ? `: ${activeParseSummary}` : ""}. Bạn có thể tiếp tục xem, sửa
                  hoặc thao tác trên tài liệu khác.
                </span>
                {runningParseJob && (
                  <ParseProgress
                    progress={runningParseJob.progress}
                    message={runningParseJob.progress_message}
                    label={parseJobLabel(runningParseJob)}
                    indeterminate={
                      runningParseJob.status === "queued" || !runningParseJob.progress
                    }
                  />
                )}
              </div>
            </div>
          )}

          {loadError && (
            <div className="inline-alert is-error" role="alert" style={{ marginBottom: 12 }}>
              <AlertTriangle size={16} />
              <span>
                {loadError.title}. {loadError.detail}
              </span>
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
                    const parseJob = parseJobByDocument.get(doc.id);
                    const isParsing = Boolean(parseJob);
                    const isChunking = chunkingDocId === doc.id;
                    const rowBusy = pipelineBusy || isParsing || isChunking;
                    const isEnabled = enabledDocs[doc.id] !== false;
                    const status = documentStatus(doc);

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
                          {isParsing ? (
                            <div className="doc-status-stack">
                              <span
                                className="doc-status-badge is-parsing"
                                title="Đang parse trong nền; bạn vẫn có thể làm việc khác"
                              >
                                Đang parse
                              </span>
                              <ParseProgress
                                compact
                                progress={parseJob.progress}
                                message={parseJob.progress_message}
                                label="Tiến trình"
                                indeterminate={parseJob.status === "queued" || !parseJob.progress}
                              />
                            </div>
                          ) : (
                            <span className={`doc-status-badge is-${status.key}`} title={status.hint}>
                              {status.label}
                            </span>
                          )}
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
                              title={isParsing ? `Đang parse ${fileName} trong nền` : `Parse lại ${fileName}`}
                              aria-label={`Parse lại ${fileName}`}
                              onClick={() => requestParse(doc)}
                              disabled={rowBusy}
                            >
                              {isParsing ? <Loader2 size={14} className="spin" /> : <Play size={13} fill="currentColor" />}
                            </button>
                            <button
                              type="button"
                              className={`act-btn ${needsChunking(doc) ? "is-attention" : ""}`}
                              title={
                                isParsing
                                  ? "Chờ parse nền xong rồi chia đoạn"
                                  : `${needsChunking(doc) ? "Chia đoạn" : "Chia đoạn lại"} ${fileName}`
                              }
                              aria-label={`Chia đoạn ${fileName}`}
                              onClick={() => chunkDocument(doc)}
                              disabled={rowBusy}
                            >
                              {isChunking ? <Loader2 size={14} className="spin" /> : <Scissors size={14} />}
                            </button>
                            <button
                              type="button"
                              className="act-btn"
                              title={canEditMarkdown(doc) ? `Sửa Markdown của ${fileName}` : NO_MARKDOWN_HINT}
                              aria-label={`Sửa Markdown của ${fileName}`}
                              onClick={() => setMarkdownDoc(doc)}
                              disabled={rowBusy || !canEditMarkdown(doc)}
                            >
                              <FilePenLine size={14} />
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
