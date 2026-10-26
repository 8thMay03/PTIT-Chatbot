import { describe, expect, it } from "vitest";
import { canEditMarkdown, documentStatus, needsChunking } from "./documentStatus";

describe("documentStatus", () => {
  it("phân biệt đã nạp, chờ chia đoạn và cần chia đoạn lại", () => {
    expect(documentStatus({ status: "active", chunk_count: 4 }).label).toBe("Đã nạp");
    expect(documentStatus({ status: "parsed", chunk_count: 0 }).key).toBe("parsed");
    expect(documentStatus({ status: "parsed", chunk_count: 4 }).key).toBe("stale");
    expect(documentStatus(null).label).toBe("—");
  });

  it("chỉ tài liệu đã parse mới cần chia đoạn", () => {
    expect(needsChunking({ status: "parsed" })).toBe(true);
    expect(needsChunking({ status: "active" })).toBe(false);
  });

  it("chỉ sửa được Markdown khi tài liệu đã lưu bản parse", () => {
    expect(canEditMarkdown({ parsed_at: "2026-10-27T00:00:00Z" })).toBe(true);
    // Tài liệu index trước khi tách hai bước.
    expect(canEditMarkdown({ parsed_at: null })).toBe(false);
  });
});
