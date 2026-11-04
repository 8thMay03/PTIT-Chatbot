import React, { useEffect, useState } from "react";
import Modal from "./Modal";
import { documentsApi, errorMessage, isAbortError } from "../api";
import { FileText, Layers, Loader2, AlertCircle, AlertTriangle, RefreshCw, ArrowRight, Info, Upload } from "lucide-react";
import "../styles/parser-selection.css";

const PARSER_DETAILS = {
  docling: { title: "Docling", description: "Chuyển PDF và Word thành văn bản, giữ tiêu đề và cấu trúc bảng." },
  text: { title: "Text", description: "Đọc trực tiếp nội dung Markdown và văn bản UTF-8." },
  llamaparse: {
    title: "LlamaParse",
    badge: "Cloud",
    description: "Parse PDF và Word bằng dịch vụ LlamaParse, phù hợp file scan, bảng phức tạp hoặc có watermark. File được gửi lên LlamaCloud và tốn credit theo số trang.",
  },
};

// Tier LlamaParse, rẻ nhất trước; credit/trang theo bảng giá LlamaCloud.
const VARIANT_DETAILS = {
  fast: { title: "Fast", credits: 1, description: "Chỉ lấy văn bản, nhanh nhất" },
  cost_effective: { title: "Cost effective", credits: 3, description: "Cân bằng chất lượng và chi phí" },
  agentic: { title: "Agentic", credits: 10, description: "Bảng, scan và bố cục phức tạp" },
  agentic_plus: { title: "Agentic Plus", credits: 45, description: "Chính xác nhất cho tài liệu khó" },
};

const FILE_PREVIEW_LIMIT = 3;

/** Tên parser có thể kèm tùy chọn dạng "llamaparse:agentic". */
export function parserBaseName(name) {
  return (name || "").split(":")[0];
}

export function parserTitle(name) {
  const [base, variant] = (name || "").split(":");
  const title = PARSER_DETAILS[base]?.title || base;
  return variant ? `${title} · ${VARIANT_DETAILS[variant]?.title || variant}` : title;
}

function defaultParser(options) {
  return (options.find((item) => item.is_default) || options[0])?.name || "";
}

function defaultVariants(options) {
  return Object.fromEntries(options.filter((item) => item.variants?.length)
    .map((item) => [item.name, item.default_variant || item.variants[0]]));
}

/**
 * Chọn parser cho một tài liệu đã có (`document`, tự tải danh sách parser)
 * hoặc cho các tệp sắp tải lên (`upload`: { files, parsers, choiceCount }).
 */
