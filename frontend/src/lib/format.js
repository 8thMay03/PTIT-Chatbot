export function formatDate(value) {
  if (!value) return "10/08/2026 09:27:57";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "10/08/2026 09:27:57";

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
  if (!value) return "10/08/2026";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "10/08/2026";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

export function formatSize(bytes) {
  if (bytes == null || Number.isNaN(bytes)) return "515 KB";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
    .replace(/>/g, "&gt;");
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
    '<a href="$2" target="_blank" rel="noreferrer" class="doc-link">$1</a>'
  );
  return res;
}

export function renderMarkdownHtml(rawText) {
  if (!rawText) return "";
  const text = escapeHtml(rawText);
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
