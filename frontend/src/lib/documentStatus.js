import { EMPTY } from "./format";

/**
 * Trạng thái tài liệu theo hai bước: parse lưu Markdown, chia đoạn đưa vào kho.
 * `parsed` có đoạn nghĩa là Markdown đã đổi sau lần chia gần nhất; đoạn cũ vẫn được dùng khi hỏi đáp.
 */
export function documentStatus(doc) {
  if (doc?.status === "active" && needsEmbedding(doc)) {
    return {
      key: "unembedded",
      label: "Cần nhúng lại",
      hint:
        `${doc.stale_chunk_count} đoạn chưa có vector của mô hình nhúng đang dùng (vừa đổi mô hình hoặc chưa nhúng); ` +
        "các đoạn này chỉ tìm được bằng từ khóa cho tới khi nhúng lại.",
    };
  }
  if (doc?.status === "active") {
    return { key: "active", label: "Đã nạp", hint: "Đã parse và chia đoạn; đang được dùng khi hỏi đáp." };
  }
  if (doc?.status === "parsed") {
    return (doc.chunk_count ?? 0) > 0
      ? {
          key: "stale",
          label: "Cần chia đoạn lại",
          hint: "Markdown đã thay đổi sau lần chia đoạn gần nhất; các đoạn cũ vẫn đang được dùng khi hỏi đáp.",
        }
      : {
          key: "parsed",
          label: "Chờ chia đoạn",
          hint: "Đã parse nhưng chưa chia đoạn nên chưa được dùng khi hỏi đáp.",
        };
  }
  return { key: doc?.status || "unknown", label: doc?.status || EMPTY, hint: "" };
}

/** Còn đoạn chưa có vector của mô hình nhúng đang chạy. */
export function needsEmbedding(doc) {
  return (doc?.stale_chunk_count ?? 0) > 0;
}

export function needsChunking(doc) {
  return doc?.status === "parsed";
}

/** Chỉ tài liệu đã lưu Markdown (parse sau khi tách hai bước) mới sửa được Markdown. */
export function canEditMarkdown(doc) {
  return Boolean(doc?.parsed_at);
}

export const NO_MARKDOWN_HINT = "Tài liệu chưa có bản Markdown đã lưu; hãy Parse lại trước khi sửa.";
