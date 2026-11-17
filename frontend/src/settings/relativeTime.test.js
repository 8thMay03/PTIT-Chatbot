import { describe, expect, it } from "vitest";
import { NEVER_SAVED, formatLastSaved } from "./relativeTime";

const now = new Date(2026, 10, 17, 15, 30); // 15:30 ngày 17/11/2026, giờ địa phương.

describe("formatLastSaved", () => {
  it("cùng ngày: giờ và 'hôm nay'", () => {
    expect(formatLastSaved(new Date(2026, 10, 17, 14, 2), now)).toBe("14:02 hôm nay");
  });

  it("hôm qua giữ giờ và ghi 'hôm qua'", () => {
    expect(formatLastSaved(new Date(2026, 10, 16, 9, 5), now)).toBe("09:05 hôm qua");
  });

  it("trong năm: giờ và ngày/tháng", () => {
    expect(formatLastSaved(new Date(2026, 10, 15, 8, 0), now)).toBe("08:00 15/11");
  });

  it("khác năm: giờ, ngày/tháng/năm", () => {
    expect(formatLastSaved(new Date(2025, 11, 31, 23, 59), now)).toBe("23:59 31/12/2025");
  });

  it("chưa lưu hoặc dữ liệu hỏng thì ghi rõ chưa lưu", () => {
    expect(formatLastSaved(null, now)).toBe(NEVER_SAVED);
    expect(formatLastSaved(undefined, now)).toBe(NEVER_SAVED);
    expect(formatLastSaved("không phải ngày", now)).toBe(NEVER_SAVED);
  });
});
