import { describe, expect, it } from "vitest";
import { ACTIVE_LINE_PX, pickActiveSection } from "./scrollSpy";

// Số đo gần với form thật ở 1366×820: khung 700px, nội dung 1935px (cuộn tối đa 1235px).
const layout = {
  keys: ["retrieval", "reranker", "gate", "generation"],
  offsets: [12, 640, 900, 1435],
  clientHeight: 700,
  scrollHeight: 1935,
};

describe("pickActiveSection", () => {
  it("ở đầu form là mục đầu tiên", () => {
    expect(pickActiveSection({ ...layout, scrollTop: 0 })).toBe("retrieval");
  });

  it("chọn mục cuối cùng có tiêu đề đã qua vạch", () => {
    expect(pickActiveSection({ ...layout, scrollTop: 628 })).toBe("reranker");
    expect(pickActiveSection({ ...layout, scrollTop: 888 })).toBe("gate");
    // Tiêu đề "Ngưỡng tin cậy" chưa tới vạch thì vẫn là mục trước.
    expect(pickActiveSection({ ...layout, scrollTop: 900 - ACTIVE_LINE_PX - 1 })).toBe("reranker");
  });

  it("cuộn tới đáy là mục cuối dù tiêu đề chưa lên tới đỉnh khung", () => {
    // Bấm "Sinh câu trả lời": khung chỉ cuộn được tới 1235, tiêu đề còn cách đỉnh 200px.
    expect(pickActiveSection({ ...layout, scrollTop: 1235 })).toBe("generation");
    expect(pickActiveSection({ ...layout, scrollTop: 1234 })).toBe("generation");
    expect(pickActiveSection({ ...layout, scrollTop: 1200 })).toBe("gate");
  });

  it("nội dung vừa khung (không cuộn được) không coi là ở đáy", () => {
    expect(
      pickActiveSection({ ...layout, scrollTop: 0, scrollHeight: 700 })
    ).toBe("retrieval");
  });

  it("không có mục thì trả null", () => {
    expect(pickActiveSection({ ...layout, keys: [], scrollTop: 0 })).toBeNull();
  });
});
