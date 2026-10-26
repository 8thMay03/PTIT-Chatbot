import React, { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, ExternalLink, Info, Loader2, RefreshCw, RotateCcw, Save } from "lucide-react";
import { API_BASE_URL } from "../api";
import { apiError } from "../lib/format";
import MarkdownView from "./MarkdownView";
import Modal from "./Modal";
import OriginalDocumentViewer, { BROWSER_VIEWABLE_TYPES, documentFileUrl } from "./OriginalDocumentViewer";
import { useToast } from "./Toast";
import "../styles/markdown-editor.css";

const PANES = [
  { key: "original", label: "Bản gốc", title: "Tệp gốc đã tải lên (cuộn riêng)" },
  { key: "raw", label: "Markdown thô", title: "Bản Markdown để sửa" },
  { key: "rendered", label: "Bản render", title: "Markdown sau khi render" },
];
const PANES_STORAGE_KEY = "ptit_md_editor_panes";

function savedPanes() {
  try {
    const saved = JSON.parse(localStorage.getItem(PANES_STORAGE_KEY));
    const keys = PANES.map((pane) => pane.key).filter((key) => Array.isArray(saved) && saved.includes(key));
    if (keys.length) return keys;
  } catch {
    // Giá trị hỏng hoặc không đọc được localStorage: hiện đủ ba cột.
  }
  return PANES.map((pane) => pane.key);
}

async function requestJson(url, options, fallback) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(apiError(payload, fallback));
  return payload;
}

/**
 * Sửa tay bản Markdown đã parse khi parser đọc sai, đối chiếu ba cột: bản gốc,
 * Markdown thô (nơi sửa) và bản render. Lưu chỉ cập nhật Markdown; kho tri thức chỉ
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
  const [syncScroll, setSyncScroll] = useState(true);
  const [visiblePanes, setVisiblePanes] = useState(savedPanes);
  // Render tài liệu dài tốn thời gian: bản render đi sau một nhịp để gõ không bị giật.
  const previewText = useDeferredValue(text);
  const editorRef = useRef(null);
  const previewRef = useRef(null);
  const echoFrom = useRef(null);

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
    requestJson(
      `${API_BASE_URL}/documents/${documentId}/markdown`,
      { signal: controller.signal },
      "Không tải được bản Markdown của tài liệu."
    )
      .then((payload) => {
        if (controller.signal.aborted) return;
        setStored(payload);
        setText(payload.text);
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setLoadError(err instanceof TypeError ? "Không kết nối được máy chủ." : err.message);
        }
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
      const payload = await requestJson(
        `${API_BASE_URL}/documents/${documentId}/markdown`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, base_hash: stored.content_hash }),
        },
        "Không lưu được Markdown."
      );
      setStored(payload);
      setSavedCount((count) => count + 1);
      toast.success("Đã lưu Markdown. Bấm “Chia đoạn” để kho tri thức dùng bản mới.");
    } catch (err) {
      toast.error(err instanceof TypeError ? "Không kết nối được máy chủ." : err.message);
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
  function mirrorScroll(from) {
    if (echoFrom.current === from) {
      echoFrom.current = null;
      return;
    }
    if (!syncScroll) return;
    const source = from === "editor" ? editorRef.current : previewRef.current;
    const target = from === "editor" ? previewRef.current : editorRef.current;
    if (!source || !target) return;
    const range = source.scrollHeight - source.clientHeight;
    const ratio = range > 0 ? source.scrollTop / range : 0;
    const next = Math.round(ratio * (target.scrollHeight - target.clientHeight));
    if (Math.abs(target.scrollTop - next) < 2) return;
    echoFrom.current = from === "editor" ? "preview" : "editor";
    target.scrollTop = next;
  }

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
              Đối chiếu bản gốc với bản render rồi sửa ở cột <strong>Markdown thô</strong> (bản mà bước chia đoạn sẽ
              đọc). Lưu xong, bấm <strong>Chia đoạn</strong> cho tài liệu này để kho tri thức dùng bản mới. Parse
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

            {visiblePanes.includes("raw") && (
              <section className="md-editor-pane" aria-label="Markdown thô">
                <header className="md-editor-pane-header">
                  <span className="md-editor-pane-title">Markdown thô</span>
                  <span>
                    {stats.lines} dòng · {stats.chars} ký tự
                  </span>
                </header>
                <textarea
                  ref={editorRef}
                  className="md-editor-textarea"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  onScroll={() => mirrorScroll("editor")}
                  readOnly={saving}
                  spellCheck={false}
                  aria-label="Nội dung Markdown"
                />
              </section>
            )}

            {visiblePanes.includes("rendered") && (
              <section className="md-editor-pane" aria-label="Bản render">
                <header className="md-editor-pane-header">
                  <span className="md-editor-pane-title">Bản render</span>
                  {visiblePanes.includes("raw") && (
                    <label className="md-editor-sync">
                      <input
                        type="checkbox"
                        checked={syncScroll}
                        onChange={(event) => setSyncScroll(event.target.checked)}
                      />
                      Cuộn đồng bộ
                    </label>
                  )}
                </header>
                <div ref={previewRef} className="md-editor-preview" onScroll={() => mirrorScroll("preview")}>
                  <MarkdownView
                    className="doc-markdown-rendered-view"
                    content={previewText || "*Markdown đang trống.*"}
                  />
                </div>
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
