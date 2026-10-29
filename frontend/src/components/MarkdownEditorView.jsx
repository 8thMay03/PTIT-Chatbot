import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  Eye,
  Info,
  Loader2,
  Pencil,
  RefreshCw,
  RotateCcw,
  Save,
} from "lucide-react";
import { describeError, documentsApi, errorMessage, isAbortError } from "../api";
import MarkdownView from "./MarkdownView";
import Modal from "./Modal";
import OriginalDocumentViewer, { BROWSER_VIEWABLE_TYPES, documentFileUrl } from "./OriginalDocumentViewer";
import { useToast } from "./Toast";
import "../styles/markdown-editor.css";

const PANES = [
  { key: "original", label: "Bản gốc", title: "Tệp gốc đã tải lên (cuộn riêng)" },
  { key: "markdown", label: "Markdown", title: "Markdown thô (nơi sửa) hoặc bản render" },
];
const PANES_STORAGE_KEY = "ptit_md_editor_panes";

function savedPanes() {
  try {
    const saved = JSON.parse(localStorage.getItem(PANES_STORAGE_KEY));
    // Bản cũ lưu hai cột "raw"/"rendered" riêng; nay gộp thành cột "markdown".
    const migrated = Array.isArray(saved)
      ? saved.map((key) => (key === "raw" || key === "rendered" ? "markdown" : key))
      : [];
    const keys = PANES.map((pane) => pane.key).filter((key) => migrated.includes(key));
    if (keys.length) return keys;
  } catch {
    // Giá trị hỏng hoặc không đọc được localStorage: hiện đủ các cột.
  }
  return PANES.map((pane) => pane.key);
}

function scrollRatio(element) {
  if (!element) return 0;
  const range = element.scrollHeight - element.clientHeight;
  return range > 0 ? element.scrollTop / range : 0;
}

/**
 * Sửa tay bản Markdown đã parse khi parser đọc sai, đối chiếu bản gốc với cột Markdown;
 * cột Markdown chuyển qua lại giữa Markdown thô (nơi sửa) và bản render bằng một nút. Lưu chỉ cập nhật Markdown; kho tri thức chỉ
 * dùng bản mới sau khi bấm "Chia đoạn", giống như sau khi parse.
 */
