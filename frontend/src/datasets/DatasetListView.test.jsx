import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DatasetListView from "./DatasetListView";
import { ToastProvider } from "../components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function renderView(props) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return { container, root, client };
}

describe("DatasetListView", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  async function renderList(props) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <DatasetListView datasets={[]} loading={false} loadError={null} onOpen={vi.fn()} {...props} />
          </ToastProvider>
        </QueryClientProvider>
      );
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
  }

  it("hiển thị trạng thái đang tải", async () => {
    await renderList({ loading: true });
    expect(document.body.textContent).toContain("Đang tải danh sách dataset");
  });

  it("hiển thị lỗi khi tải thất bại", async () => {
    await renderList({ loadError: { title: "Lỗi", detail: "mạng" } });
    expect(document.body.textContent).toContain("Lỗi");
  });

  it("cảnh báo khi không còn dataset nào bật", async () => {
    await renderList({
      datasets: [{ id: "a", name: "A", enabled: false, document_count: 1, chunk_count: 2, pending_count: 0 }],
    });
    expect(document.body.textContent).toContain("Không có dataset nào đang bật");
  });

  it("hiển thị thẻ dataset với thống kê", async () => {
    await renderList({
      datasets: [
        { id: "a", name: "Sổ tay", description: "K2024", enabled: true, document_count: 12, chunk_count: 840, pending_count: 2, size_bytes: 1024 },
      ],
    });
    expect(document.body.textContent).toContain("Sổ tay");
    expect(document.body.textContent).toContain("12 tài liệu");
    expect(document.body.textContent).toContain("2 chờ chia đoạn");
  });

  function stubApi({ activeJobs }) {
    const calls = [];
    const fetchMock = vi.fn((url, init = {}) => {
      const href = String(url);
      calls.push({ href, method: init.method ?? "GET" });
      const payload = href.includes("parse-jobs")
        ? { jobs: activeJobs }
        : { documents: 3, chunks: 9, skipped: 0, collection: "c" };
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) });
    });
    vi.stubGlobal("fetch", fetchMock);
    return calls;
  }

  async function openMaintenance() {
    const toggle = [...container.querySelectorAll("button")].find((b) => b.textContent.includes("Bảo trì"));
    await act(async () => {
      toggle.click();
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    const items = [...container.querySelectorAll('[role="menuitem"]')];
    return {
      rechunk: items.find((b) => b.textContent.includes("Chia đoạn lại toàn bộ")),
      reindex: items.find((b) => b.textContent.includes("Nạp lại toàn bộ")),
    };
  }

  it("khóa bảo trì toàn kho khi còn job parse nền", async () => {
    stubApi({
      activeJobs: [
        { id: "job-1", kind: "upload", status: "running", dataset_id: "a", file_name: "x.md", created_at: new Date().toISOString() },
      ],
    });
    await renderList({ datasets: [{ id: "a", name: "A", enabled: true, document_count: 1, chunk_count: 1, pending_count: 0 }] });
    const { rechunk, reindex } = await openMaintenance();
    expect(rechunk.disabled).toBe(true);
    expect(reindex.disabled).toBe(true);
    expect(rechunk.title).toContain("Chờ các job parse nền");
    expect(reindex.title).toContain("Chờ các job parse nền");
  });

  it("cho chạy bảo trì toàn kho khi không còn job nền", async () => {
    const calls = stubApi({ activeJobs: [] });
    await renderList({ datasets: [{ id: "a", name: "A", enabled: true, document_count: 1, chunk_count: 1, pending_count: 0 }] });
    const { rechunk, reindex } = await openMaintenance();
    expect(rechunk.disabled).toBe(false);
    expect(reindex.disabled).toBe(false);
    await act(async () => {
      rechunk.click();
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    const posts = calls.filter((c) => c.method === "POST").map((c) => c.href);
    expect(posts.some((href) => href.includes("ingest/chunk"))).toBe(true);
  });

  it("không chạy bảo trì nếu job nền xuất hiện ngay trước khi bấm", async () => {
    let active = [];
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url, init = {}) => {
        const href = String(url);
        calls.push({ href, method: init.method ?? "GET" });
        const payload = href.includes("parse-jobs") ? { jobs: active } : { documents: 0, chunks: 0 };
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) });
      })
    );
    await renderList({ datasets: [{ id: "a", name: "A", enabled: true, document_count: 1, chunk_count: 1, pending_count: 0 }] });
    const { reindex } = await openMaintenance();
    active = [{ id: "job-2", kind: "parse", status: "queued", document_id: "d", created_at: new Date().toISOString() }];
    await act(async () => {
      reindex.click();
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    expect(document.body.textContent).toContain("Còn job parse nền đang chạy");
  });
});
