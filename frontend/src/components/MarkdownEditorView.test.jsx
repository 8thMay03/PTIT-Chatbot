import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MarkdownEditorView from "./MarkdownEditorView";
import { ToastProvider } from "./Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(payload) });
}

function markdown(text, contentHash, extra = {}) {
  return {
    document_id: "doc-1",
    text,
    content_hash: contentHash,
    status: "parsed",
    parsed_at: null,
    markdown_edited: false,
    ...extra,
  };
}

function button(label) {
  return [...document.body.querySelectorAll("button")].find((item) => item.textContent.trim() === label);
}

async function type(textarea, value) {
  const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  await act(async () => {
    setValue.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function click(element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

describe("MarkdownEditorView", () => {
  let container;
  let root;
  let onClose;

  beforeEach(async () => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    onClose = vi.fn();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function renderEditor(fetchMock) {
    vi.stubGlobal("fetch", fetchMock);
    await act(async () => {
      root.render(
        <ToastProvider>
          <MarkdownEditorView documentId="doc-1" fileName="policy.pdf" onClose={onClose} />
        </ToastProvider>
      );
    });
  }

  it("hiện Markdown thô cạnh bản render và lưu kèm content_hash mới nhất", async () => {
    const fetchMock = vi.fn((url, options = {}) => {
      if (!options.method) return jsonResponse(markdown("# Học phí\n\nBản parser", "hash-1"));
      const body = JSON.parse(options.body);
      return jsonResponse(markdown(body.text, `hash-after-${body.base_hash}`, { markdown_edited: true }));
    });
    await renderEditor(fetchMock);

    const textarea = container.querySelector("textarea");
    expect(textarea.value).toBe("# Học phí\n\nBản parser");
    expect(container.querySelector(".md-editor-preview h1")?.textContent).toBe("Học phí");
    expect(button("Lưu").disabled).toBe(true);

    await type(textarea, "# Học phí\n\nBản sửa tay");
    expect(container.querySelector(".md-editor-state").textContent).toBe("Có thay đổi chưa lưu");
    await click(button("Lưu"));

    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/api\/documents\/doc-1\/markdown$/),
      expect.objectContaining({ method: "PUT" })
    );
    expect(JSON.parse(fetchMock.mock.lastCall[1].body)).toEqual({
      text: "# Học phí\n\nBản sửa tay",
      base_hash: "hash-1",
    });
    expect(container.querySelector(".md-editor-state").textContent).toBe("Đã lưu");
    expect(button("Lưu").disabled).toBe(true);

    // Lần lưu sau gửi hash do máy chủ trả về, không phải hash lúc mở trình sửa.
    await type(textarea, "# Học phí\n\nSửa lần hai");
    await click(button("Lưu"));
    expect(JSON.parse(fetchMock.mock.lastCall[1].body).base_hash).toBe("hash-after-hash-1");
  });

  it("hỏi trước khi bỏ thay đổi chưa lưu", async () => {
    await renderEditor(vi.fn(() => jsonResponse(markdown("# A", "hash-1"))));

    await type(container.querySelector("textarea"), "# B");
    await click(button("Quay lại tài liệu"));

    expect(onClose).not.toHaveBeenCalled();
    expect(document.body.querySelector("[role='dialog']")).not.toBeNull();

    await click(button("Bỏ thay đổi"));
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it("báo lỗi khi tài liệu chưa có bản parse", async () => {
    await renderEditor(
      vi.fn(() => jsonResponse({ detail: "Tài liệu chưa có bản parse đã lưu; hãy parse lại." }, 409))
    );

    expect(container.querySelector("[role='alert']").textContent).toContain("chưa có bản parse");
    expect(container.querySelector("textarea")).toBeNull();
  });
});
