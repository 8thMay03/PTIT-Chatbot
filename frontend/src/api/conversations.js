import { request } from "./client";

export function list({ limit = 50, offset = 0, signal } = {}) {
  return request("conversations", {
    query: { limit, offset },
    signal,
  });
}

export function get(conversationId, { signal } = {}) {
  return request(`conversations/${conversationId}`, { signal });
}

export function rename(conversationId, title) {
  return request(`conversations/${conversationId}`, {
    method: "PATCH",
    body: { title },
  });
}

export function remove(conversationId) {
  return request(`conversations/${conversationId}`, { method: "DELETE" });
}
