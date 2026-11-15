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

  function stubApi({ activeJobs, maintenance = () => ({ documents: 3, chunks: 9, skipped: 0, collection: "c" }) }) {
    const calls = [];
    const fetchMock = vi.fn((url, init = {}) => {
      const href = String(url);
      calls.push({ href, method: init.method ?? "GET" });
      if (href.includes("parse-jobs")) {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ jobs: activeJobs }) });
      }
      const result = maintenance(href);
      if (result && typeof result.then === "function") return result;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(result) });
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

  const flush = (ms = 20) => new Promise((resolve) => setTimeout(resolve, ms));
  const dialog = () => document.body.querySelector('[role="dialog"]');
  const dialogButton = (label) =>
    [...(dialog()?.querySelectorAll("button") ?? [])].find((b) => b.textContent.trim() === label);
  const maintenancePosts = (calls) =>
    calls.filter((c) => c.method === "POST" && /\/ingest(\/chunk)?$/.test(c.href));

  async function click(button) {
    await act(async () => {
      button.click();
      await flush();
    });
  }

  const TWO_DATASETS = [
    { id: "a", name: "A", enabled: true, document_count: 4, chunk_count: 10, pending_count: 0 },
    { id: "b", name: "B", enabled: false, document_count: 3, chunk_count: 6, pending_count: 0 },
  ];

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
    await click(rechunk);
    expect(maintenancePosts(calls)).toHaveLength(0);
    await click(dialogButton("Chia đoạn lại toàn bộ"));
    const posts = maintenancePosts(calls).map((c) => c.href);
    expect(posts).toHaveLength(1);
    expect(posts[0]).toMatch(/ingest\/chunk$/);
    expect(dialog()).toBeNull();
    expect(document.body.textContent).toContain("Đã chia đoạn lại 3 tài liệu · 9 đoạn.");
  });

  it.each([
    ["rechunk", "Chia đoạn lại toàn bộ kho tài liệu?"],
    ["reindex", "Nạp lại toàn bộ kho tài liệu?"],
  ])("mở hộp xác nhận cho %s; Hủy, Esc và bấm nền không gọi API", async (kind, title) => {
    const calls = stubApi({ activeJobs: [] });
    await renderList({ datasets: TWO_DATASETS });

    const closers = {
      cancel: async () => click(dialogButton("Hủy")),
      escape: async () => {
        await act(async () => {
          document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
          await flush();
        });
      },
      backdrop: async () => {
        await act(async () => {
          const backdrop = document.body.querySelector(".modal-backdrop");
          backdrop.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
          await flush();
        });
      },
    };

    for (const close of Object.values(closers)) {
      const items = await openMaintenance();
      await click(items[kind]);
      expect(dialog()).not.toBeNull();
      expect(dialog().querySelector("h3").textContent).toBe(title);
      await close();
      expect(dialog()).toBeNull();
    }
    expect(maintenancePosts(calls)).toHaveLength(0);
  });

  it("nêu phạm vi, việc nhúng lại và thời gian trong hộp xác nhận", async () => {
    stubApi({ activeJobs: [] });
    await renderList({ datasets: TWO_DATASETS });

    await click((await openMaintenance()).rechunk);
    let text = dialog().textContent;
    expect(text).toContain("toàn bộ 2 dataset (7 tài liệu)");
    expect(text).toContain("nhúng vector lại");
    expect(text).toContain("không được parse lại");
    expect(text).toContain("mất nhiều thời gian");
    expect(dialog().querySelector(".modal-icon").classList.contains("is-danger")).toBe(false);
    await click(dialogButton("Hủy"));

    await click((await openMaintenance()).reindex);
    text = dialog().textContent;
    expect(text).toContain("parse lại file gốc");
    expect(text).toContain("toàn bộ 2 dataset (7 tài liệu)");
    expect(text).toContain("nhúng vector lại");
    expect(text).toContain("Markdown sửa tay được giữ nguyên");
    expect(text).toContain("mất nhiều thời gian");
    expect(dialog().querySelector(".modal-icon").classList.contains("is-danger")).toBe(true);
    expect(dialogButton("Nạp lại toàn bộ").className).toContain("danger-btn");
  });

  it("giữ hộp xác nhận và khóa nút trong lúc nạp lại đang chạy", async () => {
    let resolveIngest;
    const calls = stubApi({
      activeJobs: [],
      maintenance: () =>
        new Promise((resolve) => {
          resolveIngest = () =>
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.resolve({ documents: 7, chunks: 20, skipped: 2, collection: "c" }),
            });
        }),
    });
    await renderList({ datasets: TWO_DATASETS });
    await click((await openMaintenance()).reindex);
    const confirm = dialogButton("Nạp lại toàn bộ");
    await click(confirm);
    expect(resolveIngest).toBeTypeOf("function");

    expect(confirm.disabled).toBe(true);
    expect(dialogButton("Hủy").disabled).toBe(true);
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      document.body.querySelector(".modal-backdrop").dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      confirm.click();
      await flush();
    });
    expect(dialog()).not.toBeNull();
    expect(maintenancePosts(calls)).toHaveLength(1);

    await act(async () => {
      resolveIngest();
      await flush();
    });
    expect(dialog()).toBeNull();
    expect(document.body.textContent).toContain("Bỏ qua 2 tài liệu chưa có bản parse");
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
    await click(reindex);
    await click(dialogButton("Nạp lại toàn bộ"));
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    expect(dialog()).toBeNull();
    expect(document.body.textContent).toContain("Còn job parse nền đang chạy");
  });
});
