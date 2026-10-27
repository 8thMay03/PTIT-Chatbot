import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DatasetView from "./DatasetView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
}

function documentItem(overrides) {
  return {
    id: "doc-1",
    title: "policy",
    file_name: "policy.pdf",
    source_path: "data/policy.pdf",
    file_type: "pdf",
    status: "active",
    markdown_edited: false,
    parsed_at: "2026-10-27T14:00:00Z",
    chunk_count: 5,
    size_bytes: 1024,
    created_at: "2026-10-27T14:00:00Z",
    updated_at: "2026-10-27T14:00:00Z",
    ...overrides,
  };
}

describe("DatasetView background parse", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  it("shows a background banner and only locks the document being parsed", async () => {
    const documents = [
      documentItem({ id: "doc-1", title: "policy", file_name: "policy.pdf" }),
      documentItem({
        id: "doc-2",
        title: "faq",
        file_name: "faq.md",
        file_type: "md",
        source_path: "data/faq.md",
      }),
    ];
    const job = {
      id: "job-1",
      kind: "parse",
      status: "running",
      document_id: "doc-1",
      file_name: "policy.pdf",
      parser_name: null,
      created_at: "2026-10-27T14:00:01Z",
      started_at: "2026-10-27T14:00:02Z",
      finished_at: null,
      error: null,
      result: null,
      progress: 42,
      progress_message: "Đang parse 5/12 trang",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((url) => {
        const target = String(url);
        if (target.includes("/parse-jobs")) return jsonResponse({ jobs: [job] });
        if (target.includes("/documents")) return jsonResponse({ documents });
        return jsonResponse({});
      })
    );

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <DatasetView />
          </ToastProvider>
        </QueryClientProvider>
      );
      await new Promise((resolve) => setTimeout(resolve, 80));
    });

    expect(document.body.textContent).toContain("Đang xử lý nền 1 tài liệu");
    expect(document.body.textContent).toContain("42%");
    expect(
      [...document.body.querySelectorAll('[role="progressbar"]')].some(
        (bar) => bar.getAttribute("aria-valuenow") === "42"
      )
    ).toBe(true);
    const rows = [...document.body.querySelectorAll("tbody tr")];
    const parsingRow = rows.find((row) => row.textContent.includes("policy.pdf"));
    const idleRow = rows.find((row) => row.textContent.includes("faq.md"));

    expect(parsingRow.textContent).toContain("Đang parse");
    expect(parsingRow.querySelector('button[aria-label^="Parse lại"]').disabled).toBe(true);
    expect(parsingRow.querySelector('button[aria-label^="Chia đoạn"]').disabled).toBe(true);
    expect(idleRow.querySelector('button[aria-label^="Parse lại"]').disabled).toBe(false);
    expect(idleRow.querySelector('button[aria-label^="Chia đoạn"]').disabled).toBe(false);
  });
});
