import { EMPTY } from "./format";

/**
 * Trạng thái tài liệu theo hai bước: parse lưu Markdown, chia đoạn đưa vào kho.
 * `parsed` có đoạn nghĩa là Markdown đã đổi sau lần chia gần nhất; đoạn cũ vẫn được dùng khi hỏi đáp.
 */
export function documentStatus(doc) {
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

export function needsChunking(doc) {
  return doc?.status === "parsed";
}
