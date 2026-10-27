import { describe, expect, it } from "vitest";
import {
  adminRouteHash,
  isAdminPath,
  isAppearanceHash,
  legacyHashToAdmin,
  readAdminRoute,
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
