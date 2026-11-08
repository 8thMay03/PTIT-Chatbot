const CITATION_RE = /\[(\d{1,3})\]/g;
// Chip `[n]` không được render trong code (plugin markdown chạy ở bộ parse), nên bỏ
// code block và inline code trước khi tìm.
const FENCED_CODE_RE = /```[\s\S]*?```|~~~[\s\S]*?~~~/g;
const INLINE_CODE_RE = /`[^`\n]*`/g;

/**
 * Câu trả lời có ít nhất một `[n]` trỏ tới một nguồn trong `sources` hay không.
 *
 * Dùng để ghi nhãn khối nguồn (RAG-22): có chip trích dẫn hợp lệ thì là "Nguồn trích
 * dẫn", ngược lại backend chỉ trả các nguồn liên quan đã dùng làm ngữ cảnh.
 * Module nhẹ, không import `lib/markdown.js` (được tải lazy cùng MarkdownView).
 */
export function hasCitedSource(content, sources) {
  if (!content || !sources?.length) return false;
  const ids = new Set(sources.map((source) => String(source?.citation_id)));
  const prose = String(content).replace(FENCED_CODE_RE, " ").replace(INLINE_CODE_RE, " ");
  for (const match of prose.matchAll(CITATION_RE)) {
    if (ids.has(match[1])) return true;
  }
  return false;
}

export function sourcesLabel(content, sources) {
  return hasCitedSource(content, sources) ? "Nguồn trích dẫn" : "Nguồn liên quan";
}
