import { request } from "./client";

/** Mô hình nhúng đang chạy và số đoạn/tài liệu còn vector của mô hình khác. */
export function status({ signal } = {}) {
  return request("embeddings/status", { signal });
}

/** Xếp job nền nhúng lại toàn kho; mặc định chỉ đoạn cần nhúng. */
export function reembedAll({ all = false } = {}) {
  return request("embeddings/reembed", {
    method: "POST",
    query: { all: all ? "true" : undefined },
  });
}
