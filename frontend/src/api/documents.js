import { API_BASE_URL, request } from "./client";

const LONG_RUNNING_TIMEOUT_MS = 5 * 60_000;

export function list({ signal } = {}) {
  return request("documents", { signal });
}

export function get(documentId, { signal } = {}) {
  return request(`documents/${documentId}`, { signal });
}

export function chunks(
  documentId,
  { offset = 0, limit = 200, signal } = {}
) {
  return request(`documents/${documentId}/chunks`, {
    query: { offset, limit },
    signal,
  });
}

/** Nạp toàn bộ đoạn theo lô; dùng cho tìm kiếm phía client. */
export async function allChunks(documentId, { signal, batchSize = 500 } = {}) {
  const collected = [];
  let offset = 0;
  let total = Infinity;

  while (offset < total) {
    const payload = await chunks(documentId, {
      offset,
      limit: batchSize,
      signal,
    });
    const items = payload.chunks ?? [];
    collected.push(...items);
    total = payload.total ?? collected.length;
    offset += batchSize;
    if (items.length === 0) break;
  }

  return collected;
}

export function upload(file, { parserName = null } = {}) {
  const form = new FormData();
  form.append("file", file);
  if (parserName) form.append("parser_name", parserName);

  return request("documents", {
    method: "POST",
    body: form,
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function remove(documentId) {
  return request(`documents/${documentId}`, { method: "DELETE" });
}

export function reindex() {
  return request("ingest", {
    method: "POST",
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function rechunk() {
  return request("ingest/chunk", {
    method: "POST",
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function parse(documentId, parserName) {
  return request(`documents/${documentId}/parse`, {
    method: "POST",
    query: { parser_name: parserName },
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function chunk(documentId) {
  return request(`documents/${documentId}/chunk`, {
    method: "POST",
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function parsersForFile(fileName) {
  return request("parsers", { query: { file_name: fileName } });
}

export function parsersForDocument(documentId, { signal } = {}) {
  return request(`documents/${documentId}/parsers`, { signal });
}

export function markdown(documentId, { signal } = {}) {
  return request(`documents/${documentId}/markdown`, { signal });
}

export function saveMarkdown(documentId, { text, baseHash }) {
  return request(`documents/${documentId}/markdown`, {
    method: "PUT",
    body: { text, base_hash: baseHash },
  });
}

export function file(
  documentId,
  { inline = false, responseType = "blob", signal } = {}
) {
  return request(`documents/${documentId}/file`, {
    query: { inline: inline ? "true" : undefined },
    responseType,
    signal,
    timeout: LONG_RUNNING_TIMEOUT_MS,
  });
}

export function fileUrl(documentId, { inline = false } = {}) {
  const root = API_BASE_URL.replace(/\/+$/, "");
  return `${root}/documents/${documentId}/file${inline ? "?inline=true" : ""}`;
}
