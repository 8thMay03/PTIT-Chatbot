import { request } from "./client";

/**
 * Chạy thử pipeline truy xuất trên cấu hình đã lưu.
 *
 * `datasetIds` bỏ trống = tìm trên mọi dataset đang bật. Pipeline có thể gọi
 * embedding và (khi bật viết lại bằng LLM) cả mô hình ngôn ngữ nên thời gian chờ
 * dài hơn API thường.
 */
export function test({ query, topK, datasetIds }, { signal } = {}) {
  return request("retrieval/test", {
    method: "POST",
    body: {
      query,
      top_k: topK,
      dataset_ids: datasetIds && datasetIds.length > 0 ? datasetIds : undefined,
    },
    signal,
    timeout: 120_000,
  });
}
