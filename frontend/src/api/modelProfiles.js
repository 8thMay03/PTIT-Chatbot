import { request } from "./client";

/**
 * Kho mô hình (LLM, embedding, reranker) và chọn mô hình đang dùng.
 * Mọi thao tác ghi trả về toàn bộ trạng thái kho để ghi thẳng vào cache.
 */

export function list({ signal } = {}) {
  return request("model-profiles", { signal });
}

export function create(payload) {
  return request("model-profiles", { method: "POST", body: payload });
}

export function update(profileId, payload) {
  return request(`model-profiles/${encodeURIComponent(profileId)}`, { method: "PUT", body: payload });
}

export function remove(profileId) {
  return request(`model-profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });
}

/** `profileId = null`: LLM/embedding về cấu hình `.env`, reranker về heuristic. */
export function activate(kind, profileId) {
  return request("model-profiles/activate", {
    method: "POST",
    body: { kind, profile_id: profileId },
  });
}

export function testLlm(payload) {
  return request("model-profiles/test-llm", {
    method: "POST",
    body: payload,
    timeout: 60_000,
  });
}
