import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import ParseProgress from "./ParseProgress";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("ParseProgress", () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  function render(props) {
    act(() => {
      root.render(<ParseProgress {...props} />);
    });
  }

  it("renders the percentage, message and accessible progress value", () => {
    render({ progress: 42, message: "Đang parse 5/12 trang", label: "Tài liệu A" });

    expect(container.textContent).toContain("42%");
    expect(container.textContent).toContain("Đang parse 5/12 trang");
    const bar = container.querySelector('[role="progressbar"]');
    expect(bar.getAttribute("aria-valuenow")).toBe("42");
    expect(bar.getAttribute("aria-label")).toBe("Tài liệu A");
    expect(container.querySelector(".parse-progress-fill").style.width).toBe("42%");
  });

  it("shows an indeterminate waiting bar for queued jobs", () => {
    render({ progress: 0, indeterminate: true, label: "Đang chờ" });

    expect(container.textContent).toContain("Chờ");
    const bar = container.querySelector('[role="progressbar"]');
    expect(bar.getAttribute("aria-valuenow")).toBeNull();
    expect(bar.getAttribute("aria-busy")).toBe("true");
    expect(container.querySelector(".parse-progress").className).toContain("is-indeterminate");
  });
});
