import { renderMarkdownHtml } from "./markdown";

/**
 * Tìm vị trí một đoạn (chunk) trên bản Markdown đã render của tài liệu.
 *
 * Đoạn được chia từ `clean_text(parsed_text)` còn cột trái render `parsed_text`
 * gốc, nên không có offset chung để tra trực tiếp. Bản trước so `textContent`
 * từng khối với dòng Markdown thô của đoạn: hàng bảng (`|a|b|`, `<br/>`, `\@`)
 * không bao giờ khớp, và khi không khớp thì đoán vị trí theo tỷ lệ
 * chunk_index/tổng — đánh dấu sai chỗ. Ở đây cả tài liệu lẫn đoạn đều đi qua
 * cùng renderer, được chuẩn hóa thành chuỗi chỉ gồm chữ/số, rồi căn các mảnh
 * của đoạn theo đúng thứ tự trên chuỗi của tài liệu.
 */

/** Các khối được đánh dấu; chữ thuộc về khối gần nhất bao quanh nó. */
export const CHUNK_BLOCK_SELECTOR =
  ".doc-p, .doc-h1, .doc-h2, .doc-h3, .doc-h4, .doc-h5, .doc-h6, li, tr, .doc-blockquote, .doc-pre";

const HEADING_TAGS = new Set(["H1", "H2", "H3", "H4", "H5", "H6"]);
// Mảnh ngắn quá thì khớp bừa nhiều chỗ; dài quá thì một khác biệt nhỏ làm hỏng cả mảnh.
const UNIT_SIZE = 48;
const MIN_UNIT = 6;
const MAX_HITS_PER_UNIT = 400;
// Khoảng chữ của tài liệu được phép chen giữa hai mảnh liên tiếp (header/footer
// trang, dòng nhiễu mà bước làm sạch đã bỏ khỏi đoạn).
const MAX_GAP = 250;
// Mỗi chữ chen giữa bị trừ điểm, để vùng liền mạch thắng vùng "nhảy cóc" ghép
// mảnh của hai chỗ có nội dung na ná nhau.
const GAP_PENALTY = 0.5;

