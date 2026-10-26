import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";

/**
 * Renderer Markdown dùng chung cho chat và màn tài liệu.
 *
 * Trước đây `format.js` tự parse Markdown rồi nối chuỗi HTML, khiến nội dung
 * tài liệu (người dùng upload) và câu trả lời LLM có thể chèn HTML thực thi.
 * Bây giờ mọi thứ đi qua `markdown-it` (GFM table, list, code fence) rồi
 * `DOMPurify` với allowlist chặt, nên chỉ còn các thẻ/thuộc tính hiển thị.
 */

const CITATION_CLASS = "citation-chip";

const md = new MarkdownIt({
  html: true,
  linkify: false,
  // Giữ xuống dòng đơn như bản render cũ: tài liệu PDF/DOCX tách dòng theo
  // layout, gộp chúng thành một đoạn sẽ làm mất cấu trúc.
  breaks: true,
  typographer: false,
});

/** Class CSS đã có trong `document.css`/`chat.css`, giữ nguyên giao diện cũ. */
const TOKEN_CLASSES = {
  paragraph_open: "doc-p",
  bullet_list_open: "doc-ul",
  ordered_list_open: "doc-ol",
  blockquote_open: "doc-blockquote",
  table_open: "doc-table",
  hr: "doc-hr",
  code_inline: "doc-inline-code",
};

const SAFE_LINK_PROTOCOL = /^(?:https?:|mailto:)/i;

/**
 * Gắn class cho token do Markdown sinh ra (không đụng tới HTML thô của tài liệu).
 */
function decorateTokens(tokens) {
  for (const token of tokens) {
    if (token.type === "heading_open") {
      token.attrJoin("class", `doc-h${token.tag.slice(1)}`);
    } else if (TOKEN_CLASSES[token.type]) {
      token.attrJoin("class", TOKEN_CLASSES[token.type]);
    } else if (token.type === "link_open") {
      token.attrJoin("class", "doc-link");
      token.attrSet("target", "_blank");
      token.attrSet("rel", "noopener noreferrer");
    }

    if (token.children) decorateTokens(token.children);
  }
}

md.core.ruler.push("doc_classes", (state) => {
  decorateTokens(state.tokens);
});

// Bảng HTML thô trong tài liệu không đi qua renderer của markdown-it. Thêm
// wrapper cuộn ngang ngay trên token để DOMPurify kiểm tra luôn wrapper này;
// thao tác chỉ chèn thẻ bao nên không thể tạo thuộc tính/thẻ thực thi.
const RAW_TABLE_OPEN = /<table\b/gi;
const RAW_TABLE_CLOSE = /<\/table>/gi;

function wrapRawHtmlTables(tokens) {
  for (const token of tokens) {
    if (token.type === "html_block" && /<table\b/i.test(token.content)) {
      token.content = token.content
        .replace(RAW_TABLE_OPEN, '<div class="doc-table-wrapper"><table')
        .replace(RAW_TABLE_CLOSE, "</table></div>");
    }
    if (token.children) wrapRawHtmlTables(token.children);
  }
}

md.core.ruler.push("doc_raw_tables", (state) => {
  wrapRawHtmlTables(state.tokens);
});

// Bọc bảng Markdown trong div cuộn ngang, giống class cũ.
const renderToken = (tokens, idx, options, env, self) => self.renderToken(tokens, idx, options);

const defaultTableOpen = md.renderer.rules.table_open || renderToken;
const defaultTableClose = md.renderer.rules.table_close || renderToken;

md.renderer.rules.table_open = (tokens, idx, options, env, self) =>
  `<div class="doc-table-wrapper">${defaultTableOpen(tokens, idx, options, env, self)}`;
md.renderer.rules.table_close = (tokens, idx, options, env, self) =>
  `${defaultTableClose(tokens, idx, options, env, self)}</div>`;

// Khối code: markdown-it mặc định chèn `<pre><code>` không class.
md.renderer.rules.fence = (tokens, idx) => {
  const token = tokens[idx];
  const info = token.info ? md.utils.escapeHtml(token.info.trim()) : "";
  const langClass = info ? ` language-${info}` : "";
  return (
    `<pre class="doc-pre"><code class="doc-code-block${langClass}">` +
    `${md.utils.escapeHtml(token.content)}</code></pre>\n`
  );
};

md.renderer.rules.code_block = (tokens, idx) =>
  `<pre class="doc-pre"><code class="doc-code-block">${md.utils.escapeHtml(
    tokens[idx].content
  )}</code></pre>\n`;

// Ảnh không nằm trong allowlist; chỉ giữ phần chữ thay thế để không mất nội dung.
md.renderer.rules.image = (tokens, idx) =>
  md.utils.escapeHtml(tokens[idx].content || tokens[idx].attrGet("alt") || "");

