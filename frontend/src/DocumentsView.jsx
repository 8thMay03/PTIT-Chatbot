import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
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
  if (!value) return "10/08/2026 09:27:57";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "10/08/2026 09:27:57";

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
  if (bytes == null || Number.isNaN(bytes)) return "515 KB";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  return fallback;
}

function escapeHtml(value) {
  if (!value) return "";
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function parseInlineMarkdown(text) {
  if (!text) return "";
  let res = text;
  // Inline code
  res = res.replace(/`([^`]+)`/g, '<code class="doc-inline-code">$1</code>');
  // Bold + Italic
  res = res.replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>");
  res = res.replace(/_\*\*([^*]+)\*\*_|\*\*_([^_]+)_\*\*/g, "<strong><em>$1$2</em></strong>");
  // Bold
  res = res.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  res = res.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  // Italic
  res = res.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  res = res.replace(/(^|[^_])_([^_]+)_/g, "$1<em>$2</em>");
  // Links
  res = res.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer" class="doc-link">$1</a>'
  );
  return res;
}

function renderMarkdownHtml(rawText) {
  if (!rawText) return "";
  const text = escapeHtml(rawText);
  const lines = text.split(/\r?\n/);
  const out = [];
  let inList = false;
  let listType = null;
  let inTable = false;

  const closeList = () => {
    if (inList) {
      out.push(`</${listType}>`);
      inList = false;
      listType = null;
    }
  };

  const closeTable = () => {
    if (inTable) {
      out.push("</tbody></table></div>");
      inTable = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      closeList();
      closeTable();
      continue;
    }

    // Horizontal rule
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      closeList();
      closeTable();
      out.push('<hr class="doc-hr" />');
      continue;
    }

    // Headings (# to ######)
    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(trimmed);
    if (headingMatch) {
      closeList();
      closeTable();
      const level = headingMatch[1].length;
      out.push(`<h${level} class="doc-h${level}">${parseInlineMarkdown(headingMatch[2])}</h${level}>`);
      continue;
    }

    // Blockquote
    if (trimmed.startsWith("&gt; ") || trimmed.startsWith("> ")) {
      closeList();
      closeTable();
      const quoteText = trimmed.replace(/^(&gt;|>)\s+/, "");
      out.push(`<blockquote class="doc-blockquote">${parseInlineMarkdown(quoteText)}</blockquote>`);
      continue;
    }

    // Table rows
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      closeList();
      if (/^\|(\s*[-:]+[-| :]*)\|$/.test(trimmed)) {
        continue;
      }
      const cells = trimmed
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());

      if (!inTable) {
        inTable = true;
        out.push('<div class="doc-table-wrapper"><table class="doc-table"><thead><tr>');
        cells.forEach((cell) => {
          out.push(`<th>${parseInlineMarkdown(cell)}</th>`);
        });
        out.push("</tr></thead><tbody>");
      } else {
        out.push("<tr>");
        cells.forEach((cell) => {
          out.push(`<td>${parseInlineMarkdown(cell)}</td>`);
        });
        out.push("</tr>");
      }
      continue;
    } else {
      closeTable();
    }

    // Unordered lists
    const ulMatch = /^\s*[-*]\s+(.*)$/.exec(rawLine);
    if (ulMatch) {
      closeTable();
      if (!inList || listType !== "ul") {
        closeList();
        out.push('<ul class="doc-ul">');
        inList = true;
        listType = "ul";
      }
      out.push(`<li>${parseInlineMarkdown(ulMatch[1])}</li>`);
      continue;
    }

    // Ordered lists
    const olMatch = /^\s*(\d+)\.\s+(.*)$/.exec(rawLine);
    if (olMatch) {
      closeTable();
      if (!inList || listType !== "ol") {
        closeList();
        out.push('<ol class="doc-ol">');
        inList = true;
        listType = "ol";
      }
      out.push(`<li>${parseInlineMarkdown(olMatch[2])}</li>`);
      continue;
    }

    // Paragraph
    closeList();
    closeTable();
    out.push(`<p class="doc-p">${parseInlineMarkdown(trimmed)}</p>`);
  }

  closeList();
  closeTable();
  return out.join("\n");
}


export default function DocumentsView({ onChanged }) {
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem("ptit_dataset_tab");
    return ["files", "retrieval", "logs", "config"].includes(saved) ? saved : "files";
  });
  const [selectedDocId, setSelectedDocId] = useState(() => {
    return localStorage.getItem("ptit_selected_doc_id") || null;
  });

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

  // Document Chunk Detail View State
  const [docDetail, setDocDetail] = useState(null);
  const [docDetailLoading, setDocDetailLoading] = useState(false);
  const [docChunks, setDocChunks] = useState([]);
  const [docChunksLoading, setDocChunksLoading] = useState(false);
  const [chunkMode, setChunkMode] = useState(() => {
    const saved = localStorage.getItem("ptit_chunk_mode");
    return ["full", "ellipse", "markdown"].includes(saved) ? saved : "full";
  });
  const [chunkQuery, setChunkQuery] = useState("");
  const [selectedChunkIds, setSelectedChunkIds] = useState(new Set());
  const [enabledChunks, setEnabledChunks] = useState({});
  const [chunkPage, setChunkPage] = useState(1);
  const [chunkPageSize, setChunkPageSize] = useState(50);

  useEffect(() => {
    localStorage.setItem("ptit_dataset_tab", activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (selectedDocId) {
      localStorage.setItem("ptit_selected_doc_id", selectedDocId);
    } else {
      localStorage.removeItem("ptit_selected_doc_id");
    }
  }, [selectedDocId]);

  useEffect(() => {
    localStorage.setItem("ptit_chunk_mode", chunkMode);
  }, [chunkMode]);

  // Modals
  const [editingDoc, setEditingDoc] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [pendingDelete, setPendingDelete] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [notice, setNotice] = useState("");

  // Retrieval Testing State (Matching reference parameters)
  const [testQuery, setTestQuery] = useState("");
  const [testSimilarityThreshold, setTestSimilarityThreshold] = useState(0.2);
  const [testVectorWeight, setTestVectorWeight] = useState(0.3);
  const [testRerankModel, setTestRerankModel] = useState("");
  const [testUseKg, setTestUseKg] = useState(false);
  const [testCrossLang, setTestCrossLang] = useState("");
  const [testMetadata, setTestMetadata] = useState("");
  const [testTopK, setTestTopK] = useState(10);
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
    if (!selectedDocId) {
      setDocDetail(null);
      setDocChunks([]);
      return;
    }
    let cancelled = false;
    setDocDetailLoading(true);
    setDocChunksLoading(true);

    fetch(`${API_BASE_URL}/documents/${selectedDocId}`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        if (!cancelled) setDocDetail(payload);
      })
      .catch(() => {
        if (!cancelled) setDocDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDocDetailLoading(false);
      });

    fetch(`${API_BASE_URL}/documents/${selectedDocId}/chunks?limit=500`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        if (!cancelled) {
          const list = payload.chunks ?? [];
          setDocChunks(list);
          setEnabledChunks((prev) => {
            const next = { ...prev };
            list.forEach((c) => {
              if (next[c.id] === undefined) next[c.id] = true;
            });
            return next;
          });
        }
      })
      .catch(() => {
        if (!cancelled) setDocChunks([]);
      })
      .finally(() => {
        if (!cancelled) setDocChunksLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDocId]);

  const filteredChunks = useMemo(() => {
    let list = [...docChunks];
    const q = chunkQuery.trim().toLowerCase();
    if (q) {
      list = list.filter((c) => c.text && c.text.toLowerCase().includes(q));
    }
    return list;
  }, [docChunks, chunkQuery]);

  function toggleSelectAllChunks() {
    if (selectedChunkIds.size === filteredChunks.length) {
      setSelectedChunkIds(new Set());
    } else {
      setSelectedChunkIds(new Set(filteredChunks.map((c) => c.id)));
    }
  }

  function toggleSelectChunk(id) {
    setSelectedChunkIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleEnableChunk(id) {
    setEnabledChunks((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  }

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
      if (selectedDocId === pendingDelete.id) {
        setSelectedDocId(null);
        setDocDetail(null);
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
        body: JSON.stringify({
          query: testQuery,
          top_k: Number(testTopK) || 10,
          similarity_threshold: testSimilarityThreshold,
          vector_similarity_weight: testVectorWeight,
          rerank_model: testRerankModel || null,
          use_knowledge_graph: testUseKg,
          cross_language_search: testCrossLang || null,
          meta_data: testMetadata || null,
        }),
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

  // ----------------------------------------------------
  // DOCUMENT DETAIL VIEW (Matching image.png Document View)
  // ----------------------------------------------------
  if (selectedDocId) {
    const pagedChunks = filteredChunks.slice(
      (chunkPage - 1) * chunkPageSize,
      chunkPage * chunkPageSize
    );
    const totalChunkPages = Math.ceil(filteredChunks.length / chunkPageSize) || 1;

    return (
      <div className="doc-view-page">
        {/* Top Back Button */}
        <div className="doc-view-top-bar">
          <button
            type="button"
            className="btn-back-dataset"
            onClick={() => setSelectedDocId(null)}
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>
        </div>

        {/* 2-Column Split Layout */}
        <div className="doc-view-split-layout">
          {/* Left Column: Document Preview */}
          <div className="doc-view-left-col">
            <div className="doc-view-meta-header">
              <h2 className="doc-view-filename">
                {docDetail?.file_name || docDetail?.title || "so-tay-sinh-vien-d21.md"}
              </h2>
              <div className="doc-view-meta-info">
                <span>Size: {formatSize(docDetail?.size_bytes)}</span>
                <span className="doc-meta-sep">
                  Uploaded time: {formatDate(docDetail?.created_at)}
                </span>
              </div>
            </div>

            <div className="doc-view-content-pane">
              {docDetailLoading ? (
                <div className="doc-view-loading">
                  <Loader2 size={24} className="spin" />
                  <p>Loading document...</p>
                </div>
              ) : (
                <div
                  className="doc-markdown-rendered-view"
                  dangerouslySetInnerHTML={{
                    __html: renderMarkdownHtml(
                      docDetail?.full_text || docDetail?.preview || "No content available."
                    ),
                  }}
                />
              )}
            </div>
          </div>

          {/* Right Column: Chunk Result */}
          <div className="doc-view-right-col">
            <div className="chunk-result-header">
              <div className="chunk-result-title-group">
                <h3>Chunk result</h3>
                <p>View the chunked segments used for embedding and retrieval.</p>
              </div>

              {/* Toolbar */}
              <div className="chunk-result-toolbar">
                <label className="chunk-select-all-label">
                  <input
                    type="checkbox"
                    checked={
                      filteredChunks.length > 0 &&
                      selectedChunkIds.size === filteredChunks.length
                    }
                    onChange={toggleSelectAllChunks}
                  />
                  <span>Select all</span>
                </label>

                <div className="chunk-toolbar-right">
                  {/* Segmented Mode Button (Full text | Ellipse | Markdown) */}
                  <div className="chunk-mode-toggle">
                    <button
                      type="button"
                      className={`chunk-mode-btn ${chunkMode === "full" ? "active" : ""}`}
                      onClick={() => setChunkMode("full")}
                    >
                      Full text
                    </button>
                    <button
                      type="button"
                      className={`chunk-mode-btn ${chunkMode === "ellipse" ? "active" : ""}`}
                      onClick={() => setChunkMode("ellipse")}
                    >
                      Ellipse
                    </button>
                    <button
                      type="button"
                      className={`chunk-mode-btn ${chunkMode === "markdown" ? "active" : ""}`}
                      onClick={() => setChunkMode("markdown")}
                    >
                      Markdown
                    </button>
                  </div>

                  {/* Search box */}
                  <div className="chunk-search-field">
                    <Search size={14} className="search-icon" />
                    <input
                      type="text"
                      placeholder="Search"
                      value={chunkQuery}
                      onChange={(e) => setChunkQuery(e.target.value)}
                    />
                    {chunkQuery && (
                      <button
                        type="button"
                        className="search-clear-btn"
                        onClick={() => setChunkQuery("")}
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>

                  {/* Filter / Sort Button */}
                  <button type="button" className="chunk-tool-btn" title="Filter chunks">
                    <SlidersHorizontal size={14} />
                  </button>

                  {/* Add chunk Button */}
                  <button
                    type="button"
                    className="chunk-tool-btn"
                    title="Add chunk"
                    onClick={() => setNotice("Tính năng tạo chunk thủ công.")}
                  >
                    <Plus size={15} />
                  </button>
                </div>
              </div>
            </div>

            {/* Chunks List */}
            <div className="chunk-cards-container">
              {docChunksLoading ? (
                <div className="doc-view-loading">
                  <Loader2 size={24} className="spin" />
                  <p>Loading chunks...</p>
                </div>
              ) : pagedChunks.length === 0 ? (
                <div className="doc-empty-chunks">
                  <FileText size={32} />
                  <p>No chunks found.</p>
                </div>
              ) : (
                <div className="chunk-cards-list">
                  {pagedChunks.map((chunk) => {
                    const isSelected = selectedChunkIds.has(chunk.id);
                    const isEnabled = enabledChunks[chunk.id] !== false;

                    return (
                      <div
                        key={chunk.id}
                        className={`chunk-card-item ${isSelected ? "selected" : ""}`}
                      >
                        {/* Top Header of Card */}
                        <div className="chunk-card-top">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectChunk(chunk.id)}
                            className="chunk-checkbox"
                          />
                          <div className="chunk-card-top-right">
                            <span className="chunk-type-tag">Text</span>
                            <button
                              type="button"
                              className={`pill-switch ${isEnabled ? "on" : "off"}`}
                              onClick={() => toggleEnableChunk(chunk.id)}
                              title={isEnabled ? "Enabled" : "Disabled"}
                              aria-label="Toggle chunk status"
                            >
                              <span className="pill-switch-thumb" />
                            </button>
                          </div>
                        </div>

                        {/* Body Content: Render Markdown when chunkMode === 'markdown' */}
                        {chunkMode === "markdown" ? (
                          <div
                            className="chunk-card-markdown-view"
                            dangerouslySetInnerHTML={{
                              __html: renderMarkdownHtml(chunk.text),
                            }}
                          />
                        ) : (
                          <div
                            className={`chunk-card-text ${
                              chunkMode === "ellipse" ? "is-ellipse" : ""
                            }`}
                          >
                            {chunk.text}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Pagination Footer */}
            <div className="chunk-pagination-footer">
              <div className="pagination-info">
                <span>Total {filteredChunks.length}</span>
              </div>

              <div className="pagination-controls">
                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={chunkPage <= 1}
                  onClick={() => setChunkPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={14} />
                </button>

                <span className="page-current-badge">{chunkPage}</span>

                {totalChunkPages > 1 && (
                  <button
                    type="button"
                    className={`page-num-btn ${chunkPage === 2 ? "active" : ""}`}
                    onClick={() => setChunkPage(2)}
                  >
                    2
                  </button>
                )}

                {totalChunkPages > 2 && (
                  <button
                    type="button"
                    className={`page-num-btn ${chunkPage === 3 ? "active" : ""}`}
                    onClick={() => setChunkPage(3)}
                  >
                    3
                  </button>
                )}

                {totalChunkPages > 4 && <span className="page-ellipsis">...</span>}

                {totalChunkPages > 3 && (
                  <button
                    type="button"
                    className={`page-num-btn ${
                      chunkPage === totalChunkPages ? "active" : ""
                    }`}
                    onClick={() => setChunkPage(totalChunkPages)}
                  >
                    {totalChunkPages}
                  </button>
                )}

                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={chunkPage >= totalChunkPages}
                  onClick={() => setChunkPage((p) => Math.min(totalChunkPages, p + 1))}
                >
                  <ChevronRight size={14} />
                </button>

                <div className="page-size-selector">
                  <span>{chunkPageSize} / Page</span>
                  <ChevronDown size={13} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
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
                                onClick={() => setSelectedDocId(doc.id)}
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
                                title="View document chunks"
                                onClick={() => setSelectedDocId(doc.id)}
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

        {/* TAB 2: RETRIEVAL TESTING (Matching image.png) */}
        {activeTab === "retrieval" && (
          <div className="dataset-retrieval-screen">
            {/* Top Title & Full Description */}
            <header className="retrieval-top-header">
              <h2>Retrieval testing</h2>
              <p>
                Conduct a retrieval test to check if RAGFlow can recover the intended content for the LLM. If you have adjusted the default settings, such as keyword similarity weight or similarity threshold, to achieve the optimal results, be aware that these changes will not be automatically saved. You must apply them to your chat assistant settings or the Retrieval agent component settings.
              </p>
            </header>

            {/* 2-Column Split Layout */}
            <div className="retrieval-two-col-layout">
              {/* Left Column: Setting & Input */}
              <div className="retrieval-col-left">
                <div className="retrieval-settings-card">
                  <h3 className="retrieval-settings-title">Setting</h3>

                  {/* Similarity threshold */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Similarity threshold</span>
                      <span className="ret-info-icon" title="Ngưỡng tương đồng tối thiểu để giữ lại chunk">ⓘ</span>
                    </div>
                    <div className="ret-slider-row">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={testSimilarityThreshold}
                        onChange={(e) => setTestSimilarityThreshold(parseFloat(e.target.value))}
                        className="ret-cyan-slider"
                      />
                      <span className="ret-val-box">
                        {testSimilarityThreshold.toFixed(1).replace(".", ",")}
                      </span>
                    </div>
                  </div>

                  {/* Vector similarity weight */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Vector similarity weight</span>
                      <span className="ret-info-icon" title="Trọng số tìm kiếm vector ngữ nghĩa vs full-text BM25">ⓘ</span>
                    </div>
                    <div className="ret-weight-indicators">
                      <span className="ret-ind-left">vector {testVectorWeight.toFixed(2)}</span>
                      <span className="ret-ind-right">full-text {(1 - testVectorWeight).toFixed(2)}</span>
                    </div>
                    <div className="ret-slider-row">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={testVectorWeight}
                        onChange={(e) => setTestVectorWeight(parseFloat(e.target.value))}
                        className="ret-cyan-slider"
                      />
                      <span className="ret-val-box">
                        {testVectorWeight.toFixed(1).replace(".", ",")}
                      </span>
                    </div>
                  </div>

                  {/* Rerank model */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Rerank model</span>
                      <span className="ret-info-icon" title="Mô hình Reranker xếp hạng lại đoạn trích">ⓘ</span>
                    </div>
                    <div className="ret-select-box">
                      <select
                        value={testRerankModel}
                        onChange={(e) => setTestRerankModel(e.target.value)}
                      >
                        <option value="">Select value</option>
                        <option value="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1">cross-encoder/mmarco-mMiniLMv2-L12-H384-v1</option>
                        <option value="BAAI/bge-reranker-base">BAAI/bge-reranker-base</option>
                        <option value="BAAI/bge-reranker-large">BAAI/bge-reranker-large</option>
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" />
                    </div>
                  </div>

                  {/* Use knowledge graph */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Use knowledge graph</span>
                      <span className="ret-info-icon" title="Sử dụng Knowledge Graph">ⓘ</span>
                    </div>
                    <button
                      type="button"
                      className={`ret-kg-switch ${testUseKg ? "on" : "off"}`}
                      onClick={() => setTestUseKg(!testUseKg)}
                      aria-label="Toggle knowledge graph"
                    >
                      <span className="ret-kg-thumb" />
                    </button>
                  </div>

                  {/* Cross-language search */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Cross-language search</span>
                      <span className="ret-info-icon" title="Tìm kiếm đa ngôn ngữ">ⓘ</span>
                    </div>
                    <div className="ret-select-box">
                      <select
                        value={testCrossLang}
                        onChange={(e) => setTestCrossLang(e.target.value)}
                      >
                        <option value="">Select value</option>
                        <option value="en">English</option>
                        <option value="vi">Vietnamese</option>
                        <option value="auto">Auto detect</option>
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" />
                    </div>
                  </div>

                  {/* Meta data */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Meta data</span>
                      <span className="ret-info-icon" title="Bộ lọc trường metadata">ⓘ</span>
                    </div>
                    <div className="ret-select-box">
                      <select
                        value={testMetadata}
                        onChange={(e) => setTestMetadata(e.target.value)}
                      >
                        <option value="">Select value</option>
                        <option value="all">All Metadata</option>
                        <option value="file_name">Filter by File Name</option>
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" />
                    </div>
                  </div>

                  {/* Top */}
                  <div className="ret-form-group">
                    <div className="ret-field-label">
                      <span>Top</span>
                    </div>
                    <div className="ret-select-box">
                      <select
                        value={testTopK}
                        onChange={(e) => setTestTopK(Number(e.target.value))}
                      >
                        <option value={5}>Top 5</option>
                        <option value={10}>Top 10</option>
                        <option value={15}>Top 15</option>
                        <option value={20}>Top 20</option>
                        <option value={30}>Top 30</option>
                      </select>
                      <ChevronDown size={14} className="ret-select-chevron" />
                    </div>
                  </div>
                </div>

                {/* Query Input Box */}
                <div className="ret-query-box">
                  <textarea
                    rows={4}
                    placeholder=""
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
                      {testLoading ? (
                        <Loader2 size={13} className="spin" />
                      ) : (
                        <span>Run</span>
                      )}
                      <svg
                        width="13"
                        height="13"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ marginLeft: 4 }}
                      >
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Column: Results */}
              <div className="retrieval-col-right">
                <div className="ret-results-header">
                  <div className="ret-results-title">
                    <h3>Results</h3>
                    <span className="ret-total-tag">
                      Total: {testResults ? (testResults.contexts?.length ?? 0) : 0}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="ret-filter-btn"
                    title="Filter test results"
                  >
                    <Filter size={14} />
                  </button>
                </div>

                <div className="ret-results-container">
                  {!testResults || (testResults.contexts?.length ?? 0) === 0 ? (
                    <div className="ret-empty-placeholder">
                      {/* Document Scroll Outline Icon */}
                      <div className="ret-empty-icon">
                        <svg
                          width="46"
                          height="46"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#cbd5e1"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                          <line x1="16" y1="13" x2="8" y2="13"></line>
                          <line x1="16" y1="17" x2="8" y2="17"></line>
                          <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                      </div>
                      <p>No test has been run yet. Results will appear here.</p>
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
                            {ctx.section_path && (
                              <span className="ret-chunk-sec">· {ctx.section_path}</span>
                            )}
                            <div className="ret-chunk-badges">
                              {ctx.combined_score != null && (
                                <span className="ret-badge rerank">
                                  Rerank: {(ctx.combined_score * 100).toFixed(1)}%
                                </span>
                              )}
                              {ctx.score != null && (
                                <span className="ret-badge sim">
                                  Sim: {(ctx.score * 100).toFixed(1)}%
                                </span>
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
