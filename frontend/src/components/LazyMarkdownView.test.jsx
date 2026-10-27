import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import LazyMarkdownView, { preloadMarkdownView } from "./LazyMarkdownView";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("LazyMarkdownView", () => {
  let container;
  let root;

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("hiện văn bản thuần đã escape khi chưa tải xong, rồi render Markdown đã lọc", async () => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    const content = "**Học phí** <img src=x onerror=alert(1)>";

    act(() => {
      root.render(<LazyMarkdownView className="md" content={content} sources={[]} />);
    });
    const pending = container.querySelector(".markdown-pending");
    if (pending) {
      // Fallback: chuỗi gốc là text node, không có thẻ HTML nào được tạo.
      expect(pending.textContent).toBe(content);
      expect(container.querySelector("img")).toBeNull();
    }

    await act(async () => {
      await preloadMarkdownView();
    });

    expect(container.querySelector(".markdown-pending")).toBeNull();
    expect(container.querySelector(".md strong").textContent).toBe("Học phí");
    expect(container.querySelector("img[onerror]")).toBeNull();
  });
});