/**
 * Plugin chip trích dẫn `[n]`.
 *
 * Chạy trong bộ parse nên `[n]` trong inline code, code block hoặc link label
 * không bị biến thành chip. Nhãn lấy từ backend được escape bằng
 * `md.utils.escapeHtml` trước khi đưa vào thuộc tính.
 */
function citationPlugin(instance) {
  instance.inline.ruler.before("text", "doc_citation", (state, silent) => {
    const start = state.pos;
    if (state.src.charCodeAt(start) !== 0x5b /* [ */) return false;

    const match = /^\[(\d{1,3})\]/.exec(state.src.slice(start));
    if (!match) return false;

    if (!silent) {
      const token = state.push("doc_citation", "", 0);
      token.content = match[1];
    }
    state.pos += match[0].length;
    return true;
  });

  instance.renderer.rules.doc_citation = (tokens, idx, _options, env) => {
    const id = tokens[idx].content;
    const sources = env?.sources ?? [];
    const source = sources.find((item) => String(item?.citation_id) === id);

    if (!source) return `[${instance.utils.escapeHtml(id)}]`;

    const label =
      source.locator || source.section_path || source.heading || source.source_name || "";
    const ariaLabel = `Xem nguồn trích dẫn số ${id}${label ? `: ${label}` : ""}`;

    return (
      `<button type="button" class="${CITATION_CLASS}" ` +
      `data-citation-id="${instance.utils.escapeHtml(id)}" ` +
      `aria-label="${instance.utils.escapeHtml(ariaLabel)}">` +
      `${instance.utils.escapeHtml(id)}</button>`
    );
  };
}

md.use(citationPlugin);

const ALLOWED_TAGS = [
  "a",
  "b",
  "blockquote",
  "br",
  "button",
  "caption",
  "code",
  "col",
  "colgroup",
  "dd",
  "del",
  "div",
  "dl",
  "dt",
  "em",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "i",
  "ins",
  "li",
  "mark",
  "ol",
  "p",
  "pre",
  "s",
  "span",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "tfoot",
  "th",
  "thead",
  "tr",
  "u",
  "ul",
];

const ALLOWED_ATTR = [
  "align",
  "aria-label",
  "class",
  "colspan",
  "data-citation-id",
  "href",
  "rel",
  "rowspan",
  "scope",
  "start",
  "target",
  "title",
  "type",
  "valign",
];

// Các thẻ/thuộc tính luôn bị chặn, kể cả khi DOMPurify đổi allowlist mặc định.
const FORBID_TAGS = [
  "audio",
  "base",
  "canvas",
  "embed",
  "form",
  "iframe",
  "img",
  "input",
  "link",
  "math",
  "meta",
  "noscript",
  "object",
  "option",
  "script",
  "select",
  "source",
  "style",
  "svg",
  "template",
  "textarea",
  "track",
  "video",
];

const SANITIZE_CONFIG = {
  ALLOWED_TAGS,
  ALLOWED_ATTR,
  FORBID_TAGS,
  ALLOW_DATA_ATTR: false,
  ALLOW_ARIA_ATTR: true,
  KEEP_CONTENT: true,
};

const ALLOWED_CLASS = /^(?:doc-[a-z0-9-]+|citation-chip)$/;

DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  const tagName = node.tagName?.toLowerCase();

  if (tagName === "a") {
    const href = (node.getAttribute("href") || "").trim();
    const isAllowed =
      href.startsWith("#") || href.startsWith("/") || SAFE_LINK_PROTOCOL.test(href);

    if (!isAllowed) {
      node.removeAttribute("href");
    } else {
      node.setAttribute("rel", "noopener noreferrer");
      node.setAttribute("target", "_blank");
    }
  }

  // Chỉ giữ class của giao diện; class lạ từ HTML thô bị bỏ.
  const classValue = node.getAttribute("class");
  if (classValue) {
    const kept = classValue
      .split(/\s+/)
      .filter((name) => name && ALLOWED_CLASS.test(name));
    if (kept.length > 0) node.setAttribute("class", kept.join(" "));
    else node.removeAttribute("class");
  }

  if (tagName === "table") node.classList.add("doc-table");
});

/**
 * Trả về HTML đã render + sanitize.
 *
 * @param {string} rawText Markdown gốc.
 * @param {Array<object>} sources Danh sách nguồn để biến `[n]` thành chip.
 */
export function renderMarkdownHtml(rawText, sources = []) {
  if (!rawText) return "";
  const rendered = md.render(String(rawText), { sources });
  return DOMPurify.sanitize(rendered, SANITIZE_CONFIG);
}
