import React, { memo, useMemo } from "react";
import { renderMarkdownHtml } from "../lib/markdown";

/**
 * Một chỗ render Markdown duy nhất cho chat và màn tài liệu.
 *
 * HTML đã được `markdown-it` + `DOMPurify` xử lý trong `lib/markdown.js`;
 * component này chỉ memo hóa kết quả để màn tài liệu không render lại toàn văn
 * mỗi khi hover một đoạn.
 */
function MarkdownView({ content, sources, className = "" }) {
  const html = useMemo(() => renderMarkdownHtml(content, sources), [content, sources]);

  return <div className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

export default memo(MarkdownView);
