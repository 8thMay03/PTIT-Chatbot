import { describe, expect, it } from "vitest";
import {
  adminRouteHash,
  authPageHref,
  isAdminPath,
  isAppearanceHash,
  legacyHashToAdmin,
  legacyRootHashToChat,
  readAdminRoute,
  readNextParam,
  resolveAppRoute,
  safeNextPath,
} from "./appRoute";

describe("isAdminPath", () => {
  it("chỉ nhận /admin và đường dẫn con", () => {
    expect(isAdminPath("/admin")).toBe(true);
    expect(isAdminPath("/admin/")).toBe(true);
    expect(isAdminPath("/admin/anything")).toBe(true);
    expect(isAdminPath("/")).toBe(false);
    expect(isAdminPath("/administrator")).toBe(false);
    expect(isAdminPath("")).toBe(false);
    expect(isAdminPath(undefined)).toBe(false);
  });
});

describe("legacyHashToAdmin", () => {
  it("chuyển hash màn quản trị cũ sang /admin tương ứng", () => {
    expect(legacyHashToAdmin("#documents")).toBe("/admin#documents");
    expect(legacyHashToAdmin("#config")).toBe("/admin#settings/config");
    expect(legacyHashToAdmin("#models")).toBe("/admin#settings/models");
    expect(legacyHashToAdmin("#settings/config")).toBe("/admin#settings/config");
    expect(legacyHashToAdmin("#settings/models")).toBe("/admin#settings/models");
    expect(legacyHashToAdmin("#settings")).toBe("/admin#settings/config");
    expect(legacyHashToAdmin("#/documents")).toBe("/admin#documents");
  });

  it("giữ ở app sinh viên với #chat, #settings/appearance và hash lạ", () => {
    expect(legacyHashToAdmin("")).toBeNull();
    expect(legacyHashToAdmin("#chat")).toBeNull();
    expect(legacyHashToAdmin("#settings/appearance")).toBeNull();
    expect(legacyHashToAdmin("#main-content")).toBeNull();
  });
});

describe("isAppearanceHash", () => {
  it("chỉ đúng với #settings/appearance", () => {
    expect(isAppearanceHash("#settings/appearance")).toBe(true);
    expect(isAppearanceHash("#settings/config")).toBe(false);
    expect(isAppearanceHash("")).toBe(false);
  });
});

describe("readAdminRoute / adminRouteHash", () => {
  it("đọc hash con trong app admin, tab lạ về config", () => {
    expect(readAdminRoute("#documents")).toEqual({ view: "documents", tab: "config" });
    expect(readAdminRoute("#settings/models")).toEqual({ view: "settings", tab: "models" });
    expect(readAdminRoute("#settings/appearance")).toEqual({
      view: "settings",
      tab: "appearance",
    });
    expect(readAdminRoute("#settings/khac")).toEqual({ view: "settings", tab: "config" });
    expect(readAdminRoute("#models")).toEqual({ view: "settings", tab: "models" });
    expect(readAdminRoute("#chat")).toEqual({ view: "chat", tab: "config" });
    expect(readAdminRoute("#main-content")).toBeNull();
    expect(readAdminRoute(null)).toBeNull();
  });

  it("route → hash khứ hồi", () => {
    for (const hash of ["chat", "documents", "settings/config", "settings/models", "settings/appearance"]) {
      expect(adminRouteHash(readAdminRoute(`#${hash}`))).toBe(hash);
    }
  });
});

describe("resolveAppRoute", () => {
  it("ánh xạ pathname sang trang, đường dẫn lạ về landing", () => {
    expect(resolveAppRoute("/")).toBe("landing");
    expect(resolveAppRoute("")).toBe("landing");
    expect(resolveAppRoute(undefined)).toBe("landing");
    expect(resolveAppRoute("/chat")).toBe("chat");
    expect(resolveAppRoute("/chat/")).toBe("chat");
    expect(resolveAppRoute("/login")).toBe("login");
    expect(resolveAppRoute("/register/")).toBe("register");
    expect(resolveAppRoute("/admin")).toBe("admin");
    expect(resolveAppRoute("/admin/x")).toBe("admin");
    expect(resolveAppRoute("/chatbot")).toBe("landing");
    expect(resolveAppRoute("/khong-co")).toBe("landing");
  });
});

describe("safeNextPath", () => {
  it("nhận đường dẫn nội bộ bắt đầu bằng một dấu /", () => {
    expect(safeNextPath("/chat")).toBe("/chat");
    expect(safeNextPath("/")).toBe("/");
    expect(safeNextPath("/chat#settings/appearance")).toBe("/chat#settings/appearance");
    expect(safeNextPath("/chat?q=hoc-phi")).toBe("/chat?q=hoc-phi");
  });

  it.each([
    ["//evil.com"],
    ["//evil.com/chat"],
    ["/\\evil.com"],
    ["/\\/evil.com"],
    ["/chat\\..\\evil"],
    ["https://evil.com"],
    ["http:/evil.com"],
    ["javascript:alert(1)"],
    ["JavaScript:alert(1)"],
    ["chat"],
    [" /chat"],
    ["/ch at"],
    ["/chat\n//evil.com"],
    ["/chat\t"],
    [""],
    [null],
    [undefined],
    [42],
  ])("chặn %j → /chat", (value) => {
    expect(safeNextPath(value)).toBe("/chat");
  });

  it("đọc next từ query string và dùng fallback khi không hợp lệ", () => {
    expect(readNextParam("?next=%2Fchat%23settings%2Fappearance")).toBe("/chat#settings/appearance");
    expect(readNextParam("?next=%2F%2Fevil.com")).toBe("/chat");
    expect(readNextParam("?next=https%3A%2F%2Fevil.com")).toBe("/chat");
    expect(readNextParam("")).toBe("/chat");
  });

  it("authPageHref giữ next hợp lệ, bỏ next mặc định", () => {
    expect(authPageHref("login")).toBe("/login");
    expect(authPageHref("register", "/chat")).toBe("/register");
    expect(authPageHref("login", "/admin")).toBe("/login?next=%2Fadmin");
    expect(authPageHref("login", "//evil.com")).toBe("/login");
  });
});

describe("legacyRootHashToChat", () => {
  it("hash cũ của app chat ở / chuyển sang /chat", () => {
    expect(legacyRootHashToChat("/", "#chat")).toBe("/chat");
    expect(legacyRootHashToChat("/", "#settings/appearance")).toBe("/chat#settings/appearance");
  });

  it("không chuyển khi đã ở trang khác hoặc hash không thuộc app chat", () => {
    expect(legacyRootHashToChat("/", "")).toBeNull();
    expect(legacyRootHashToChat("/", "#tinh-nang")).toBeNull();
    expect(legacyRootHashToChat("/chat", "#chat")).toBeNull();
    expect(legacyRootHashToChat("/login", "#settings/appearance")).toBeNull();
  });
});
