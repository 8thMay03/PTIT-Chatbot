import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DatasetView from "./DatasetView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(payload) });
}

const flush = (ms = 30) => new Promise((resolve) => setTimeout(resolve, ms));
const dialog = () => document.body.querySelector('[role="dialog"]');
const dialogButton = (label) =>
  [...(dialog()?.querySelectorAll("button") ?? [])].find((b) => b.textContent.trim() === label);

const DOCUMENTS = [
  {
    id: "d1",
    dataset_id: "ds-1",
    title: "quy-che",
    file_name: "quy-che.md",
    status: "active",
    chunk_count: 8,
    stale_chunk_count: 8,
    parsed_at: "2026-11-20T00:00:00Z",
    created_at: "2026-11-20T00:00:00Z",
  },
  {
    id: "d2",
    dataset_id: "ds-1",
    title: "hoc-phi",
    file_name: "hoc-phi.md",
    status: "active",
    chunk_count: 4,
    stale_chunk_count: 0,
    parsed_at: "2026-11-21T00:00:00Z",
    created_at: "2026-11-21T00:00:00Z",
  },
];

function embedJob(fields = {}) {
  return {
    id: "job-embed",
    kind: "embed",
    status: "queued",
    dataset_id: "ds-1",
    document_id: null,
    file_name: "Sổ tay",
    created_at: new Date().toISOString(),
    progress: 0,
    progress_message: "Đang chờ trong hàng đợi",
    ...fields,
  };
}

describe("DatasetView nhúng vector", () => {
  let container;
  let root;
  let queryClient;
  let calls;
  let jobs;

  async function renderView(dataset) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <DatasetView dataset={dataset} onBack={() => {}} />
          </ToastProvider>
        </QueryClientProvider>
      );
      await flush(80);
    });
  }

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
    calls = [];
    jobs = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url, init = {}) => {
        const target = String(url);
        const method = init.method ?? "GET";
        calls.push({ target, method });
        if (target.includes("/parse-jobs")) return jsonResponse({ jobs });
        if (target.includes("/datasets/ds-1/embed") && method === "POST") {
          const job = embedJob();
          jobs = [job];
          return jsonResponse(job, 202);
        }
        if (target.includes("/documents/d2/embed") && method === "POST") {
          const job = embedJob({ document_id: "d2", file_name: "hoc-phi.md" });
          jobs = [job];
          return jsonResponse(job, 202);
        }
        if (target.includes("/documents")) return jsonResponse({ documents: DOCUMENTS });
        return jsonResponse({});
      })
    );
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  const embedPosts = () => calls.filter((c) => c.method === "POST" && c.target.includes("/embed"));
  const toolbarButton = (text) =>
    [...container.querySelectorAll(".dataset-view-toolbar button")].find((b) => b.textContent.includes(text));

  async function click(button) {
    await act(async () => {
      button.click();
      await flush();
    });
  }

  it("còn tài liệu cần nhúng: badge, banner, chỉ nhúng tài liệu lệch sau khi xác nhận", async () => {
    await renderView({
      id: "ds-1",
      name: "Sổ tay",
      enabled: true,
      document_count: 2,
      chunk_count: 12,
      stale_document_count: 1,
      stale_chunk_count: 8,
    });

    expect(container.querySelector(".dataset-detail-stats").textContent).toContain("1 cần nhúng lại");
    expect(container.querySelector(".doc-status-badge.is-unembedded").textContent).toBe("Cần nhúng lại");
    const banner = container.querySelector(".embed-stale-banner");
    expect(banner.textContent).toContain("1 tài liệu (8 đoạn)");
    const trigger = toolbarButton("Nhúng 1 tài liệu");
    expect(trigger.classList.contains("is-attention")).toBe(true);

    await click(trigger);
    expect(dialog().querySelector("h3").textContent).toBe("Nhúng 1 tài liệu của “Sổ tay”?");
    expect(dialog().textContent).toContain("không parse hay chia đoạn lại");
    await click(dialogButton("Hủy"));
    expect(embedPosts()).toHaveLength(0);

    await click(trigger);
    await click(dialogButton("Nhúng"));
    const [post] = embedPosts();
    expect(post.target).toContain("/datasets/ds-1/embed");
    expect(post.target).not.toContain("all=");
    expect(dialog()).toBeNull();
    // Job nhúng đang chạy: banner tiến độ, khóa nút nhúng, ẩn banner nhắc.
    expect(container.textContent).toContain("Đang nhúng vector nền");
    expect(toolbarButton("Đang nhúng...").disabled).toBe(true);
    expect(container.querySelector(".embed-stale-banner")).toBeNull();
  });

  it("mọi đoạn đã khớp: nhúng lại toàn bộ dataset với all=true, nhúng một tài liệu từ hàng", async () => {
    await renderView({
      id: "ds-1",
      name: "Sổ tay",
      enabled: true,
      document_count: 2,
      chunk_count: 12,
      stale_document_count: 0,
      stale_chunk_count: 0,
    });
    expect(container.querySelector(".embed-stale-banner")).toBeNull();

    // Hàng tài liệu đã khớp mô hình: nhúng lại cả tài liệu.
    await click(container.querySelector('button[aria-label="Nhúng hoc-phi.md"]'));
    expect(embedPosts()[0].target).toContain("/documents/d2/embed?all=true");
    expect(container.textContent).toContain("Đang nhúng");

    await click(toolbarButton("Nhúng lại dataset"));
    expect(dialog().querySelector("h3").textContent).toBe("Nhúng lại toàn bộ dataset “Sổ tay”?");
    expect(dialog().textContent).toContain("toàn bộ 12 đoạn");
    await click(dialogButton("Nhúng lại"));
    expect(embedPosts()[1].target).toContain("/datasets/ds-1/embed?all=true");
  });

  it("dataset chưa có đoạn nào thì không nhúng được", async () => {
    await renderView({ id: "ds-1", name: "Sổ tay", enabled: true, document_count: 0, chunk_count: 0, stale_document_count: 0 });
    expect(toolbarButton("Nhúng lại dataset").disabled).toBe(true);
  });
});
