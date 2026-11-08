import { describe, expect, it } from "vitest";
import { isImeComposing, isSubmitEnter } from "./keyboard";

function keydown(init) {
  const event = new KeyboardEvent("keydown", { key: "Enter", ...init });
  // jsdom không nhận `keyCode` qua init của KeyboardEvent.
  if (init?.keyCode !== undefined) Object.defineProperty(event, "keyCode", { value: init.keyCode });
  return event;
}

describe("isImeComposing", () => {
  it("nhận Enter chốt chữ qua isComposing (Chrome/Edge) hoặc keyCode 229 (Safari)", () => {
    expect(isImeComposing(keydown({ isComposing: true }))).toBe(true);
    expect(isImeComposing(keydown({ keyCode: 229 }))).toBe(true);
    expect(isImeComposing(keydown({ keyCode: 13 }))).toBe(false);
  });

  it("đọc nativeEvent của synthetic event React", () => {
    expect(isImeComposing({ nativeEvent: keydown({ isComposing: true }) })).toBe(true);
    expect(isImeComposing({ nativeEvent: keydown({}) })).toBe(false);
  });
});

describe("isSubmitEnter", () => {
  it("chỉ Enter thường mới gửi", () => {
    expect(isSubmitEnter(keydown({}))).toBe(true);
    expect(isSubmitEnter(keydown({ shiftKey: true }))).toBe(false);
    expect(isSubmitEnter(keydown({ isComposing: true }))).toBe(false);
    expect(isSubmitEnter(keydown({ keyCode: 229 }))).toBe(false);
    expect(isSubmitEnter(keydown({ key: "a" }))).toBe(false);
  });
});
