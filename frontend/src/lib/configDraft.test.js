import { describe, expect, it } from "vitest";
import { mergeConfigDraft } from "./configDraft";

describe("mergeConfigDraft", () => {
  it("nhận giá trị mới từ tab khác nhưng giữ trường đang sửa dở", () => {
    const previous = { rerankerEnabled: true, temperature: 0, topK: 4 };
    const current = { rerankerEnabled: true, temperature: 0.7, topK: 4 };
    const next = { rerankerEnabled: false, temperature: 0, topK: 6 };

    expect(mergeConfigDraft(current, previous, next)).toEqual({
      rerankerEnabled: false,
      temperature: 0.7,
      topK: 6,
    });
  });

  it("lần đọc đầu tiên lấy toàn bộ giá trị máy chủ", () => {
    const next = { rerankerEnabled: false, temperature: 0.2, topK: 5 };
    expect(mergeConfigDraft({}, null, next)).toEqual(next);
  });
});
