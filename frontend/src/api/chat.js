import { request } from "./client";
import { ApiError } from "./errors";

/**
 * Đọc NDJSON từ `/chat/stream` và phát từng event đã parse.
 *
 * Toàn bộ chi tiết giao thức stream nằm ở đây; view chỉ xử lý loại event.
 */
export async function* streamChat({
  message,
  conversationId = null,
  topK = 4,
  signal,
}) {
  const response = await request("chat/stream", {
    method: "POST",
    body: {
      message,
      conversation_id: conversationId,
      top_k: topK,
    },
    signal,
    responseType: "stream",
  });

  if (!response.body) {
    throw new ApiError({
      status: 0,
      code: "unsupported",
      detail: "Trình duyệt không hỗ trợ streaming.",
    });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value ?? new Uint8Array(), { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          yield JSON.parse(trimmed);
        } catch {
          // Dòng hỏng giữa stream: bỏ qua thay vì làm sập cả câu trả lời.
        }
      }
    }

    buffer += decoder.decode();
    const trailing = buffer.trim();
    if (trailing) {
      try {
        yield JSON.parse(trailing);
      } catch {
        // Event cuối không có newline vẫn có thể hỏng; bỏ qua.
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Reader đã đóng hoặc stream đã bị huỷ.
    }
  }
}
