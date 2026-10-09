/** Ký hiệu dùng khi không có dữ liệu. Không bao giờ bịa giá trị thay thế. */
export const EMPTY = "—";

export function formatDate(value) {
  if (!value) return EMPTY;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return EMPTY;

  const pad = (n) => String(n).padStart(2, "0");
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
}

export function formatDateOnly(value) {
  if (!value) return EMPTY;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return EMPTY;
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

export function formatSize(bytes) {
  if (bytes == null || Number.isNaN(Number(bytes))) return EMPTY;
  const value = Number(bytes);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(0)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  return fallback;
}

function escapeHtml(value) {
  if (!value) return "";
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Chỉ cho phép link http/https/mailto.
 *
 * Kết quả được nhét vào innerHTML, nên một link dạng `javascript:` trong nội dung
 * tài liệu hoặc trong câu trả lời của LLM sẽ chạy được mã trong trang.
 */
function safeHref(url) {
  const trimmed = (url || "").trim();
  return /^(https?:\/\/|mailto:|#|\/)/i.test(trimmed) ? trimmed : "#";
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
    (_match, label, url) =>
      `<a href="${safeHref(url)}" target="_blank" rel="noreferrer noopener" class="doc-link">${label}</a>`
  );
  // Khôi phục các thẻ inline an toàn nếu có (ví dụ <s>, <b>, <i>, <u>, <br>, <sub>, <sup>)
  res = res.replace(/&lt;(\/?(?:b|strong|i|em|s|del|u|sub|sup|mark|code|br\s*\/?))&gt;/gi, "<$1>");
  return res;
}

/**
 * Làm sạch và chuẩn hóa bảng HTML từ tài liệu.
 * Đảm bảo chỉ giữ các thẻ an toàn, bổ sung class "doc-table" và bọc trong "doc-table-wrapper".
 */
function sanitizeHtmlTable(rawTableHtml) {
  if (!rawTableHtml) return "";

  // 1. Loại bỏ script, style, iframe
  let clean = rawTableHtml
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, "");

  // 2. Loại bỏ event handler onclick, onload, ...
  clean = clean.replace(/\s+on[a-z]+=(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, "");

  // 3. Loại bỏ link javascript:
  clean = clean.replace(/href\s*=\s*["']\s*javascript:[^"']*["']/gi, 'href="#"');

  // 4. Đảm bảo thẻ <table> có class="doc-table"
  clean = clean.replace(/<table(\s[^>]*)?>/i, (match, attrs) => {
    const attrStr = attrs || "";
    if (/class\s*=/i.test(attrStr)) {
      return match.replace(/class\s*=\s*["']([^"']*)["']/i, 'class="doc-table $1"');
    }
    return `<table class="doc-table"${attrStr}>`;
  });

  return `<div class="doc-table-wrapper">${clean}</div>`;
}

export function renderMarkdownHtml(rawText) {
  if (!rawText) return "";

  // 1. Tách các bảng HTML (<table>...</table>) ra trước để không bị escapeHtml làm thành text &lt;td&gt;
  const tableBlocks = [];
  const textWithPlaceholders = rawText.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
    const placeholder = `__DOC_HTML_TABLE_BLOCK_${tableBlocks.length}__`;
    tableBlocks.push(sanitizeHtmlTable(match));
    return `\n\n${placeholder}\n\n`;
  });

  const text = escapeHtml(textWithPlaceholders);
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

    // Khối bảng HTML đã được tách ra từ trước
    if (trimmed.includes("__DOC_HTML_TABLE_BLOCK_")) {
      closeList();
      closeTable();
      const renderedLine = trimmed.replace(/__DOC_HTML_TABLE_BLOCK_(\d+)__/g, (_m, id) => {
        return tableBlocks[parseInt(id, 10)] || "";
      });
      out.push(renderedLine);
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
