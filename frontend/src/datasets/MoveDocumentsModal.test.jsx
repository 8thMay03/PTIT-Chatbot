import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MoveDocumentsModal from "./MoveDocumentsModal";
import { ToastProvider } from "../components/Toast";
import { queryKeys } from "../api";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("MoveDocumentsModal", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
    // Seed cache để không cần fetch mạng.
    queryClient.setQueryData(queryKeys.datasetList, {
      datasets: [
        { id: "a", name: "A", document_count: 1 },
        { id: "b", name: "B", document_count: 2 },
      ],
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  it("hiển thị dataset đích trừ dataset hiện tại", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <MoveDocumentsModal open documentIds={["d1", "d2"]} currentDatasetId="a" onClose={vi.fn()} onMoved={vi.fn()} />
          </ToastProvider>
        </QueryClientProvider>
      );
      await new Promise((resolve) => setTimeout(resolve, 100));
    });
    expect(document.body.textContent).toContain("B");
    // Dataset hiện tại (A) bị lọc khỏi danh sách đích.
    expect(document.body.textContent).not.toContain("Không còn dataset khác");
  });
});
