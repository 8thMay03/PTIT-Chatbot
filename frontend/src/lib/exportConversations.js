/**
 * "Tải lịch sử về máy" (student-settings AC-05): gom mọi hội thoại của phiên hiện
 * tại qua API công khai rồi ghi thành một tệp Markdown.
 *
 * Danh sách lấy theo trang (`GET /conversations`), chi tiết từng hội thoại
 * (`GET /conversations/{id}`) tải song song có giới hạn để không dồn request.
 */
export const EXPORT_PAGE_SIZE = 200;
export const EXPORT_CONCURRENCY = 4;

/**
 * Mọi hội thoại kèm tin nhắn, theo thứ tự danh sách (mới cập nhật trước).
 *
 * `api` là `{ list, get }` (như `conversationsApi`); `onProgress(done, total)` báo
 * số hội thoại đã tải chi tiết.
 */
export async function fetchAllConversations(api, { signal, onProgress, pageSize = EXPORT_PAGE_SIZE } = {}) {
  const items = [];
  let total = Infinity;
  while (items.length < total) {
    const page = await api.list({ limit: pageSize, offset: items.length, signal });
    const batch = page?.conversations ?? [];
    total = Number.isFinite(page?.total) ? page.total : items.length + batch.length;
    items.push(...batch);
    // Danh sách co lại giữa chừng (hội thoại bị xoá ở thiết bị khác): dừng.
    if (batch.length === 0) break;
  }

  const details = new Array(items.length);
  let next = 0;
  let done = 0;
  onProgress?.(0, items.length);
  async function worker() {
    while (next < items.length) {
      const index = next;
      next += 1;
      details[index] = await api.get(items[index].id, { signal });
      done += 1;
      onProgress?.(done, items.length);
    }
  }
  await Promise.all(Array.from({ length: Math.min(EXPORT_CONCURRENCY, items.length) }, worker));
  return details;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

/** Dòng nguồn trích dẫn giống thẻ nguồn trên màn chat. */
function sourceLine(source) {
  const title = source.locator || source.heading || "Mục trong tài liệu";
  const parts = [title, source.source_name];
  if (source.section_path && source.section_path !== source.locator) parts.push(source.section_path);
  const label = source.citation_id != null ? `[${source.citation_id}] ` : "";
  return `- ${label}${parts.filter(Boolean).join(" — ")}`;
}

/** Hội thoại (dạng `GET /conversations/{id}`) → Markdown. */
export function conversationsToMarkdown(conversations, { exportedAt = new Date() } = {}) {
  const lines = [
    "# Lịch sử hội thoại — PTIT Chatbot",
    "",
    `Xuất lúc ${formatDate(exportedAt)} · ${conversations.length} hội thoại.`,
  ];
  conversations.forEach((conversation) => {
    lines.push("", "---", "", `## ${conversation.title || "Hội thoại không tên"}`);
    const created = formatDate(conversation.created_at);
    if (created) lines.push("", `_Bắt đầu ${created}_`);
    (conversation.messages ?? []).forEach((message) => {
      if (message.role === "user") {
        lines.push("", "### Câu hỏi", "", message.content || "");
        return;
      }
      lines.push("", "### Trả lời", "");
      if (message.content) lines.push(message.content);
      else if (message.interrupted) lines.push("_Đã dừng trước khi có câu trả lời._");
      else if (message.error) lines.push("_Không có câu trả lời (lỗi)._");
      if (message.sources?.length) {
        lines.push("", "**Nguồn:**", "", ...message.sources.map(sourceLine));
      }
    });
  });
  return `${lines.join("\n")}\n`;
}

/** Tên tệp kiểu `ptit-chatbot-lich-su-2026-11-17.md` (ngày theo giờ máy). */
export function exportFileName(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `ptit-chatbot-lich-su-${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}.md`;
}

/** Tải chuỗi văn bản về máy dưới dạng tệp. */
export function downloadTextFile(fileName, text, type = "text/markdown;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Trình duyệt cần URL còn sống đến khi bắt đầu tải.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
