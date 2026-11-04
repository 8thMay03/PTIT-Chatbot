import { request } from "./client";

export function list({ signal } = {}) {
  return request("datasets", { signal });
}

export function get(datasetId, { signal } = {}) {
  return request(`datasets/${datasetId}`, { signal });
}

export function create({ name, description }, { signal } = {}) {
  return request("datasets", {
    method: "POST",
    body: { name, description: description || undefined },
    signal,
  });
}

export function update(datasetId, { name, description, enabled, clearDescription } = {}, { signal } = {}) {
  return request(`datasets/${datasetId}`, {
    method: "PATCH",
    body: {
      name: name ?? undefined,
      description: description ?? undefined,
      enabled: enabled ?? undefined,
      clear_description: clearDescription || undefined,
    },
    signal,
  });
}

export function remove(datasetId, { signal } = {}) {
  return request(`datasets/${datasetId}`, { method: "DELETE", signal });
}

export function chunk(datasetId, { signal } = {}) {
  return request(`datasets/${datasetId}/chunk`, {
    method: "POST",
    timeout: 5 * 60_000,
    signal,
  });
}

export function parse(datasetId, { signal } = {}) {
  return request(`datasets/${datasetId}/parse`, { method: "POST", signal });
}
