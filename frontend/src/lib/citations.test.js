import { describe, expect, it } from "vitest";
import { hasCitedSource, sourcesLabel } from "./citations";

const SOURCES = [{ citation_id: 1 }, { citation_id: 2 }];

describe("hasCitedSource", () => {
  it("nhận [n] khớp citation_id trong sources", () => {
    expect(hasCitedSource("Học phí thu theo kỳ [2].", SOURCES)).toBe(true);
    expect(sourcesLabel("Học phí thu theo kỳ [2].", SOURCES)).toBe("Nguồn trích dẫn");
  });

  it("không có [n] hoặc [n] không có trong sources là nguồn liên quan", () => {
    expect(hasCitedSource("Tài liệu chưa đề cập mức phạt.", SOURCES)).toBe(false);
    expect(hasCitedSource("Xem mục [7].", SOURCES)).toBe(false);
    expect(sourcesLabel("Xem mục [7].", SOURCES)).toBe("Nguồn liên quan");
  });

  it("bỏ qua [n] trong code và khi không có sources", () => {
    expect(hasCitedSource("Dùng `arr[1]` và\n```\nx = a[2]\n```", SOURCES)).toBe(false);
    expect(hasCitedSource("Học phí [1].", [])).toBe(false);
    expect(hasCitedSource("", SOURCES)).toBe(false);
  });
});
