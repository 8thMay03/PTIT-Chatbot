import { describe, expect, it } from "vitest";
import { isApplePlatform, isImeComposing, isSubmitEnter, isSubmitKey } from "./keyboard";

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

describe("isSubmitKey", () => {
  it("mặc định giống isSubmitEnter", () => {
    expect(isSubmitKey(keydown({}))).toBe(true);
    expect(isSubmitKey(keydown({}), { enterToSend: true })).toBe(true);
    expect(isSubmitKey(keydown({ shiftKey: true }), { enterToSend: true })).toBe(false);
    expect(isSubmitKey(keydown({ isComposing: true }), { enterToSend: true })).toBe(false);
  });

  it("tắt Enter gửi: Enter xuống dòng, Ctrl/Cmd+Enter gửi", () => {
    const options = { enterToSend: false };
    expect(isSubmitKey(keydown({}), options)).toBe(false);
    expect(isSubmitKey(keydown({ shiftKey: true }), options)).toBe(false);
    expect(isSubmitKey(keydown({ ctrlKey: true }), options)).toBe(true);
    expect(isSubmitKey(keydown({ metaKey: true }), options)).toBe(true);
    expect(isSubmitKey(keydown({ key: "a", ctrlKey: true }), options)).toBe(false);
  });

  it("Ctrl+Enter chốt chữ IME vẫn không gửi", () => {
    const options = { enterToSend: false };
    expect(isSubmitKey(keydown({ ctrlKey: true, isComposing: true }), options)).toBe(false);
    expect(isSubmitKey(keydown({ metaKey: true, keyCode: 229 }), options)).toBe(false);
  });
});

describe("isApplePlatform", () => {
  it("nhận macOS/iOS, không nhận Windows", () => {
    expect(isApplePlatform({ platform: "MacIntel" })).toBe(true);
    expect(isApplePlatform({ userAgentData: { platform: "macOS" } })).toBe(true);
    expect(isApplePlatform({ platform: "iPhone" })).toBe(true);
    expect(isApplePlatform({ platform: "Win32" })).toBe(false);
    expect(isApplePlatform(undefined)).toBe(false);
  });
});