export default function MarkdownEditorView({
  documentId,
  fileName,
  fileType,
  backLabel = "Quay lại tài liệu",
  onClose,
}) {
  const toast = useToast();
  // Bản đã lưu trên máy chủ; content_hash gửi kèm khi lưu để phát hiện thay đổi từ nơi khác.
  const [stored, setStored] = useState(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [savedCount, setSavedCount] = useState(0);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [visiblePanes, setVisiblePanes] = useState(savedPanes);
  // "raw": sửa Markdown thô; "rendered": xem bản render. Luôn mở ở chế độ sửa.
  const [markdownMode, setMarkdownMode] = useState("raw");
  const editorRef = useRef(null);
  const previewRef = useRef(null);
  // Vị trí cuộn tương đối của chế độ vừa rời, áp cho chế độ mới để giữ đúng đoạn đang xem.
  const pendingScroll = useRef(null);
  const rendered = markdownMode === "rendered";

  const dirty = stored !== null && text !== stored.text;
  const originalType = (fileType || fileName?.split(".").pop() || "").toLowerCase();

  useEffect(() => {
    try {
      localStorage.setItem(PANES_STORAGE_KEY, JSON.stringify(visiblePanes));
    } catch {
      // Không lưu được lựa chọn cột thì lần sau hiện mặc định.
    }
  }, [visiblePanes]);

  // Luôn giữ ít nhất một cột; thứ tự cột cố định theo PANES.
  function togglePane(key) {
    setVisiblePanes((current) => {
      if (current.includes(key)) return current.length > 1 ? current.filter((item) => item !== key) : current;
      return PANES.map((pane) => pane.key).filter((item) => item === key || current.includes(item));
    });
  }
  const stats = useMemo(
    () => ({ lines: text ? text.split("\n").length : 0, chars: text.length.toLocaleString("vi-VN") }),
    [text]
  );

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError("");
    documentsApi
      .markdown(documentId, { signal: controller.signal })
      .then((payload) => {
        if (controller.signal.aborted) return;
        setStored(payload);
        setText(payload.text);
      })
      .catch((err) => {
        if (controller.signal.aborted || isAbortError(err)) return;
        setLoadError(
          describeError(err, {
            fallbackTitle: "Không tải được bản Markdown",
            fallbackDetail: "Không tải được bản Markdown của tài liệu.",
          }).detail
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [documentId, attempt]);

  // Đóng tab hoặc tải lại trang khi còn thay đổi chưa lưu.
  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = useCallback(async () => {
    if (!dirty || saving) return;
    if (!text.trim()) {
      toast.error("Markdown không được để trống.");
      return;
    }
    setSaving(true);
    try {
      const payload = await documentsApi.saveMarkdown(documentId, {
        text,
        baseHash: stored.content_hash,
      });
      setStored(payload);
      setSavedCount((count) => count + 1);
      toast.success("Đã lưu Markdown. Bấm “Chia đoạn” để kho tri thức dùng bản mới.");
    } catch (err) {
      if (isAbortError(err)) return;
      toast.error(errorMessage(err, "Không lưu được Markdown."));
    } finally {
      setSaving(false);
    }
  }, [dirty, saving, text, stored, documentId, toast]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        save();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [save]);

  function requestClose() {
    if (dirty) setConfirmLeave(true);
    else onClose(savedCount > 0);
  }

  // Cuộn theo tỉ lệ: Markdown thô và bản render dài khác nhau nên chỉ khớp tương đối.
  function toggleMarkdownMode() {
    pendingScroll.current = scrollRatio(rendered ? previewRef.current : editorRef.current);
    setMarkdownMode(rendered ? "raw" : "rendered");
  }

  useLayoutEffect(() => {
    const ratio = pendingScroll.current;
    const target = rendered ? previewRef.current : editorRef.current;
    if (ratio === null || !target) return;
    pendingScroll.current = null;
    target.scrollTop = Math.round(ratio * (target.scrollHeight - target.clientHeight));
  }, [rendered]);

  let stateLabel = stored?.markdown_edited ? "Bản đã sửa tay" : "Bản do parser tạo";
  if (saving) stateLabel = "Đang lưu...";
  else if (dirty) stateLabel = "Có thay đổi chưa lưu";
  else if (savedCount) stateLabel = "Đã lưu";

  return (
    <div className="md-editor-page">
      <div className="md-editor-top-bar">
        <button type="button" className="btn-back-dataset" onClick={requestClose}>
          <ArrowLeft size={14} />
          <span>{backLabel}</span>
        </button>
        <div className="md-editor-title">
          <h2>Sửa Markdown</h2>
          <span title={fileName}>{fileName}</span>
        </div>
        <div className="chunk-mode-toggle md-editor-pane-toggle" role="group" aria-label="Cột hiển thị">
          {PANES.map((pane) => {
            const shown = visiblePanes.includes(pane.key);
            return (
              <button
                key={pane.key}
                type="button"
                className={`chunk-mode-btn ${shown ? "active" : ""}`}
                aria-pressed={shown}
                title={shown && visiblePanes.length === 1 ? "Cần hiện ít nhất một cột" : pane.title}
                onClick={() => togglePane(pane.key)}
              >
                {pane.label}
              </button>
            );
          })}
        </div>
        {stored && (
          <div className="md-editor-actions">
            <span className={`md-editor-state ${dirty ? "is-dirty" : ""}`} role="status">
              {stateLabel}
            </span>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setText(stored.text)}
              disabled={!dirty || saving}
              title="Bỏ các thay đổi chưa lưu"
            >
              <RotateCcw size={14} />
              Hoàn tác
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={save}
              disabled={!dirty || saving}
              title="Lưu Markdown (Ctrl+S)"
            >
              {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
              Lưu
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="state-block" aria-busy="true">
          <Loader2 size={22} className="spin" />
          <p>Đang tải bản Markdown...</p>
        </div>
      ) : loadError ? (
        <div className="state-block is-error" role="alert">
          <span className="state-icon">
            <AlertTriangle size={24} />
          </span>
          <h3>Không mở được trình sửa</h3>
          <p>{loadError}</p>
          <button type="button" className="ghost-btn" onClick={() => setAttempt((value) => value + 1)}>
            <RefreshCw size={14} />
            Thử lại
          </button>
        </div>
      ) : (
        <>
          <div className="inline-alert is-info md-editor-note">
            <Info size={16} />
            <span>
              Đối chiếu bản gốc với bản render rồi sửa ở <strong>Markdown thô</strong> (bản mà bước chia đoạn sẽ
              đọc); nút <strong>Xem bản render</strong>/<strong>Sửa Markdown</strong> chuyển qua lại giữa hai bản. Lưu xong, bấm <strong>Chia đoạn</strong> cho tài liệu này để kho tri thức dùng bản mới. Parse
              lại tài liệu sẽ ghi đè các chỉnh sửa này.
            </span>
          </div>

          <div className="md-editor-panes" style={{ "--md-editor-pane-count": visiblePanes.length }}>
            {visiblePanes.includes("original") && (
              <section className="md-editor-pane" aria-label="Bản gốc">
                <header className="md-editor-pane-header">
                  <span className="md-editor-pane-title">Bản gốc</span>
                  <span className="md-editor-pane-tools">
                    {originalType && <span>.{originalType} · cuộn riêng</span>}
                    {BROWSER_VIEWABLE_TYPES.has(originalType) && (
                      <a
                        className="md-editor-open-original"
                        href={documentFileUrl(documentId, { inline: true })}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Mở bản gốc trong tab mới"
                        aria-label="Mở bản gốc trong tab mới"
                      >
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </span>
                </header>
                <div className="md-editor-original">
                  <OriginalDocumentViewer documentId={documentId} fileType={originalType} fileName={fileName} />
                </div>
              </section>
            )}

            {visiblePanes.includes("markdown") && (
              <section className="md-editor-pane" aria-label="Markdown">
                <header className="md-editor-pane-header">
                  <span className="md-editor-pane-title">{rendered ? "Bản render" : "Markdown thô"}</span>
                  <span className="md-editor-pane-tools">
                    <span>
                      {stats.lines} dòng · {stats.chars} ký tự
                    </span>
                    <button
                      type="button"
                      className="ghost-btn md-editor-mode-btn"
                      onClick={toggleMarkdownMode}
                      title={rendered ? "Quay lại sửa Markdown thô" : "Xem Markdown sau khi render"}
                    >
                      {rendered ? <Pencil size={13} /> : <Eye size={13} />}
                      {rendered ? "Sửa Markdown" : "Xem bản render"}
                    </button>
                  </span>
                </header>
                {/* Ô sửa luôn được giữ (chỉ ẩn) để không mất lịch sử hoàn tác của trình duyệt. */}
                <textarea
                  ref={editorRef}
                  className="md-editor-textarea"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  hidden={rendered}
                  readOnly={saving}
                  spellCheck={false}
                  aria-label="Nội dung Markdown"
                />
                {rendered && (
                  <div ref={previewRef} className="md-editor-preview">
                    <MarkdownView className="doc-markdown-rendered-view" content={text || "*Markdown đang trống.*"} />
                  </div>
                )}
              </section>
            )}
          </div>
        </>
      )}

      <Modal
        open={confirmLeave}
        onClose={() => setConfirmLeave(false)}
        title="Bỏ thay đổi chưa lưu?"
        description="Các chỉnh sửa Markdown chưa lưu sẽ mất khi rời trình sửa."
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setConfirmLeave(false)}>
              Ở lại
            </button>
            <button
              type="button"
              className="danger-btn"
              onClick={() => {
                setConfirmLeave(false);
                onClose(savedCount > 0);
              }}
            >
              Bỏ thay đổi
            </button>
          </>
        }
      />
    </div>
  );
}
