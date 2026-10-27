import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

/** Tiện ích dùng chung cho test landing/trang tài khoản (không nằm trong bundle). */

export const GUEST = { authenticated: false, user: null, registration_enabled: true };
export const STUDENT = {
  authenticated: true,
  user: {
    id: "u-1",
    email: "sv@stu.ptit.edu.vn",
    full_name: "Nguyễn Văn An",
    created_at: "2026-10-28T00:00:00+00:00",
  },
  registration_enabled: true,
};

export function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    url: "",
    headers: { get: () => "application/json" },
    json: () => Promise.resolve(payload),
  });
}

/**
 * Backend giả theo `METHOD path` (không có tiền tố /api/). Handler trả `[status, body]`
 * hoặc body (200). Route không khai báo trả 404.
 */
export function createBackend(routes) {
  const fetchMock = vi.fn((url, options = {}) => {
    const path = new URL(String(url), "http://localhost").pathname.replace(/^\/api\//, "");
    const key = `${options.method ?? "GET"} ${path}`;
    const handler = routes[key];
    if (!handler) return jsonResponse({ detail: `Không có ${key}` }, 404);
    const body = options.body ? JSON.parse(options.body) : undefined;
    const result = typeof handler === "function" ? handler(body) : handler;
    if (result instanceof Promise) return result;
    return Array.isArray(result) ? jsonResponse(result[1], result[0]) : jsonResponse(result);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function callsTo(fetchMock, key) {
  return fetchMock.mock.calls.filter(([url, options = {}]) => {
    const path = new URL(String(url), "http://localhost").pathname.replace(/^\/api\//, "");
    return `${options.method ?? "GET"} ${path}` === key;
  });
}

export async function waitFor(check, timeout = 1500) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeout) {
    try {
      const value = check();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
  throw lastError ?? new Error("Hết thời gian chờ trạng thái giao diện.");
}

/** Render một trang trong QueryClient riêng; trả `{ container, queryClient, unmount }`. */
export async function renderPage(element) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await act(async () => {
    root.render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
  });
  return {
    container,
    queryClient,
    unmount() {
      act(() => root.unmount());
      container.remove();
      queryClient.clear();
    },
  };
}

/** Gõ giá trị vào input có kiểm soát của React. */
export function typeInto(input, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

export function inputByLabel(container, text) {
  const label = [...container.querySelectorAll("label")].find(
    (item) => item.textContent.trim() === text
  );
  if (!label) throw new Error(`Không thấy nhãn ${text}`);
  return container.ownerDocument.getElementById(label.htmlFor);
}

export function buttonByText(container, text) {
  return [...container.querySelectorAll("button")].find((item) => item.textContent.trim() === text);
}

export async function submit(form) {
  await act(async () => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
}
