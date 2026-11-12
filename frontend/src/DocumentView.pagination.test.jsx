import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DocumentView from "./DocumentView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const TOTAL_CHUNKS = 45;

function delayedJson(payload, ms = 20) {
  return new Promise((resolve) =>
    setTimeout(
      () => resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) }),
      ms
    )
  );
}

function chunkPage(offset, limit) {
  const end = Math.min(offset + limit, TOTAL_CHUNKS);
  const chunks = [];
  for (let i = offset; i < end; i += 1) {
    chunks.push({ id: `chunk-${i}`, chunk_index: i, text: `Đoạn số ${i}`, metadata: {} });
  }
  return { chunks, total: TOTAL_CHUNKS };
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

describe("DocumentView chunk pagination", () => {
  let container;
  let root;
  let queryClient;
  let chunkOffsets;

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });
    chunkOffsets = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url) => {
        const target = new URL(String(url), "http://localhost");
        if (target.pathname.endsWith("/chunks")) {
          const offset = Number(target.searchParams.get("offset"));
          const limit = Number(target.searchParams.get("limit"));
          chunkOffsets.push(offset);
          return delayedJson(chunkPage(offset, limit));
        }
        if (target.pathname.endsWith("/documents/doc-1")) {
          return delayedJson({
            id: "doc-1",
            title: "policy",
            file_name: "policy.md",
            file_type: "md",
            status: "active",
            chunk_count: TOTAL_CHUNKS,
            full_text: "# policy",
          });
        }
        return delayedJson({});
      })
    );
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  it("keeps the requested page instead of snapping back to page 1", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <DocumentView documentId="doc-1" onBack={() => {}} />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
    // act của React 19 chỉ render khi callback kết thúc, nên chờ fetch ở lượt act riêng.
    await act(async () => {
      await wait(200);
    });

    const badge = () => container.querySelector(".page-current-badge")?.textContent;
    const next = () => container.querySelector('button[aria-label="Trang sau"]');
    expect(badge()).toBe("1 / 3");

    await act(async () => {
      next().click();
    });
    await act(async () => {
      await wait(100);
    });
    expect(badge()).toBe("2 / 3");
    expect(container.textContent).toContain("Đoạn số 20");

    await act(async () => {
      next().click();
    });
    await act(async () => {
      await wait(100);
    });
    expect(badge()).toBe("3 / 3");
    expect(container.textContent).toContain("Đoạn số 44");
    expect(chunkOffsets).toEqual(expect.arrayContaining([0, 20, 40]));
  });
});
