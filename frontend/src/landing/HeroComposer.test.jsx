import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const transitionTo = vi.fn();
vi.mock("../lib/motion/pixelTransition", () => ({ transitionTo: (url) => transitionTo(url) }));

const { default: HeroComposer } = await import("./HeroComposer");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function pressEnter(target, init = {}) {
  const event = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true, ...init });
  if (init.keyCode !== undefined) Object.defineProperty(event, "keyCode", { value: init.keyCode });
  act(() => {
    target.dispatchEvent(event);
  });
  return event;
}

describe("HeroComposer", () => {
  let container;
  let root;

  beforeEach(() => {
    transitionTo.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root.render(<HeroComposer />));
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("Enter chốt chữ IME (isComposing hoặc keyCode 229) không mở trang chat", () => {
    const textarea = container.querySelector("textarea");

    const composing = pressEnter(textarea, { isComposing: true });
    const safari = pressEnter(textarea, { keyCode: 229 });
    pressEnter(textarea, { shiftKey: true });

    expect(transitionTo).not.toHaveBeenCalled();
    // Không chặn Enter của IME: bộ gõ cần nó để chốt chữ.
    expect(composing.defaultPrevented).toBe(false);
    expect(safari.defaultPrevented).toBe(false);
  });

  it("Enter thường mở trang chat", () => {
    pressEnter(container.querySelector("textarea"));

    expect(transitionTo).toHaveBeenCalledTimes(1);
  });
});
