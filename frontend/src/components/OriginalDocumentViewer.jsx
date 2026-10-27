import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, Download, FileText, Loader2 } from "lucide-react";
import { describeError, documentsApi, isAbortError } from "../api";

const TEXT_TYPES = new Set(["md", "txt"]);
/** Định dạng trình duyệt tự hiển thị được khi mở tệp trong tab mới. */
export const BROWSER_VIEWABLE_TYPES = new Set(["pdf", ...TEXT_TYPES]);
// Tệp DOCX do người dùng tải lên có thể chứa liên kết javascript: — chỉ giữ giao thức an toàn.
const SAFE_HREF = /^(https?:|mailto:|#)/i;

export function documentFileUrl(documentId, { inline = false } = {}) {
  return documentsApi.fileUrl(documentId, { inline });
}

function neutralizeUnsafeLinks(root) {
  root.querySelectorAll("a[href]").forEach((link) => {
    const href = link.getAttribute("href") ?? "";
    if (!SAFE_HREF.test(href.trim())) {
      link.removeAttribute("href");
    } else if (!href.startsWith("#")) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  });
}

/** Trang DOCX có bề rộng cố định (khổ giấy): thu nhỏ cho vừa cột thay vì cuộn ngang. */
function fitDocxToWidth(container) {
  const wrapper = container.querySelector(".docx-wrapper");
  if (!wrapper) return;
  wrapper.style.zoom = "";
  const pages = Array.from(wrapper.querySelectorAll("section.docx"));
  if (pages.length === 0) return;
  const style = getComputedStyle(wrapper);
  const natural =
    Math.max(...pages.map((page) => page.offsetWidth)) +
    parseFloat(style.paddingLeft) +
    parseFloat(style.paddingRight);
  const available = container.clientWidth;
  if (natural > available && available > 0) wrapper.style.zoom = String(available / natural);
}

/**
 * Hiển thị tệp gốc của tài liệu: PDF qua trình xem PDF của trình duyệt, DOCX
 * render thành trang ngay trên trình duyệt, MD/TXT là văn bản thô.
 */
export default function OriginalDocumentViewer({ documentId, fileType, fileName }) {
  const type = (fileType || "").toLowerCase();
  const supported = type === "pdf" || type === "docx" || TEXT_TYPES.has(type);
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [text, setText] = useState(null);
  const docxRef = useRef(null);

  const inlineUrl = documentFileUrl(documentId, { inline: true });
  const downloadUrl = documentFileUrl(documentId);

  useEffect(() => {
    if (!supported) return undefined;
    const controller = new AbortController();
    setStatus("loading");
    setErrorMessage("");
    setText(null);

    (async () => {
      if (type === "pdf") {
        // Chỉ cần biết tệp còn trên máy chủ; iframe tự tải và hiển thị bằng trình xem PDF.
        const response = await documentsApi.file(documentId, {
          inline: true,
          responseType: "response",
          signal: controller.signal,
        });
        await response.body?.cancel();
      } else if (TEXT_TYPES.has(type)) {
        const content = await documentsApi.file(documentId, {
          inline: true,
          responseType: "text",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setText(content);
      } else {
        const data = await documentsApi.file(documentId, {
          inline: true,
          responseType: "arrayBuffer",
          signal: controller.signal,
        });
        const { renderAsync } = await import("docx-preview");
        const container = docxRef.current;
        if (controller.signal.aborted || !container) return;
        // Render vào phần tử mới: lượt render cũ chưa xong (đổi tài liệu) chỉ ghi vào nút đã bị gỡ.
        const target = document.createElement("div");
        container.replaceChildren(target);
        await renderAsync(data, target, target, {
          // altChunk được render thành iframe srcdoc cùng origin, có thể chạy script trong tệp.
          renderAltChunks: false,
          breakPages: true,
        });
        if (controller.signal.aborted) return;
        neutralizeUnsafeLinks(target);
        fitDocxToWidth(container);
      }
      if (!controller.signal.aborted) setStatus("ready");
    })().catch((err) => {
      if (controller.signal.aborted || isAbortError(err)) return;
      const described = describeError(err, {
        fallbackTitle: "Không hiển thị được tệp gốc",
        fallbackDetail: "Không tải được tệp gốc từ máy chủ.",
      });
      setErrorMessage(described.detail);
      setStatus("error");
    });

    return () => controller.abort();
  }, [inlineUrl, type, supported]);

  // Cột co giãn theo cửa sổ: tính lại tỉ lệ thu nhỏ của trang DOCX khi bề rộng đổi.
  useEffect(() => {
    const container = docxRef.current;
    if (type !== "docx" || status !== "ready" || !container) return undefined;
    let lastWidth = container.clientWidth;
    const observer = new ResizeObserver(() => {
      if (container.clientWidth === lastWidth) return;
      lastWidth = container.clientWidth;
      fitDocxToWidth(container);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [type, status]);

  if (!supported) {
    return (
      <div className="state-block">
        <span className="state-icon">
          <FileText size={24} />
        </span>
        <h3>Chưa xem trực tiếp được định dạng này</h3>
        <p>Tải tệp xuống để mở bằng ứng dụng phù hợp.</p>
        <a className="ghost-btn doc-original-download" href={downloadUrl}>
          <Download size={14} />
          <span>Tải xuống</span>
        </a>
      </div>
    );
  }

  return (
    <div className={`doc-original-viewer is-${type}`}>
      {status === "loading" && (
        <div className="doc-original-status" role="status">
          <Loader2 size={16} className="spin" />
          <span>Đang tải bản gốc…</span>
        </div>
      )}

      {status === "error" && (
        <div className="state-block is-error">
          <span className="state-icon">
            <AlertTriangle size={24} />
          </span>
          <h3>Không mở được bản gốc</h3>
          <p>{errorMessage}</p>
          <a className="ghost-btn doc-original-download" href={downloadUrl}>
            <Download size={14} />
            <span>Thử tải xuống</span>
          </a>
        </div>
      )}

      {type === "pdf" && status === "ready" && (
        <iframe className="doc-original-frame" src={inlineUrl} title={`Bản gốc: ${fileName}`} />
      )}

      {text !== null && status === "ready" && <pre className="doc-original-text">{text}</pre>}

      {type === "docx" && (
        <div ref={docxRef} className="doc-original-docx" hidden={status === "error"} />
      )}
    </div>
  );
}