export function normalizeForMatch(text) {
  return String(text || "")
    .normalize("NFC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

/** Gom chữ của mỗi text node vào khối gần nhất, giữ thứ tự xuất hiện. */
function collectBlocks(root) {
  const owned = new Map();
  const order = [];
  const walker = root.ownerDocument.createTreeWalker(root, 4 /* NodeFilter.SHOW_TEXT */);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const block = node.parentElement?.closest(CHUNK_BLOCK_SELECTOR);
    if (!block || !root.contains(block)) continue;
    if (!owned.has(block)) {
      owned.set(block, []);
      order.push(block);
    }
    owned.get(block).push(node.nodeValue);
  }
  return order
    .map((el) => ({ el, text: normalizeForMatch(owned.get(el).join(" ")) }))
    .filter((block) => block.text);
}

/**
 * Lập chỉ mục chữ của bản render. Tính một lần cho mỗi nội dung tài liệu rồi
 * dùng lại cho mọi lần trỏ chuột.
 */
export function buildDocumentIndex(root) {
  const spans = [];
  // headingAt[i]: khối heading gần nhất tính tới khối i (-1 nếu chưa có).
  const headingAt = [];
  let stream = "";
  // Số lần mỗi heading xuất hiện: heading chung ("NĂM HỌC THỨ BA" ở mọi ngành)
  // không giúp chọn đúng section.
  const headingCounts = new Map();
  for (const { el, text } of collectBlocks(root)) {
    const heading = HEADING_TAGS.has(el.tagName);
    headingAt.push(heading ? spans.length : headingAt.length ? headingAt[headingAt.length - 1] : -1);
    if (heading) headingCounts.set(text, (headingCounts.get(text) ?? 0) + 1);
    spans.push({ el, start: stream.length, end: stream.length + text.length, heading });
    stream += text;
  }
  return { stream, spans, headingAt, headingCounts };
}

/**
 * Render đoạn bằng cùng renderer rồi cắt thành các mảnh đã chuẩn hóa.
 *
 * Bước chia đoạn chép dòng heading của section vào đầu MỌI đoạn con, nên
 * heading tách riêng: chỉ dùng để chọn đúng section, không nằm trong chuỗi
 * mảnh (nếu không, đoạn thứ ba của section sẽ kéo vùng đánh dấu về tận heading).
 */
export function chunkUnits(chunkText, ownerDocument = document) {
  const holder = ownerDocument.createElement("div");
  holder.innerHTML = renderMarkdownHtml(chunkText);
  const blocks = collectBlocks(holder);
  const heading = blocks.length > 1 && HEADING_TAGS.has(blocks[0].el.tagName) ? blocks[0].text : "";

  const units = [];
  for (const { text } of heading ? blocks.slice(1) : blocks) {
    const count = Math.max(1, Math.round(text.length / UNIT_SIZE));
    const size = Math.ceil(text.length / count);
    for (let i = 0; i < text.length; i += size) {
      const piece = text.slice(i, i + size);
      if (piece.length >= MIN_UNIT || (count === 1 && piece.length >= 3)) units.push(piece);
    }
  }
  return { units, heading };
}

function spanIndexAt(spans, pos) {
  let lo = 0;
  let hi = spans.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (spans[mid].start <= pos) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

/** Heading gần nhất phía trước `pos` có phải heading (duy nhất) của đoạn không. */
function underHeading(index, pos, heading) {
  if (!heading || index.headingCounts.get(heading) !== 1) return false;
  const at = index.headingAt[spanIndexAt(index.spans, pos)];
  const span = index.spans[at];
  return Boolean(span) && index.stream.slice(span.start, span.end) === heading;
}

/**
 * Tìm vùng của đoạn trên tài liệu.
 *
 * @param {object} index Kết quả `buildDocumentIndex`.
 * @param {string} chunkText Nội dung Markdown của đoạn.
 * @param {{hintRatio?: number, after?: number}} options `hintRatio` (0..1) là vị
 *   trí ước lượng theo chunk_index; `after` là vị trí của đoạn liền trước — khi
 *   cùng nội dung xuất hiện ở nhiều chỗ (văn bản trùng, bảng giống nhau giữa các
 *   ngành), chọn chỗ đầu tiên nằm sau đoạn đó.
 * @returns {{elements: Element[], start: number, end: number, ambiguous: boolean} | null}
 *   `null` khi không đủ căn cứ (thà không đánh dấu còn hơn đánh dấu sai chỗ).
 */
export function locateChunk(index, chunkText, { hintRatio = 0, after = null, ownerDocument } = {}) {
  if (!index || !index.stream || !chunkText) return null;
  const { units, heading } = chunkUnits(chunkText, ownerDocument ?? index.spans[0]?.el.ownerDocument);
  if (units.length === 0) return null;
  const { stream, spans } = index;

  const hits = [];
  units.forEach((unit, u) => {
    let found = 0;
    for (let pos = stream.indexOf(unit); pos !== -1 && found < MAX_HITS_PER_UNIT; pos = stream.indexOf(unit, pos + 1)) {
      hits.push({ u, start: pos, end: pos + unit.length });
      found += 1;
    }
  });
  if (hits.length === 0) return null;
  hits.sort((a, b) => a.start - b.start || a.u - b.u);

  // Chuỗi mảnh tốt nhất: mảnh sau đứng sau mảnh trước cả trong đoạn lẫn trên
  // tài liệu, cách nhau không quá MAX_GAP chữ; điểm = số chữ khớp − phạt khoảng hở.
  const score = new Array(hits.length);
  const first = new Array(hits.length);
  for (let i = 0; i < hits.length; i++) {
    const hit = hits[i];
    score[i] = hit.end - hit.start;
    first[i] = i;
    for (let j = i - 1; j >= 0; j--) {
      const prev = hits[j];
      if (hit.start - prev.start > MAX_GAP + UNIT_SIZE * 2) break;
      if (prev.u >= hit.u || prev.end > hit.start || hit.start - prev.end > MAX_GAP) continue;
      const candidate = score[j] + (hit.end - hit.start) - GAP_PENALTY * (hit.start - prev.end);
      if (candidate > score[i]) {
        score[i] = candidate;
        first[i] = first[j];
      }
    }
  }

  // Heading của đoạn xác định section nên chuỗi nằm dưới đúng heading được cộng điểm.
  const totalLen = units.reduce((sum, unit) => sum + unit.length, 0);
  const candidates = [];
  for (let i = 0; i < hits.length; i++) {
    const start = hits[first[i]].start;
    const bonus = underHeading(index, start, heading) ? totalLen * 0.5 : 0;
    candidates.push({ start, end: hits[i].end, score: score[i], value: score[i] + bonus });
  }
  const bestValue = Math.max(...candidates.map((c) => c.value));
  // Các vùng gần ngang điểm nhất, mỗi vùng chỉ giữ chuỗi dài nhất của nó.
  const contenders = candidates
    .filter((c) => c.value >= bestValue * 0.9)
    .sort((a, b) => b.value - a.value)
    .filter((c, i, list) => list.findIndex((o) => o.start < c.end && c.start < o.end) === i);
  const hint = Math.max(0, Math.min(1, hintRatio)) * stream.length;
  const byHint = (a, b) => Math.abs(a.start - hint) - Math.abs(b.start - hint);
  const top = contenders.filter((c) => c.value === bestValue).sort(byHint)[0];

  let chosen = top;
  if (after != null && contenders.length > 1) {
    const following = contenders
      .filter((c) => c.start >= after)
      .sort((a, b) => a.start - b.start);
    if (following.length > 0) chosen = following[0];
  }
  if (chosen.score < Math.min(24, totalLen * 0.5)) return null;

  let from = spanIndexAt(spans, chosen.start);
  const to = spanIndexAt(spans, chosen.end - 1);
  // Đoạn đầu của section: heading đứng ngay trước phần thân thì đánh dấu cùng.
  const before = spans[from - 1];
  if (before?.heading && stream.slice(before.start, before.end) === heading) from -= 1;
  return {
    elements: spans.slice(from, to + 1).map((span) => span.el),
    start: chosen.start,
    end: chosen.end,
    ambiguous: contenders.length > 1,
  };
}

/**
 * Bộ định vị cho một bản render: lập chỉ mục một lần, nhớ kết quả theo danh
 * sách đoạn đang hiển thị. Khi vị trí của một đoạn chưa phân định được, định
 * vị đoạn đứng trước nó trong danh sách (chunk_index nhỏ hơn) rồi chọn chỗ nằm
 * sau — kết quả không phụ thuộc thứ tự người dùng trỏ chuột.
 */
export function createChunkLocator(root) {
  const index = buildDocumentIndex(root);
  let cachedList = null;
  let cache = new Map();

  function locateAt(list, position, totalChunks) {
    const chunk = list[position];
    if (cache.has(chunk.id)) return cache.get(chunk.id);
    const hintRatio = totalChunks > 0 ? (chunk.chunk_index ?? 0) / totalChunks : 0;
    let result = locateChunk(index, chunk.text, { hintRatio });
    const prevChunk = list[position - 1];
    if (result?.ambiguous && prevChunk && (prevChunk.chunk_index ?? -1) < (chunk.chunk_index ?? 0)) {
      const prev = locateAt(list, position - 1, totalChunks);
      if (prev) result = locateChunk(index, chunk.text, { hintRatio, after: prev.start });
    }
    cache.set(chunk.id, result);
    return result;
  }

  return {
    /** Các phần tử thuộc `list[position]`, rỗng khi không tìm được. */
    locate(list, position, totalChunks) {
      if (list !== cachedList) {
        cachedList = list;
        cache = new Map();
      }
      if (!list[position]) return [];
      return locateAt(list, position, totalChunks)?.elements ?? [];
    },
  };
}
