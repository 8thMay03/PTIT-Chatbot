import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DatasetView from "./DatasetView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) });
}

const flush = (ms = 30) => new Promise((resolve) => setTimeout(resolve, ms));
const dialog = () => document.body.querySelector('[role="dialog"]');
const dialogButton = (label) =>
  [...(dialog()?.querySelectorAll("button") ?? [])].find((b) => b.textContent.trim() === label);

describe("DatasetView chia đoạn lại dataset", () => {
  let container;
  let root;
  let queryClient;
  let calls;
  let chunkResponse;

  const dataset = { id: "ds-1", name: "Sổ tay", enabled: true, document_count: 12, chunk_count: 40, pending_count: 0 };

  beforeEach(async () => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
    calls = [];
    chunkResponse = () => jsonResponse({ documents: 12, chunks: 41, skipped: 0 });
    vi.stubGlobal(
      "fetch",
      vi.fn((url, init = {}) => {
        const target = String(url);
        calls.push({ target, method: init.method ?? "GET" });
        if (target.includes("/parse-jobs")) return jsonResponse({ jobs: [] });
        if (target.endsWith("/datasets/ds-1/chunk")) return chunkResponse();
        if (target.includes("/documents")) return jsonResponse({ documents: [] });
        return jsonResponse({});
      })
    );

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
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  const chunkPosts = () => calls.filter((c) => c.method === "POST" && c.target.endsWith("/chunk"));

  async function click(button) {
    await act(async () => {
      button.click();
      await flush();
    });
  }

  async function openConfirm() {
    const trigger = [...container.querySelectorAll("button")].find((b) =>
      b.textContent.includes("Chia đoạn lại dataset")
    );
    await click(trigger);
  }

  it("hỏi xác nhận kèm tên dataset; Hủy, Esc và bấm nền không gọi API", async () => {
    await openConfirm();
    expect(dialog().querySelector("h3").textContent).toBe("Chia đoạn lại dataset “Sổ tay”?");
    const text = dialog().textContent;
    expect(text).toContain("12 tài liệu trong dataset này");
    expect(text).toContain("nhúng vector lại");
    expect(text).toContain("không được parse lại");
    expect(text).toContain("mất nhiều thời gian");
    await click(dialogButton("Hủy"));
    expect(dialog()).toBeNull();

    await openConfirm();
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await flush();
    });
    expect(dialog()).toBeNull();

    await openConfirm();
    await act(async () => {
      document.body.querySelector(".modal-backdrop").dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      await flush();
    });
    expect(dialog()).toBeNull();
    expect(chunkPosts()).toHaveLength(0);
  });

  it("chỉ gọi API sau khi xác nhận và khóa hộp thoại trong lúc chạy", async () => {
    let resolveChunk;
    chunkResponse = () =>
      new Promise((resolve) => {
        resolveChunk = () =>
          resolve({ ok: true, status: 200, json: () => Promise.resolve({ documents: 12, chunks: 41, skipped: 0 }) });
      });

    await openConfirm();
    const confirm = dialogButton("Chia đoạn lại");
    await click(confirm);
    expect(chunkPosts()).toHaveLength(1);
    expect(confirm.disabled).toBe(true);
    expect(dialogButton("Hủy").disabled).toBe(true);

    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      document.body.querySelector(".modal-backdrop").dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      confirm.click();
      await flush();
    });
    expect(dialog()).not.toBeNull();
    expect(chunkPosts()).toHaveLength(1);

    await act(async () => {
      resolveChunk();
      await flush();
    });
    expect(dialog()).toBeNull();
    expect(document.body.textContent).toContain("Đã chia đoạn lại 12 tài liệu · 41 đoạn trong “Sổ tay”.");
  });
});
