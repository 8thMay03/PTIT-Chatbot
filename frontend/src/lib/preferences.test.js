import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  applyFontScale,
  normalizePreferences,
  readPreferences,
  usePreferences,
  writePreferences,
} from "./preferences";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

/** Render một hook trong component tạm; `result.current` là giá trị trả về mới nhất. */
function renderHook(useHook) {
  const result = { current: undefined };
  const container = document.createElement("div");
  const root = createRoot(container);
  function Harness() {
    result.current = useHook();
    return null;
  }
  act(() => root.render(createElement(Harness)));
  return { result, unmount: () => act(() => root.unmount()) };
}

const mounted = [];
function mount(useHook) {
  const rendered = renderHook(useHook);
  mounted.push(rendered);
  return rendered;
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-font-scale");
});

afterEach(() => {
  mounted.splice(0).forEach(({ unmount }) => unmount());
  vi.restoreAllMocks();
});

describe("normalizePreferences", () => {
  it("giữ trường hợp lệ, trường lạ về mặc định", () => {
    expect(
      normalizePreferences({ fontScale: "lg", enterToSend: false, keepReasoningOpen: true, reasoningEffort: "high" })
    ).toEqual({
      fontScale: "lg",
      enterToSend: false,
      keepReasoningOpen: true,
      reasoningEffort: "high",
    });
    expect(
      normalizePreferences({ fontScale: "xl", enterToSend: "no", keepReasoningOpen: 1, reasoningEffort: "max" })
    ).toEqual(DEFAULT_PREFERENCES);
    expect(normalizePreferences(null)).toEqual(DEFAULT_PREFERENCES);
  });
});

describe("readPreferences / writePreferences", () => {
  it("chưa lưu gì thì trả mặc định", () => {
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  it("ghi rồi đọc lại đúng, kèm version", () => {
    const saved = { fontScale: "sm", enterToSend: false, keepReasoningOpen: true, reasoningEffort: "medium" };
    expect(writePreferences(saved)).toBe(true);
    expect(JSON.parse(localStorage.getItem(PREFERENCES_STORAGE_KEY))).toEqual({ version: 1, ...saved });
    expect(readPreferences()).toEqual(saved);
  });

  it("bản lưu trước khi có mức suy luận: giữ các trường cũ, mức suy luận là Tự động", () => {
    localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ version: 1, fontScale: "lg", enterToSend: false, keepReasoningOpen: true })
    );
    expect(readPreferences()).toEqual({
      fontScale: "lg",
      enterToSend: false,
      keepReasoningOpen: true,
      reasoningEffort: "auto",
    });
  });

  it("JSON hỏng hoặc version khác thì trả mặc định", () => {
    localStorage.setItem(PREFERENCES_STORAGE_KEY, "{hỏng");
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
    localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify({ version: 2, fontScale: "lg" }));
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  it("storage bị chặn: đọc trả mặc định, ghi trả false, không ném lỗi", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
    expect(writePreferences({ fontScale: "lg" })).toBe(false);
  });
});

describe("applyFontScale", () => {
  it("đặt data-font-scale cho sm/lg, bỏ thuộc tính với md hoặc giá trị lạ", () => {
    const root = document.documentElement;
    applyFontScale("lg");
    expect(root.getAttribute("data-font-scale")).toBe("lg");
    applyFontScale("md");
    expect(root.hasAttribute("data-font-scale")).toBe(false);
    applyFontScale("sm");
    applyFontScale("xl");
    expect(root.hasAttribute("data-font-scale")).toBe(false);
  });
});

describe("usePreferences", () => {
  it("đổi tùy chọn: áp dụng ngay, lưu lại và giữ sau khi mount lại", () => {
    const { result, unmount } = renderHook(() => usePreferences());
    expect(result.current.fontScale).toBe("md");

    let persisted;
    act(() => {
      persisted = result.current.setPreference("fontScale", "lg");
    });
    act(() => {
      result.current.setPreference("enterToSend", false);
    });

    expect(persisted).toBe(true);
    expect(result.current.fontScale).toBe("lg");
    expect(result.current.enterToSend).toBe(false);
    expect(document.documentElement.getAttribute("data-font-scale")).toBe("lg");
    unmount();
    // Rời trang chat thì bỏ cỡ chữ đã gắn.
    expect(document.documentElement.hasAttribute("data-font-scale")).toBe(false);

    const { result: reloaded } = mount(() => usePreferences());
    expect(reloaded.current).toMatchObject({ fontScale: "lg", enterToSend: false, keepReasoningOpen: false });
    expect(document.documentElement.getAttribute("data-font-scale")).toBe("lg");
  });

  it("storage bị chặn: vẫn áp dụng trong phiên, setPreference trả false", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    const { result } = mount(() => usePreferences());

    let persisted;
    act(() => {
      persisted = result.current.setPreference("keepReasoningOpen", true);
    });

    expect(persisted).toBe(false);
    expect(result.current.keepReasoningOpen).toBe(true);
  });

  it("bỏ qua khoá không thuộc tùy chọn", () => {
    const { result } = mount(() => usePreferences());
    let persisted;
    act(() => {
      persisted = result.current.setPreference("theme", "dark");
    });
    expect(persisted).toBe(false);
    expect(result.current).not.toHaveProperty("theme");
  });
});
