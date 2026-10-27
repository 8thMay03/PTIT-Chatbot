import { request } from "./client";

export function get({ signal } = {}) {
  return request("config", { signal });
}

export function update(payload) {
  return request("config", {
    method: "PUT",
    body: payload,
  });
}

export function reset() {
  return request("config/reset", { method: "POST" });
}

export function testLlm(payload) {
  return request("config/test-llm", {
    method: "POST",
    body: payload,
    timeout: 60_000,
  });
}