export default function ParserSelectionModal({ document, upload, busy, progress, onClose, onConfirm }) {
  const [parsers, setParsers] = useState(() => upload?.parsers || []);
  const [selected, setSelected] = useState(() => (upload ? defaultParser(upload.parsers) : ""));
  const [variants, setVariants] = useState(() => (upload ? defaultVariants(upload.parsers) : {}));
  const [loading, setLoading] = useState(!upload);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const documentId = document?.id;

  useEffect(() => {
    if (!documentId) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSelected("");
    documentsApi
      .parsersForDocument(documentId, { signal: controller.signal })
      .then((payload) => {
        if (controller.signal.aborted) return;
        const options = payload.parsers || [];
        setParsers(options);
        setSelected(defaultParser(options));
        setVariants(defaultVariants(options));
      })
      .catch((err) => {
        if (controller.signal.aborted || isAbortError(err)) return;
        setError(errorMessage(err, "Không tải được danh sách parser."));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [documentId, attempt]);

  const selectedVariant = variants[selected];
  const choice = selectedVariant ? `${selected}:${selectedVariant}` : selected;
  const files = upload?.files || [];
  const otherCount = files.length - (upload?.choiceCount ?? files.length);
  const busyText = upload
    ? `Đang tải tệp lên${progress ? ` (${progress})` : ""}. Parse sẽ chạy nền sau khi tải xong.`
    : "Đang đưa tài liệu vào hàng đợi parse nền...";
  // Parse lại ghi đè bản Markdown đã sửa tay: cảnh báo trước khi người dùng xác nhận.
  const overwritesEdit = !upload && Boolean(document?.markdown_edited);
  let idleText = "Parse lại chạy ở chế độ nền: bạn có thể tiếp tục làm việc khác. Các đoạn hiện có vẫn được dùng khi hỏi đáp tới khi bấm “Chia đoạn”.";
  if (upload) {
    idleText = `Tài liệu được đưa vào hàng đợi parse ngay sau khi tải lên${otherCount > 0 ? `; ${otherCount} tệp không hỗ trợ parser này sẽ dùng parser mặc định` : ""}, rồi chờ bạn kiểm tra Markdown và bấm “Chia đoạn”. Có thể parse lại bằng parser khác sau.`;
  } else if (overwritesEdit) {
    idleText = "Tài liệu này có bản Markdown đã sửa tay; parse lại sẽ ghi đè các chỉnh sửa đó. Job chạy nền, các đoạn hiện có vẫn được dùng khi hỏi đáp tới khi bấm “Chia đoạn”.";
  }

  return (
    <Modal open onClose={() => { if (!busy) onClose(); }}
      title={upload ? "Chọn parser cho tài liệu tải lên" : "Chọn cách xử lý tài liệu"}
      icon={upload ? <Upload size={22} /> : <Layers size={22} />}
      description="Chọn parser phù hợp để tạo nội dung cho kho tri thức."
      actions={<>
        <button className="ghost-btn parser-cancel" type="button" disabled={busy} onClick={onClose}>Hủy</button>
        <button className="primary-btn" type="button" disabled={busy || loading || Boolean(error) || !selected}
          onClick={() => onConfirm(choice)}>{busy ? <Loader2 size={16} className="parser-spinner" /> : <ArrowRight size={16} />}
          {busy ? "Đang xử lý..." : upload ? "Tải lên và parse" : "Bắt đầu parse"}</button>
      </>}>
      <div className="parser-selection" aria-busy={busy || loading}>
        <div className="parser-document">
          <FileText size={20} aria-hidden="true" />
          {upload ? <div>
            <span>{files.length > 1 ? `${files.length} tệp được chọn` : "Tệp được chọn"}</span>
            {files.slice(0, FILE_PREVIEW_LIMIT).map((file, index) => <strong key={`${file.name}-${index}`}>{file.name}</strong>)}
            {files.length > FILE_PREVIEW_LIMIT && <span className="parser-document-more">và {files.length - FILE_PREVIEW_LIMIT} tệp khác</span>}
          </div> : <div><span>Tài liệu được chọn</span><strong>{document.file_name || document.title}</strong></div>}
        </div>
        {loading && <div className="parser-state" role="status"><Loader2 className="parser-spinner" size={20} />Đang tìm parser tương thích...</div>}
        {error && <div className="parser-state parser-error" role="alert">
          <AlertCircle size={22} /><strong>Không tải được danh sách parser</strong><p>{error}</p>
          <button className="ghost-btn parser-cancel" type="button" onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={14} />Thử lại</button>
        </div>}
        {!loading && !error && (parsers.length ? <fieldset className="parser-options" disabled={busy}>
          <legend>Parser khả dụng <span>{parsers.length}</span></legend>
          {parsers.map((parser) => {
            const details = PARSER_DETAILS[parser.name];
            const isSelected = selected === parser.name;
            const card = <label className={`parser-card ${isSelected ? "is-selected" : ""}`} key={parser.name}>
              <input type="radio" name={`parser-${documentId || "upload"}`} value={parser.name}
                checked={isSelected} onChange={() => setSelected(parser.name)} />
              <span className="parser-card-content">
                <span className="parser-card-heading"><strong>{details?.title || parser.name}</strong>
                  {parser.is_default && <span className="parser-badge">Mặc định</span>}
                  {details?.badge && <span className="parser-badge">{details.badge}</span>}</span>
                <span className="parser-card-description">{details?.description || "Xử lý tài liệu bằng parser này."}</span>
              </span>
            </label>;
            if (!isSelected || !parser.variants?.length) return card;
            return <React.Fragment key={parser.name}>
              {card}
              <div className="parser-variants" role="radiogroup" aria-label={`Chế độ ${details?.title || parser.name}`}>
                {parser.variants.map((variant) => {
                  const info = VARIANT_DETAILS[variant];
                  const checked = variants[parser.name] === variant;
                  return <label className={`parser-variant ${checked ? "is-selected" : ""}`} key={variant}>
                    <input type="radio" name={`parser-variant-${documentId || "upload"}`} value={variant} checked={checked}
                      onChange={() => setVariants((current) => ({ ...current, [parser.name]: variant }))} />
                    <span className="parser-variant-heading"><strong>{info?.title || variant}</strong>
                      {variant === parser.default_variant && <span className="parser-badge">Mặc định</span>}</span>
                    {info && <span className="parser-variant-credits">{info.credits} credit/trang</span>}
                    {info && <span className="parser-variant-description">{info.description}</span>}
                  </label>;
                })}
              </div>
            </React.Fragment>;
          })}
        </fieldset> : <div className="parser-state" role="alert"><AlertCircle size={24} /><strong>Chưa có parser tương thích</strong><p>Định dạng tài liệu này chưa được hỗ trợ.</p></div>)}
        {!loading && !error && parsers.length > 0 && <div className={`parser-notice ${overwritesEdit && !busy ? "is-warning" : ""}`} role={busy ? "status" : undefined}>
          {busy ? <Loader2 size={16} className="parser-spinner" /> : overwritesEdit ? <AlertTriangle size={16} /> : <Info size={16} />}
          <span>{busy ? busyText : idleText}</span>
        </div>}
      </div>
    </Modal>
  );
}
