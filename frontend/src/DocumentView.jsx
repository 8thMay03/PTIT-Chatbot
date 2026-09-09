import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Play,
  Plus,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { API_BASE_URL } from "./api";
import { formatDate, formatSize, renderMarkdownHtml } from "./lib/format";

// Detail screen shown when a document is opened from the Dataset (files) list.
export default function DocumentView({
  documentId,
  onBack,
  parsingDocId,
  reindexing,
  onParse,
  onNotice,
}) {
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
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    localStorage.setItem("ptit_chunk_mode", chunkMode);
  }, [chunkMode]);

  useEffect(() => {
    if (!documentId) return;
    let cancelled = false;
    setDocDetailLoading(true);
    setDocChunksLoading(true);

    fetch(`${API_BASE_URL}/documents/${documentId}`)
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

    (async () => {
      const BATCH_SIZE = 500;
      const all = [];
      try {
        let offset = 0;
        let total = Infinity;
        while (offset < total) {
          const response = await fetch(
            `${API_BASE_URL}/documents/${documentId}/chunks?offset=${offset}&limit=${BATCH_SIZE}`
          );
          if (!response.ok) throw new Error("failed");
          const payload = await response.json();
          const list = payload.chunks ?? [];
          all.push(...list);
          total = payload.total ?? all.length;
          offset += BATCH_SIZE;
          if (list.length === 0) break;
        }
        if (!cancelled) {
          setDocChunks(all);
          setEnabledChunks((prev) => {
            const next = { ...prev };
            all.forEach((c) => {
              if (next[c.id] === undefined) next[c.id] = true;
            });
            return next;
          });
        }
      } catch {
        if (!cancelled) setDocChunks([]);
      } finally {
        if (!cancelled) setDocChunksLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [documentId, reloadToken]);

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

  async function handleReparse() {
    if (!docDetail) return;
    await onParse?.(docDetail);
    setReloadToken((t) => t + 1);
  }

  const pagedChunks = filteredChunks.slice(
    (chunkPage - 1) * chunkPageSize,
    chunkPage * chunkPageSize
  );
  const totalChunkPages = Math.ceil(filteredChunks.length / chunkPageSize) || 1;
  const isParsingThis = parsingDocId === documentId;

  return (
    <div className="doc-view-page">
      {/* Top Back Button & Re-parse Action */}
      <div className="doc-view-top-bar">
        <button type="button" className="btn-back-dataset" onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Back</span>
        </button>

        {docDetail && (
          <button
            type="button"
            className="btn-parse-dataset"
            style={{ marginLeft: "auto" }}
            onClick={handleReparse}
            disabled={isParsingThis || reindexing}
            title="Re-parse file này và cập nhật vector embeddings"
          >
            {isParsingThis ? (
              <Loader2 size={14} className="spin" />
            ) : (
              <Play size={13} fill="currentColor" />
            )}
            <span>{isParsingThis ? "Đang Parse..." : "Re-parse File"}</span>
          </button>
        )}
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
                  onClick={() => onNotice?.("Tính năng tạo chunk thủ công.")}
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
