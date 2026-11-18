import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import ReasoningPanel from "./ReasoningPanel";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("ReasoningPanel guardrail step", () => {
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

  function renderGuardrail(detail) {
    act(() => {
      root.render(<ReasoningPanel open steps={[{ step: "guardrail", status: "end", detail, elapsed_ms: 0 }]} />);
    });
    return container.querySelector(".step-label").textContent;
  }

  it("labels an allowed question as valid, not as in scope", () => {
    const text = renderGuardrail({ allowed: true, reason: "passed" });

    expect(text).toContain("Kiểm tra an toàn câu hỏi");
    expect(text).toContain("Hợp lệ");
    expect(text).not.toContain("phạm vi");
  });

  it("labels a blocked question as blocked", () => {
    const text = renderGuardrail({ allowed: false, reason: "prompt_injection" });

    expect(text).toContain("Bị chặn");
    expect(text).not.toContain("phạm vi");
  });
});
