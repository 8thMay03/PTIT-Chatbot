import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Play,
  Search,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { EMPTY, formatDate, formatSize, renderMarkdownHtml } from "./lib/format";

const PAGE_SIZES = [20, 50, 100];
const FETCH_ALL_BATCH = 500;

const VIEW_MODES = [
  { key: "full", label: "Toàn văn" },
  { key: "ellipse", label: "Rút gọn" },
  { key: "markdown", label: "Markdown" },
];

/** Màn chi tiết, mở khi bấm vào một tài liệu trong danh sách kho. */
export default function DocumentView({ documentId, onBack, parsingDocId, reindexing, onParse }) {
  const [docDetail, setDocDetail] = useState(null);
  const [docDetailLoading, setDocDetailLoading] = useState(false);
  const [docError, setDocError] = useState("");

  const [chunks, setChunks] = useState([]);
  const [chunkTotal, setChunkTotal] = useState(0);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunkError, setChunkError] = useState("");

  const [chunkMode, setChunkMode] = useState(() => {
    const saved = localStorage.getItem("ptit_chunk_mode");
    return VIEW_MODES.some((m) => m.key === saved) ? saved : "full";
  });
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [reloadToken, setReloadToken] = useState(0);
  // Chọn và bật/tắt từng đoạn: backend chưa lưu trạng thái này, nên cả hai chỉ
  // tồn tại trong phiên làm việc. Tooltip trên công tắc nói rõ điều đó.
  const [selectedChunkIds, setSelectedChunkIds] = useState(new Set());
  const [enabledChunks, setEnabledChunks] = useState({});

  // Khi tìm kiếm, phải có toàn bộ đoạn trong tay vì máy chủ chưa hỗ trợ lọc.
  const [allChunks, setAllChunks] = useState(null);
  const [loadingAll, setLoadingAll] = useState(false);

  const searchTimer = useRef(null);

  useEffect(() => {
    localStorage.setItem("ptit_chunk_mode", chunkMode);
  }, [chunkMode]);

  // Gõ tới đâu tìm tới đó sẽ gọi API liên tục — chờ người dùng ngừng gõ 350ms.
  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setSearchTerm(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(searchTimer.current);
  }, [searchInput]);

  // ---- Thông tin tài liệu ----
  useEffect(() => {
    if (!documentId) return undefined;
    let cancelled = false;
    setDocDetailLoading(true);
    setDocError("");

    fetch(`${API_BASE_URL}/documents/${documentId}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("lỗi"))))
      .then((payload) => {
        if (!cancelled) setDocDetail(payload);
      })
      .catch(() => {
        if (!cancelled) {
          setDocDetail(null);
          setDocError("Không tải được nội dung tài liệu từ máy chủ.");
        }
      })
      .finally(() => {
        if (!cancelled) setDocDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [documentId, reloadToken]);

  // ---- Các đoạn: chỉ tải đúng trang đang xem ----
  // Bản trước tải TOÀN BỘ đoạn (lô 500, lặp tới hết) ngay khi mở màn, khiến
  // tài liệu lớn phải chờ rất lâu mới hiện được gì.
  useEffect(() => {
    if (!documentId || searchTerm) return undefined;
    let cancelled = false;
    setChunksLoading(true);
    setChunkError("");

    const offset = (page - 1) * pageSize;
    fetch(`${API_BASE_URL}/documents/${documentId}/chunks?offset=${offset}&limit=${pageSize}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("lỗi"))))
      .then((payload) => {
        if (cancelled) return;
        setChunks(payload.chunks ?? []);
        setChunkTotal(payload.total ?? 0);
      })
      .catch(() => {
        if (!cancelled) {
          setChunks([]);
          setChunkError("Không tải được danh sách đoạn văn bản.");
        }
      })
      .finally(() => {
        if (!cancelled) setChunksLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [documentId, page, pageSize, searchTerm, reloadToken]);

  // ---- Tìm kiếm: nạp toàn bộ một lần rồi lọc tại chỗ ----
  const fetchAllChunks = useCallback(async () => {
    setLoadingAll(true);
    setChunkError("");
    const collected = [];
    try {
      let offset = 0;
      let total = Infinity;
      while (offset < total) {
        const response = await fetch(
          `${API_BASE_URL}/documents/${documentId}/chunks?offset=${offset}&limit=${FETCH_ALL_BATCH}`
        );
        if (!response.ok) throw new Error("lỗi");
        const payload = await response.json();
        const list = payload.chunks ?? [];
        collected.push(...list);
        total = payload.total ?? collected.length;
        offset += FETCH_ALL_BATCH;
        if (list.length === 0) break;
      }
      setAllChunks(collected);
      setChunkTotal(collected.length);
    } catch {
      setAllChunks([]);
      setChunkError("Không tải được toàn bộ đoạn để tìm kiếm.");
    } finally {
      setLoadingAll(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (searchTerm && allChunks === null && !loadingAll) fetchAllChunks();
  }, [searchTerm, allChunks, loadingAll, fetchAllChunks]);

  // Tài liệu đổi hoặc vừa parse lại thì bộ nhớ đệm tìm kiếm không còn đúng nữa
  useEffect(() => {
    setAllChunks(null);
    setPage(1);
  }, [documentId, reloadToken]);

  const searchResults = useMemo(() => {
    if (!searchTerm || !allChunks) return null;
    const needle = searchTerm.toLowerCase();
    return allChunks.filter((c) => c.text && c.text.toLowerCase().includes(needle));
  }, [searchTerm, allChunks]);

  const renderedDocHtml = useMemo(() => {
    const content = docDetail?.full_text || docDetail?.preview;
    if (!content) return "<p><em>Tài liệu chưa có nội dung văn bản.</em></p>";
    return renderMarkdownHtml(content);
  }, [docDetail?.full_text, docDetail?.preview]);

  const isSearching = Boolean(searchTerm);
  const visibleTotal = isSearching ? searchResults?.length ?? 0 : chunkTotal;
  const totalPages = Math.max(1, Math.ceil(visibleTotal / pageSize));
  const visibleChunks = isSearching
    ? (searchResults ?? []).slice((page - 1) * pageSize, page * pageSize)
    : chunks;
  const busy = chunksLoading || loadingAll;

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  function toggleSelectChunk(id) {
    setSelectedChunkIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAllChunks() {
    const ids = visibleChunks.map((c) => c.id);
    setSelectedChunkIds((prev) => {
      const next = new Set(prev);
      const allSelected = ids.length > 0 && ids.every((id) => next.has(id));
      if (allSelected) ids.forEach((id) => next.delete(id));
      else ids.forEach((id) => next.add(id));
      return next;
    });
  }

  function toggleEnableChunk(id) {
    setEnabledChunks((prev) => ({ ...prev, [id]: prev[id] === false }));
  }

  async function handleReparse() {
    if (!docDetail) return;
    await onParse?.(docDetail);
    setReloadToken((t) => t + 1);
  }

  const isParsingThis = parsingDocId === documentId;
  const fileName = docDetail?.file_name || docDetail?.title || EMPTY;

  return (
    <div className="doc-view-page">
      <div className="doc-view-top-bar">
        <button type="button" className="btn-back-dataset" onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Quay lại kho tài liệu</span>
        </button>

        {docDetail && (
          <button
            type="button"
            className="btn-parse-dataset"
            style={{ marginLeft: "auto" }}
            onClick={handleReparse}
            disabled={isParsingThis || reindexing}
            title="Parse lại file này và cập nhật vector embedding"
          >
            {isParsingThis ? <Loader2 size={14} className="spin" /> : <Play size={13} fill="currentColor" />}
            <span>{isParsingThis ? "Đang parse..." : "Parse lại"}</span>
          </button>
        )}
      </div>

      <div className="doc-view-split-layout">
        {/* ---- Cột trái: nội dung tài liệu ---- */}
        <div className="doc-view-left-col">
          <div className="doc-view-meta-header">
            <h2 className="doc-view-filename" title={fileName}>
              {fileName}
            </h2>
            <div className="doc-view-meta-info">
              <span>Dung lượng: {formatSize(docDetail?.size_bytes)}</span>
              <span className="doc-meta-sep">Tải lên: {formatDate(docDetail?.created_at)}</span>
            </div>
          </div>

          <div className="doc-view-content-pane" aria-busy={docDetailLoading}>
            {docDetailLoading ? (
              <div style={{ padding: 16 }}>
                {Array.from({ length: 10 }, (_, i) => (
                  <div
                    key={i}
                    className="skeleton skeleton-text"
                    style={{ width: `${65 + ((i * 13) % 35)}%` }}
                  />
                ))}
              </div>
            ) : docError ? (
              <div className="state-block is-error">
                <span className="state-icon">
                  <AlertTriangle size={24} />
                </span>
                <h3>Không mở được tài liệu</h3>
                <p>{docError}</p>
              </div>
            ) : (
              <div
                className="doc-markdown-rendered-view"
                dangerouslySetInnerHTML={{
                  __html: renderedDocHtml,
                }}
              />
            )}
          </div>
        </div>

        {/* ---- Cột phải: các đoạn đã chia ---- */}
        <div className="doc-view-right-col">
          <div className="chunk-result-header">
            <div className="chunk-result-title-group">
              <h3>Các đoạn đã chia</h3>
              <p>Những đoạn văn bản được dùng để nhúng vector và truy xuất khi trả lời.</p>
            </div>

            <div className="chunk-result-toolbar">
              <label className="chunk-select-all-label">
                <input
                  type="checkbox"
                  className="chunk-checkbox"
                  checked={
                    visibleChunks.length > 0 &&
                    visibleChunks.every((c) => selectedChunkIds.has(c.id))
                  }
                  onChange={toggleSelectAllChunks}
                  disabled={visibleChunks.length === 0}
                />
                <span>Chọn tất cả</span>
              </label>

              <span className="chunk-count-label">
                {busy ? "Đang tải..." : `${visibleTotal} đoạn`}
              </span>

              <div className="chunk-toolbar-right">
                <div className="chunk-mode-toggle" role="group" aria-label="Kiểu hiển thị đoạn">
                  {VIEW_MODES.map((mode) => (
                    <button
                      key={mode.key}
                      type="button"
                      className={`chunk-mode-btn ${chunkMode === mode.key ? "active" : ""}`}
                      aria-pressed={chunkMode === mode.key}
                      onClick={() => setChunkMode(mode.key)}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>

                <div className="chunk-search-field">
                  <Search size={14} className="search-icon" aria-hidden="true" />
                  <label className="sr-only" htmlFor="chunk-search">
                    Tìm trong nội dung các đoạn
                  </label>
                  <input
                    id="chunk-search"
                    type="text"
                    placeholder="Tìm trong các đoạn"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                  />
                  {searchInput && (
                    <button
                      type="button"
                      className="search-clear-btn"
                      onClick={() => setSearchInput("")}
                      aria-label="Xóa từ khóa tìm kiếm"
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="chunk-cards-container" aria-busy={busy}>
            {busy ? (
              <div style={{ padding: 4 }}>
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="skeleton" style={{ height: 96, marginBottom: 12 }} />
                ))}
              </div>
            ) : chunkError ? (
              <div className="state-block is-error">
                <span className="state-icon">
                  <AlertTriangle size={24} />
                </span>
                <h3>Không tải được các đoạn</h3>
                <p>{chunkError}</p>
              </div>
            ) : visibleChunks.length === 0 ? (
              <div className="state-block">
                <span className="state-icon">
                  <FileText size={24} />
                </span>
                <h3>{isSearching ? "Không có đoạn nào khớp" : "Tài liệu chưa được chia đoạn"}</h3>
                <p>
                  {isSearching
                    ? "Thử từ khóa khác, hoặc xóa ô tìm kiếm để xem toàn bộ."
                    : "Bấm “Parse lại” để chia tài liệu thành các đoạn và nhúng vector."}
                </p>
              </div>
            ) : (
              <div className="chunk-cards-list">
                {visibleChunks.map((chunk) => {
                  const isSelected = selectedChunkIds.has(chunk.id);
                  const isEnabled = enabledChunks[chunk.id] !== false;
                  const label = `Đoạn #${(chunk.chunk_index ?? 0) + 1}`;

                  return (
                  <div key={chunk.id} className={`chunk-card-item ${isSelected ? "selected" : ""}`}>
                    <div className="chunk-card-top">
                      <input
                        type="checkbox"
                        className="chunk-checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectChunk(chunk.id)}
                        aria-label={`Chọn ${label}`}
                      />
                      <span className="chunk-index-tag">{label}</span>
                      {chunk.token_count != null && (
                        <span className="chunk-token-tag">{chunk.token_count} token</span>
                      )}
                      <div className="chunk-card-top-right">
                        <span className="chunk-type-tag">Văn bản</span>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={isEnabled}
                          className={`pill-switch ${isEnabled ? "on" : "off"}`}
                          onClick={() => toggleEnableChunk(chunk.id)}
                          title={`${isEnabled ? "Đang bật" : "Đang tắt"} — trạng thái này chưa được máy chủ lưu lại`}
                          aria-label={`Bật/tắt ${label}`}
                        >
                          <span className="pill-switch-thumb" />
                        </button>
                      </div>
                    </div>

                    {chunkMode === "markdown" ? (
                      <div
                        className="chunk-card-markdown-view"
                        dangerouslySetInnerHTML={{ __html: renderMarkdownHtml(chunk.text) }}
                      />
                    ) : (
                      <div className={`chunk-card-text ${chunkMode === "ellipse" ? "is-ellipse" : ""}`}>
                        {chunk.text}
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            )}
          </div>

          {visibleTotal > 0 && (
            <div className="chunk-pagination-footer">
              <div className="pagination-info">
                <span>
                  Đoạn {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, visibleTotal)} trên {visibleTotal}
                </span>
              </div>

              <div className="pagination-controls">
                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={page <= 1 || busy}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  aria-label="Trang trước"
                >
                  <ChevronLeft size={14} />
                </button>

                <span className="page-current-badge" aria-live="polite">
                  {page} / {totalPages}
                </span>

                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={page >= totalPages || busy}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Trang sau"
                >
                  <ChevronRight size={14} />
                </button>

                <label className="sr-only" htmlFor="chunk-page-size">
                  Số đoạn mỗi trang
                </label>
                <select
                  id="chunk-page-size"
                  className="page-size-select"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
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
      </div>
    </div>
  );
}
