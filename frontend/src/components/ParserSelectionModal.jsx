import React, { useEffect, useState } from "react";
import Modal from "./Modal";
import { API_BASE_URL } from "../api";
import { apiError } from "../lib/format";
import { FileText, Layers, Loader2, AlertCircle, RefreshCw, ArrowRight, Info } from "lucide-react";
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

export default function ParserSelectionModal({ document, busy, onClose, onConfirm }) {
  const [parsers, setParsers] = useState([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSelected("");
    fetch(`${API_BASE_URL}/documents/${document.id}/parsers`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(apiError(payload, "Không tải được danh sách parser."));
        if (controller.signal.aborted) return;
        const options = payload.parsers || [];
        setParsers(options);
        setSelected((options.find((item) => item.is_default) || options[0])?.name || "");
      })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [document.id, attempt]);

  return (
    <Modal open onClose={() => { if (!busy) onClose(); }} title="Chọn cách xử lý tài liệu"
      icon={<Layers size={22} />}
      description="Chọn parser phù hợp để tạo nội dung cho kho tri thức."
      actions={<>
        <button className="ghost-btn parser-cancel" type="button" disabled={busy} onClick={onClose}>Hủy</button>
        <button className="primary-btn" type="button" disabled={busy || loading || Boolean(error) || !selected}
          onClick={() => onConfirm(selected)}>{busy ? <Loader2 size={16} className="parser-spinner" /> : <ArrowRight size={16} />}
          {busy ? "Đang xử lý..." : "Bắt đầu parse"}</button>
      </>}>
      <div className="parser-selection" aria-busy={busy || loading}>
        <div className="parser-document">
          <FileText size={20} aria-hidden="true" />
          <div><span>Tài liệu được chọn</span><strong>{document.file_name || document.title}</strong></div>
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
            return <label className={`parser-card ${selected === parser.name ? "is-selected" : ""}`} key={parser.name}>
              <input type="radio" name={`parser-${document.id}`} value={parser.name}
                checked={selected === parser.name} onChange={() => setSelected(parser.name)} />
              <span className="parser-card-content">
                <span className="parser-card-heading"><strong>{details?.title || parser.name}</strong>
                  {parser.is_default && <span className="parser-badge">Mặc định</span>}
                  {details?.badge && <span className="parser-badge">{details.badge}</span>}</span>
                <span className="parser-card-description">{details?.description || "Xử lý tài liệu bằng parser này."}</span>
              </span>
            </label>;
          })}
        </fieldset> : <div className="parser-state" role="alert"><AlertCircle size={24} /><strong>Chưa có parser tương thích</strong><p>Định dạng tài liệu này chưa được hỗ trợ.</p></div>)}
        {!loading && !error && parsers.length > 0 && <div className="parser-notice" role={busy ? "status" : undefined}>
          {busy ? <Loader2 size={16} className="parser-spinner" /> : <Info size={16} />}
          <span>{busy ? "Đang xử lý và cập nhật kho tri thức. PDF lớn có thể mất vài phút; vui lòng chờ hoàn tất." : "Parse lại sẽ cập nhật các đoạn nội dung và dữ liệu tìm kiếm của tài liệu này."}</span>
        </div>}
      </div>
    </Modal>
  );
}
