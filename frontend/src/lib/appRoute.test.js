import { describe, expect, it } from "vitest";
import {
  ADMIN_SETTINGS_SECTIONS,
  adminRouteHash,
  authPageHref,
  chatPathWithQuestion,
  isAdminPath,
  isAdminTarget,
  isAppearanceHash,
  legacyHashToAdmin,
  legacyRootHashToChat,
  modelKindForSection,
  readAdminRoute,
  readNextParam,
  readQuestionParam,
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

describe("isAdminTarget", () => {
  it("bỏ query/hash trước khi so đường dẫn admin", () => {
    expect(isAdminTarget("/admin#documents/abc")).toBe(true);
    expect(isAdminTarget("/admin?x=1")).toBe(true);
    expect(isAdminTarget("/admin/settings#config")).toBe(true);
    expect(isAdminTarget("/administrator#x")).toBe(false);
    expect(isAdminTarget("/chat?q=/admin")).toBe(false);
    expect(isAdminTarget(null)).toBe(false);
  });
});

describe("legacyHashToAdmin", () => {
  it("chuyển hash màn quản trị cũ sang mục Settings mới", () => {
    expect(legacyHashToAdmin("#documents")).toBe("/admin#documents");
    expect(legacyHashToAdmin("#config")).toBe("/admin#settings/retrieval");
    expect(legacyHashToAdmin("#models")).toBe("/admin#settings/models-llm");
    expect(legacyHashToAdmin("#settings/config")).toBe("/admin#settings/retrieval");
    expect(legacyHashToAdmin("#settings/models")).toBe("/admin#settings/models-llm");
    expect(legacyHashToAdmin("#settings")).toBe("/admin#settings/retrieval");
    expect(legacyHashToAdmin("#settings/gate")).toBe("/admin#settings/gate");
    expect(legacyHashToAdmin("#settings/models-reranker")).toBe("/admin#settings/models-reranker");
    expect(legacyHashToAdmin("#settings/khac")).toBe("/admin#settings/retrieval");
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
  it("đọc hash con trong app admin, key lạ về retrieval", () => {
    expect(readAdminRoute("#documents")).toEqual({ view: "documents", section: null, datasetId: null });
    expect(readAdminRoute("#documents/abc_123")).toEqual({
      view: "documents",
      section: null,
      datasetId: "abc_123",
    });
    expect(readAdminRoute("#documents/invalid!")).toBeNull();
    for (const section of [
      "retrieval",
      "reranker",
      "gate",
      "generation",
      "models-llm",
      "models-embedding",
      "models-reranker",
      "appearance",
    ]) {
      expect(readAdminRoute(`#settings/${section}`)).toEqual({
        view: "settings",
        section,
        datasetId: null,
      });
    }
    expect(readAdminRoute("#settings")).toEqual({ view: "settings", section: null, datasetId: null });
    expect(readAdminRoute("#settings/config")).toEqual({
      view: "settings",
      section: "retrieval",
      datasetId: null,
    });
    expect(readAdminRoute("#settings/models")).toEqual({
      view: "settings",
      section: "models-llm",
      datasetId: null,
    });
    expect(readAdminRoute("#settings/khac")).toEqual({
      view: "settings",
      section: "retrieval",
      datasetId: null,
    });
    expect(readAdminRoute("#config")).toEqual({
      view: "settings",
      section: "retrieval",
      datasetId: null,
    });
    expect(readAdminRoute("#models")).toEqual({
      view: "settings",
      section: "models-llm",
      datasetId: null,
    });
    expect(readAdminRoute("#chat")).toEqual({ view: "chat", section: null, datasetId: null });
    expect(readAdminRoute("#main-content")).toBeNull();
    expect(readAdminRoute(null)).toBeNull();
  });

  it("route → hash khứ hồi", () => {
    for (const hash of [
      "chat",
      "documents",
      "documents/abc_123",
      "settings",
      ...ADMIN_SETTINGS_SECTIONS.map((section) => `settings/${section}`),
    ]) {
      expect(adminRouteHash(readAdminRoute(`#${hash}`))).toBe(hash);
    }
  });
});

describe("modelKindForSection", () => {
  it("ánh xạ mục Mô hình sang loại trong kho, mục khác là null", () => {
    expect(modelKindForSection("models-llm")).toBe("llm");
    expect(modelKindForSection("models-embedding")).toBe("embedding");
    expect(modelKindForSection("models-reranker")).toBe("reranker");
    expect(modelKindForSection("retrieval")).toBeNull();
    expect(modelKindForSection(null)).toBeNull();
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

describe("chatPathWithQuestion / readQuestionParam", () => {
  it("mã hoá câu hỏi vào ?q= và đọc lại đúng", () => {
    const path = chatPathWithQuestion("  Học phí & học bổng?  ");
    expect(path).toBe(`/chat?q=${encodeURIComponent("Học phí & học bổng?")}`);
    expect(readQuestionParam(path.slice("/chat".length))).toBe("Học phí & học bổng?");
  });

  it("câu hỏi rỗng về /chat; cắt độ dài tối đa", () => {
    expect(chatPathWithQuestion("   ")).toBe("/chat");
    expect(readQuestionParam("")).toBe("");
    expect(readQuestionParam(`?q=${"a".repeat(1200)}`)).toHaveLength(1000);
  });
});
